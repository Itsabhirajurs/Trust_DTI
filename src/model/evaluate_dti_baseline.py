"""Train/evaluate a leakage-aware classical baseline for Network 1.

Features: RDKit Morgan fingerprints for compounds + one-hot target-family labels.
This is a reference baseline, not the final ChemBERTa/ESM-2 fusion model.

Examples (run from the repository root after local data is available):
    python -m src.model.evaluate_dti_baseline --split random
    python -m src.model.evaluate_dti_baseline --split drugcold
    python -m src.model.evaluate_dti_baseline --split targetcold
    python -m src.model.evaluate_dti_baseline --split temporal

Default row caps bound CPU memory/time. Reported metrics describe sampled
partitions unless caps are set high enough to cover those partitions in full.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import rdFingerprintGenerator
from scipy.sparse import csr_matrix, hstack
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

from src import config


SPLIT_COLUMNS = {
    "random": "split_random",
    "drugcold": "split_drugcold",
    "targetcold": "split_targetcold",
    "temporal": "split_temporal",
}
PARTITIONS = ("train", "calib", "test")
LABEL_TO_INT = {"INACTIVE": 0, "ACTIVE": 1}
INT_TO_LABEL = {value: key for key, value in LABEL_TO_INT.items()}


def stratified_cap(frame: pd.DataFrame, max_rows: int, seed: int) -> pd.DataFrame:
    """Take a reproducible, label-stratified sample; non-positive cap means all rows."""
    if max_rows <= 0 or len(frame) <= max_rows:
        return frame.copy().reset_index(drop=True)
    counts = frame["label"].value_counts()
    if frame["label"].nunique() < 2 or counts.min() < 2:
        raise ValueError("Cannot stratify this partition: both labels need at least two rows.")
    if max_rows < frame["label"].nunique():
        raise ValueError("max_rows must be at least the number of classes.")
    sampled, _ = train_test_split(
        frame,
        train_size=max_rows,
        random_state=seed,
        stratify=frame["label"].astype(str),
    )
    return sampled.reset_index(drop=True)


def split_conformal_prediction_sets(
    calibration_probabilities: np.ndarray,
    calibration_labels: np.ndarray,
    evaluation_probabilities: np.ndarray,
    alpha: float = 0.1,
) -> tuple[np.ndarray, float]:
    """Return class-inclusion sets and the split-conformal nonconformity quantile.

    Class column order is [INACTIVE, ACTIVE]. Coverage guarantees rely on
    exchangeability assumptions; this helper does not establish those assumptions.
    """
    p_cal = np.asarray(calibration_probabilities, dtype=float)
    y_cal = np.asarray(calibration_labels, dtype=int).reshape(-1)
    p_eval = np.asarray(evaluation_probabilities, dtype=float)

    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1.")
    if p_cal.ndim != 2 or p_cal.shape[1] != 2:
        raise ValueError("Calibration probabilities must have shape (n, 2).")
    if p_eval.ndim != 2 or p_eval.shape[1] != 2:
        raise ValueError("Evaluation probabilities must have shape (n, 2).")
    if len(p_cal) != len(y_cal) or not len(y_cal):
        raise ValueError("Calibration labels must match a non-empty calibration set.")
    if not np.isfinite(p_cal).all() or not np.isfinite(p_eval).all():
        raise ValueError("Probabilities must be finite.")
    if np.any((y_cal < 0) | (y_cal > 1)):
        raise ValueError("Labels must be 0 (INACTIVE) or 1 (ACTIVE).")
    if np.any((p_cal < 0) | (p_cal > 1)) or np.any((p_eval < 0) | (p_eval > 1)):
        raise ValueError("Probabilities must lie in [0, 1].")

    nonconformity = 1.0 - p_cal[np.arange(len(y_cal)), y_cal]
    rank = int(math.ceil((len(nonconformity) + 1) * (1.0 - alpha)))
    quantile = (
        1.0
        if rank > len(nonconformity)
        else float(np.partition(nonconformity, rank - 1)[rank - 1])
    )
    included = (1.0 - p_eval) <= quantile + 1e-12
    return included, quantile


def validate_split_integrity(frame: pd.DataFrame, split_name: str) -> dict[str, bool]:
    """Check required partitions and separation specific to the requested split."""
    if split_name not in SPLIT_COLUMNS:
        raise ValueError(f"Unsupported split: {split_name}")
    split_column = SPLIT_COLUMNS[split_name]
    required = {split_column, "pik", "accession", "label"}
    if not required.issubset(frame.columns):
        raise ValueError(
            f"Missing columns for split validation: {sorted(required - set(frame.columns))}"
        )

    parts = {part: frame.loc[frame[split_column].eq(part)] for part in PARTITIONS}
    checks = {f"{part}_nonempty": not parts[part].empty for part in PARTITIONS}
    checks["unique_compound_protein_pairs"] = not frame.duplicated(["pik", "accession"]).any()
    checks["all_pairs_have_protein_accession"] = bool(frame["accession"].notna().all())

    if split_name == "drugcold":
        if "scaffold_group" not in frame.columns:
            raise ValueError("Drug-cold validation requires scaffold_group.")
        if frame["scaffold_group"].isna().any():
            checks["all_pairs_have_scaffold_group"] = False
        for left, right in (("train", "calib"), ("train", "test"), ("calib", "test")):
            a = set(parts[left]["scaffold_group"].dropna().astype(str))
            b = set(parts[right]["scaffold_group"].dropna().astype(str))
            checks[f"{left}_{right}_scaffold_disjoint"] = a.isdisjoint(b)

    elif split_name == "targetcold":
        for left, right in (("train", "calib"), ("train", "test"), ("calib", "test")):
            a = set(parts[left]["accession"].dropna().astype(str))
            b = set(parts[right]["accession"].dropna().astype(str))
            checks[f"{left}_{right}_target_disjoint"] = a.isdisjoint(b)

    elif split_name == "temporal":
        if "year" not in frame.columns:
            raise ValueError("Temporal validation requires year.")
        years = pd.to_numeric(frame["year"], errors="coerce")
        calib_years = years.loc[frame[split_column].eq("calib")].dropna()
        test_years = years.loc[frame[split_column].eq("test")].dropna()
        checks["temporal_calibration_before_2020"] = (
            not calib_years.empty and int(calib_years.max()) < 2020
        )
        checks["temporal_test_from_2020"] = (
            not test_years.empty and int(test_years.min()) >= 2020
        )

    return checks


def build_morgan_matrix(
    compound_keys: list[str],
    smiles_by_key: dict[str, str],
    radius: int = 2,
    n_bits: int = 2048,
) -> tuple[csr_matrix, dict[str, int]]:
    """Create a sparse binary Morgan fingerprint matrix for unique compound keys."""
    unique_keys = list(dict.fromkeys(str(key) for key in compound_keys))
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits)
    indices: list[int] = []
    indptr = [0]

    for key in unique_keys:
        smiles = smiles_by_key.get(key)
        if not isinstance(smiles, str) or not smiles.strip():
            raise ValueError(f"No standardized SMILES found for compound key: {key}")
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            raise ValueError(f"RDKit could not parse standardized SMILES for {key}")
        indices.extend(int(bit) for bit in generator.GetFingerprint(molecule).GetOnBits())
        indptr.append(len(indices))

    matrix = csr_matrix(
        (
            np.ones(len(indices), dtype=np.float32),
            np.asarray(indices, dtype=np.int32),
            np.asarray(indptr, dtype=np.int64),
        ),
        shape=(len(unique_keys), n_bits),
        dtype=np.float32,
    )
    return matrix, {key: i for i, key in enumerate(unique_keys)}


def expected_calibration_error(
    labels: np.ndarray, active_probabilities: np.ndarray, n_bins: int = 15
) -> float:
    """Fixed-width ECE diagnostic; sensitive to binning and not a calibration guarantee."""
    y = np.asarray(labels, dtype=int)
    probability = np.asarray(active_probabilities, dtype=float)
    if len(y) == 0 or len(y) != len(probability) or n_bins < 1:
        raise ValueError("ECE requires equal non-empty arrays and n_bins >= 1.")
    if not np.isfinite(probability).all() or np.any((probability < 0) | (probability > 1)):
        raise ValueError("Probabilities must be finite and in [0, 1].")
    bins = np.minimum((probability * n_bins).astype(int), n_bins - 1)
    error = 0.0
    for bin_index in range(n_bins):
        mask = bins == bin_index
        if mask.any():
            error += float(mask.mean()) * abs(
                float(probability[mask].mean()) - float(y[mask].mean())
            )
    return error


def _safe_metric(metric, y_true: np.ndarray, values: np.ndarray) -> float | None:
    try:
        return float(metric(y_true, values))
    except ValueError:
        return None


def metric_summary(
    y_true: np.ndarray, p_active: np.ndarray, threshold: float = 0.5
) -> dict[str, Any]:
    """Compute standard thresholded, ranking, and probability-quality metrics."""
    y_pred = (p_active >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision_active": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall_active": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_active": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": _safe_metric(roc_auc_score, y_true, p_active),
        "average_precision": _safe_metric(average_precision_score, y_true, p_active),
        "brier_score": float(brier_score_loss(y_true, p_active)),
        "expected_calibration_error_15_bins": expected_calibration_error(y_true, p_active),
        "confusion_matrix_labels_inactive_active": [
            [
                int(((y_true == 0) & (y_pred == 0)).sum()),
                int(((y_true == 0) & (y_pred == 1)).sum()),
            ],
            [
                int(((y_true == 1) & (y_pred == 0)).sum()),
                int(((y_true == 1) & (y_pred == 1)).sum()),
            ],
        ],
    }


def label_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["label"].value_counts().to_dict()
    return {str(label): int(count) for label, count in counts.items()}


def run_baseline(args: argparse.Namespace) -> dict[str, Any]:
    split_column = SPLIT_COLUMNS[args.split]
    data_path = config.PROCESSED / "network1_v1.parquet"
    smiles_path = config.INTERIM / "compounds_standardized.parquet"
    manifest_path = config.REPORTS / "week2" / "network1_v1_manifest.json"

    for path in (data_path, smiles_path, manifest_path):
        if not path.exists():
            raise SystemExit(f"Required local input is missing: {path}")

    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    required_columns = [
        "pik", "accession", "family_l1", "label", "scaffold_group", "year", split_column
    ]
    full = pd.read_parquet(data_path, columns=required_columns)
    if len(full) != int(manifest["rows"]):
        raise SystemExit(
            f"Network 1 row count does not match manifest: {len(full):,} vs "
            f"{int(manifest['rows']):,}. Validate data before training."
        )
    full = full.loc[full[split_column].isin(PARTITIONS)].copy()
    available_counts = {part: int(full[split_column].eq(part).sum()) for part in PARTITIONS}

    integrity = validate_split_integrity(full, args.split)
    failed = [name for name, passed in integrity.items() if not passed]
    if failed:
        raise SystemExit(f"Split integrity checks failed for {args.split}: {failed}")

    limits = {
        "train": args.max_train_rows,
        "calib": args.max_calib_rows,
        "test": args.max_test_rows,
    }
    sampled: dict[str, pd.DataFrame] = {}
    for offset, part in enumerate(PARTITIONS):
        sampled[part] = stratified_cap(
            full.loc[full[split_column].eq(part)], limits[part], args.seed + offset
        )
        if sampled[part]["label"].nunique() != 2:
            raise SystemExit(f"Sampled {part} partition does not contain both labels.")
    del full

    selected = pd.concat([sampled[p] for p in PARTITIONS], ignore_index=True)
    compound_keys = selected["pik"].astype(str).tolist()
    key_set = set(compound_keys)
    compounds = pd.read_parquet(
        smiles_path, columns=["parent_inchikey", "parent_smiles", "status"]
    )
    compounds = compounds.loc[
        compounds["status"].eq("ok")
        & compounds["parent_inchikey"].notna()
        & compounds["parent_smiles"].notna()
    ].drop_duplicates("parent_inchikey")
    compounds["parent_inchikey"] = compounds["parent_inchikey"].astype(str)
    smiles_by_key = dict(zip(compounds["parent_inchikey"], compounds["parent_smiles"]))
    missing = sorted(key_set - set(smiles_by_key))
    if missing:
        raise SystemExit(
            f"{len(missing)} sampled compounds lack standardized SMILES; examples: {missing[:5]}"
        )

    feature_start = time.perf_counter()
    fingerprints, key_to_row = build_morgan_matrix(
        compound_keys, smiles_by_key, radius=args.radius, n_bits=args.fp_bits
    )
    del compounds, smiles_by_key, selected

    family_encoder = OneHotEncoder(
        handle_unknown="ignore", sparse_output=True, dtype=np.float32
    )
    family_values = {
        part: sampled[part][["family_l1"]].fillna("UNCLASSIFIED").astype(str)
        for part in PARTITIONS
    }
    family_train = family_encoder.fit_transform(family_values["train"])
    features: dict[str, csr_matrix] = {}
    for part in PARTITIONS:
        indexes = np.fromiter(
            (key_to_row[str(key)] for key in sampled[part]["pik"]),
            dtype=np.int32,
            count=len(sampled[part]),
        )
        fp_part = fingerprints[indexes]
        family_part = (
            family_train if part == "train" else family_encoder.transform(family_values[part])
        )
        features[part] = hstack([fp_part, family_part], format="csr", dtype=np.float32)
    feature_seconds = time.perf_counter() - feature_start

    y: dict[str, np.ndarray] = {}
    for part in PARTITIONS:
        encoded = sampled[part]["label"].map(LABEL_TO_INT)
        if encoded.isna().any():
            raise SystemExit(
                f"Unexpected labels in {part}: "
                f"{sampled[part].loc[encoded.isna(), 'label'].unique().tolist()}"
            )
        y[part] = encoded.to_numpy(dtype=np.int8)

    model = LogisticRegression(
        solver="liblinear",
        class_weight="balanced",
        max_iter=args.max_iter,
        random_state=args.seed,
    )
    start = time.perf_counter()
    model.fit(features["train"], y["train"])
    fit_seconds = time.perf_counter() - start
    if list(model.classes_) != [0, 1]:
        raise RuntimeError(f"Unexpected class order: {model.classes_}")

    p_cal = model.predict_proba(features["calib"])
    p_test = model.predict_proba(features["test"])
    p_active = p_test[:, 1]
    sets, quantile = split_conformal_prediction_sets(p_cal, y["calib"], p_test, args.alpha)
    y_test = y["test"]
    sizes = sets.sum(axis=1).astype(int)
    covered = sets[np.arange(len(y_test)), y_test]

    predictions = sampled["test"][["pik", "accession", "family_l1", "label"]].copy()
    predictions["p_active"] = p_active.astype(float)
    predictions["predicted_label"] = np.where(p_active >= 0.5, "ACTIVE", "INACTIVE")
    predictions["conformal_set"] = [
        "|".join(INT_TO_LABEL[i] for i, included in enumerate(row) if included) or "EMPTY"
        for row in sets
    ]
    predictions["conformal_set_size"] = sizes
    predictions["split"] = args.split

    output_dir = config.REPORTS / "model_baseline"
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = config.PROCESSED / f"dti_baseline_{args.split}_morgan_family.joblib"
    metrics_path = output_dir / f"baseline_metrics_{args.split}_morgan_family.json"
    predictions_path = output_dir / f"baseline_predictions_{args.split}_morgan_family.csv"
    joblib.dump(
        {
            "classifier": model,
            "family_encoder": family_encoder,
            "feature_method": "Morgan binary fingerprints + one-hot family_l1",
            "morgan_radius": args.radius,
            "morgan_bits": args.fp_bits,
            "label_to_int": LABEL_TO_INT,
            "split": args.split,
            "seed": args.seed,
        },
        model_path,
    )
    predictions.to_csv(predictions_path, index=False)

    metrics = {
        "project": "TrustDTI",
        "baseline": "Morgan fingerprints + protein-family one-hot + logistic regression",
        "split": args.split,
        "split_column": split_column,
        "seed": args.seed,
        "network1_manifest_rows": int(manifest["rows"]),
        "available_partition_rows": available_counts,
        "sampled_partition_label_counts": {part: label_counts(sampled[part]) for part in PARTITIONS},
        "sample_caps": limits,
        "actual_partition_rows": {part: len(sampled[part]) for part in PARTITIONS},
        "split_integrity_checks": integrity,
        "split_integrity_passed": all(integrity.values()),
        "features": {
            "compound": f"RDKit Morgan binary fingerprint, radius={args.radius}, bits={args.fp_bits}",
            "protein": "family_l1 one-hot; no protein sequence or identity embedding",
            "total_sparse_dimension": int(features["train"].shape[1]),
        },
        "model": {
            "estimator": "sklearn LogisticRegression",
            "solver": "liblinear",
            "class_weight": "balanced",
            "max_iter": args.max_iter,
            "classification_threshold": 0.5,
        },
        "test_metrics": metric_summary(y_test, p_active),
        "conformal_diagnostic": {
            "alpha": args.alpha,
            "calibration_nonconformity_quantile": quantile,
            "empirical_test_coverage": float(covered.mean()),
            "mean_prediction_set_size": float(sizes.mean()),
            "empty_set_count": int((sizes == 0).sum()),
            "singleton_set_count": int((sizes == 1).sum()),
            "two_label_set_count": int((sizes == 2).sum()),
            "interpretation": (
                "Empirical split-conformal-style diagnostic. Formal coverage relies on "
                "exchangeability; pair dependence and distribution shift in group/temporal "
                "splits may violate assumptions. No coverage guarantee is claimed here."
            ),
        },
        "timing_seconds": {
            "feature_building": round(feature_seconds, 3),
            "model_fit": round(fit_seconds, 3),
        },
        "output_paths": {
            "metrics": str(metrics_path),
            "predictions": str(predictions_path),
            "model_artifact_gitignored": str(model_path),
        },
        "limitations": [
            "This is a classical baseline, not the pretrained embedding fusion model.",
            "Metrics describe stratified row-capped samples unless the caps include each full partition.",
            "Family-only target features limit target-specific biological information.",
            "The prediction-set coverage is empirical and not a formal guarantee under unverified exchangeability.",
        ],
    }
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print("\nRESULT: BASELINE RUN COMPLETED")
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=tuple(SPLIT_COLUMNS), default="random")
    parser.add_argument("--max-train-rows", type=int, default=50_000)
    parser.add_argument("--max-calib-rows", type=int, default=10_000)
    parser.add_argument("--max-test-rows", type=int, default=20_000)
    parser.add_argument("--radius", type=int, default=2)
    parser.add_argument("--fp-bits", type=int, default=2048)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--max-iter", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    for name in ("max_train_rows", "max_calib_rows", "max_test_rows"):
        if getattr(args, name) < 0:
            parser.error(f"--{name.replace('_', '-')} must be non-negative.")
    if args.radius < 0 or args.fp_bits < 64 or args.max_iter < 1:
        parser.error("Require radius >= 0, fp-bits >= 64, and max-iter >= 1.")
    if not 0.0 < args.alpha < 1.0:
        parser.error("--alpha must be strictly between 0 and 1.")
    return args


def main() -> None:
    metrics = run_baseline(parse_args())
    print(f"Saved metrics to {metrics['output_paths']['metrics']}")


if __name__ == "__main__":
    main()
