
"""
TrustDTI Week 09: Controlled InChI normalization sensitivity experiment.

Branch A:
    Existing first-selected standardized SMILES.

Branch B:
    Standard InChI round-trip representation for the 95
    identified conflicting compound mappings.

Both branches use the original baseline's sampling, split validation,
Morgan fingerprint builder, protein encoding, classifier and metrics.

This script does NOT modify the existing baseline implementation.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time

from pathlib import Path

# ============================================================
# 1. PROJECT PATH AND IMPORTS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from rdkit import Chem
from rdkit.Chem import inchi, rdFingerprintGenerator

from scipy.sparse import hstack

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder

from src import config

from src.model.evaluate_dti_baseline import (
    SPLIT_COLUMNS,
    PARTITIONS,
    LABEL_TO_INT,
    INT_TO_LABEL,
    stratified_cap,
    validate_split_integrity,
    build_morgan_matrix,
    metric_summary,
    split_conformal_prediction_sets,
)


# ============================================================
# 2. EXPERIMENT CONFIGURATION
# ============================================================

CONFLICT_SUMMARY_PATH = (
    ROOT
    / "outputs"
    / "week09_compound_conflict_audit"
    / "compound_conflict_summary.csv"
)

OUTPUT_DIR = (
    config.PROCESSED
    / "week09_inchi_sensitivity"
)


# ============================================================
# 3. LOAD AND VALIDATE CONFLICT IDENTIFIERS
# ============================================================

def load_conflict_ids() -> set[str]:

    if not CONFLICT_SUMMARY_PATH.exists():
        raise FileNotFoundError(
            f"Missing conflict summary: {CONFLICT_SUMMARY_PATH}"
        )

    summary = pd.read_csv(
        CONFLICT_SUMMARY_PATH,
        usecols=["parent_inchikey"],
        dtype={"parent_inchikey": "string"},
    )

    conflict_ids = set(
        summary["parent_inchikey"]
        .dropna()
        .str.strip()
        .str.upper()
    )

    if len(conflict_ids) != 95:
        raise ValueError(
            f"Expected 95 conflicting compounds; found "
            f"{len(conflict_ids)}."
        )

    return conflict_ids


# ============================================================
# 4. REPRODUCE ORIGINAL BASELINE COMPOUND MAPPING
# ============================================================

def load_original_mapping():

    smiles_path = (
        config.INTERIM / "compounds_standardized.parquet"
    )

    if not smiles_path.exists():
        raise FileNotFoundError(smiles_path)

    compounds = pd.read_parquet(
        smiles_path,
        columns=[
            "parent_inchikey",
            "parent_smiles",
            "status",
        ],
    )

    # Reproduce the original baseline filtering exactly.
    valid = compounds.loc[
        compounds["status"].eq("ok")
        & compounds["parent_inchikey"].notna()
        & compounds["parent_smiles"].notna()
    ].copy()

    # Branch A: reproduce the original first-row selection.
    baseline_compounds = valid.drop_duplicates(
        "parent_inchikey"
    ).copy()

    baseline_compounds["parent_inchikey"] = (
        baseline_compounds["parent_inchikey"].astype(str)
    )

    smiles_by_key = dict(
        zip(
            baseline_compounds["parent_inchikey"],
            baseline_compounds["parent_smiles"],
        )
    )

    return valid, smiles_by_key


# ============================================================
# 5. VALIDATE ALL 95 INCHI ROUND-TRIPS
# ============================================================

def build_normalized_mapping(
    valid_compounds: pd.DataFrame,
    original_mapping: dict[str, str],
    conflict_ids: set[str],
    radius: int,
    n_bits: int,
):
    """
    Independently validate all alternative SMILES representations.

    For every conflicting compound:
        1. Parse original SMILES.
        2. Generate Standard InChI.
        3. Reconstruct molecule from InChI.
        4. Verify reconstructed InChIKey.
        5. Generate canonical isomeric SMILES.
        6. Verify all representations converge.
    """

    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=radius,
        fpSize=n_bits,
    )

    valid = valid_compounds.copy()

    valid["_key"] = (
        valid["parent_inchikey"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    normalized_mapping = original_mapping.copy()

    validation_records = []

    total_structures = 0

    for key in sorted(conflict_ids):

        if key not in original_mapping:
            raise ValueError(
                f"Conflict identifier missing from baseline mapping: {key}"
            )

        group = valid.loc[
            valid["_key"].eq(key)
        ]

        unique_smiles = (
            group["parent_smiles"]
            .drop_duplicates()
            .tolist()
        )

        if len(unique_smiles) < 2:
            raise ValueError(
                f"Expected multiple SMILES for {key}; "
                f"found {len(unique_smiles)}."
            )

        original_inchis = set()
        reconstructed_inchis = set()
        reconstructed_keys = set()
        canonical_smiles = set()
        fingerprint_bits = set()

        selected_roundtrip_smiles = None

        for smiles in unique_smiles:

            molecule = Chem.MolFromSmiles(smiles)

            if molecule is None:
                raise ValueError(
                    f"SMILES parsing failed for {key}"
                )

            # Original Standard InChI and InChIKey.
            standard_inchi = inchi.MolToInchi(molecule)

            generated_key = inchi.MolToInchiKey(molecule)

            if generated_key != key:
                raise ValueError(
                    f"Original InChIKey mismatch for {key}: "
                    f"{generated_key}"
                )

            original_inchis.add(standard_inchi)

            # Reconstruct from Standard InChI.
            reconstructed = inchi.MolFromInchi(
                standard_inchi
            )

            if reconstructed is None:
                raise ValueError(
                    f"InChI reconstruction failed for {key}"
                )

            reconstructed_inchi = inchi.MolToInchi(
                reconstructed
            )

            reconstructed_key = inchi.MolToInchiKey(
                reconstructed
            )

            if reconstructed_key != key:
                raise ValueError(
                    f"Reconstructed InChIKey mismatch for {key}"
                )

            reconstructed_inchis.add(
                reconstructed_inchi
            )

            reconstructed_keys.add(
                reconstructed_key
            )

            # Canonical isomeric SMILES.
            smiles_normalized = Chem.MolToSmiles(
                reconstructed,
                canonical=True,
                isomericSmiles=True,
            )

            canonical_smiles.add(
                smiles_normalized
            )

            if smiles == original_mapping[key]:
                selected_roundtrip_smiles = (
                    smiles_normalized
                )

            # Morgan fingerprint verification.
            fingerprint = generator.GetFingerprint(
                reconstructed
            )

            fingerprint_bits.add(
                fingerprint.ToBitString()
            )

            total_structures += 1

        # All representations must converge for this compound.
        checks = {
            "one_standard_inchi": len(original_inchis) == 1,
            "one_reconstructed_inchi": (
                len(reconstructed_inchis) == 1
            ),
            "one_reconstructed_key": (
                len(reconstructed_keys) == 1
            ),
            "one_canonical_smiles": (
                len(canonical_smiles) == 1
            ),
            "one_morgan_fingerprint": (
                len(fingerprint_bits) == 1
            ),
        }

        failed = [
            name for name, passed in checks.items()
            if not passed
        ]

        if failed:
            raise ValueError(
                f"Normalization validation failed for {key}: {failed}"
            )

        if selected_roundtrip_smiles is None:
            raise ValueError(
                f"Original selected SMILES missing for {key}"
            )

        # Branch B changes only the conflicting compound.
        normalized_mapping[key] = selected_roundtrip_smiles

        validation_records.append({

            "parent_inchikey": key,

            "distinct_input_smiles": len(unique_smiles),

            "all_generated_keys_match": True,

            "standard_inchi_identical": True,

            "canonical_smiles_identical": True,

            "morgan_fingerprints_identical": True,

        })

    if len(validation_records) != 95:
        raise RuntimeError(
            "Not all 95 conflicting compounds were validated."
        )

    return (
        normalized_mapping,
        validation_records,
        total_structures,
    )


# ============================================================
# 6. LOAD DATA AND REPRODUCE ORIGINAL SPLIT SAMPLING
# ============================================================

def prepare_experiment(args):

    split_column = SPLIT_COLUMNS[args.split]

    data_path = (
        config.PROCESSED / "network1_v1.parquet"
    )

    manifest_path = (
        config.REPORTS
        / "week2"
        / "network1_v1_manifest.json"
    )

    smiles_path = (
        config.INTERIM
        / "compounds_standardized.parquet"
    )

    for path in [
        data_path,
        manifest_path,
        smiles_path,
    ]:

        if not path.exists():
            raise FileNotFoundError(path)

    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    required_columns = [
        "pik",
        "accession",
        "family_l1",
        "label",
        "scaffold_group",
        "year",
        split_column,
    ]

    full = pd.read_parquet(
        data_path,
        columns=required_columns,
    )

    if len(full) != int(manifest["rows"]):
        raise ValueError(
            "Network 1 row count does not match manifest."
        )

    full = full.loc[
        full[split_column].isin(PARTITIONS)
    ].copy()

    available_counts = {
        part: int(full[split_column].eq(part).sum())
        for part in PARTITIONS
    }

    # Existing split-integrity validation.
    integrity = validate_split_integrity(
        full,
        args.split,
    )

    failed = [
        name for name, passed in integrity.items()
        if not passed
    ]

    if failed:
        raise ValueError(
            f"Split integrity checks failed: {failed}"
        )

    # Same sample caps and same random seed offsets.
    limits = {
        "train": args.max_train_rows,
        "calib": args.max_calib_rows,
        "test": args.max_test_rows,
    }

    sampled = {}

    for offset, part in enumerate(PARTITIONS):

        sampled[part] = stratified_cap(
            full.loc[full[split_column].eq(part)],
            limits[part],
            args.seed + offset,
        )

        if sampled[part]["label"].nunique() != 2:
            raise ValueError(
                f"Sampled {part} partition does not contain "
                "both labels."
            )

    return (
        sampled,
        limits,
        available_counts,
        integrity,
        manifest,
    )


# ============================================================
# 7. CREATE IDENTICAL PROTEIN FEATURES FOR BOTH BRANCHES
# ============================================================

def build_feature_matrices(
    sampled,
    smiles_by_key,
    normalized_mapping,
    args,
):

    selected = pd.concat(
        [sampled[part] for part in PARTITIONS],
        ignore_index=True,
    )

    compound_keys = (
        selected["pik"].astype(str).tolist()
    )

    key_set = set(compound_keys)

    missing_a = key_set - set(smiles_by_key)
    missing_b = key_set - set(normalized_mapping)

    if missing_a or missing_b:

        raise ValueError(
            f"Missing compound mappings: "
            f"Branch A={len(missing_a)}, Branch B={len(missing_b)}"
        )

    # Existing baseline Morgan fingerprint builder.
    fingerprints_a, key_to_row_a = build_morgan_matrix(
        compound_keys,
        smiles_by_key,
        radius=args.radius,
        n_bits=args.fp_bits,
    )

    fingerprints_b, key_to_row_b = build_morgan_matrix(
        compound_keys,
        normalized_mapping,
        radius=args.radius,
        n_bits=args.fp_bits,
    )

    if key_to_row_a != key_to_row_b:
        raise RuntimeError(
            "Compound fingerprint row mappings differ."
        )

    # Quantify how many sampled compound fingerprints changed.
    difference = fingerprints_a != fingerprints_b

    changed_fingerprint_rows = int(
        np.count_nonzero(
            np.asarray(
                difference.getnnz(axis=1)
            ).reshape(-1)
        )
    )

    changed_fingerprint_bits = int(
        difference.nnz
    )

    sampled_conflicts = (
        key_set.intersection(
            set(normalized_mapping).difference(
                set(smiles_by_key)
            )
        )
    )

    # The conflict IDs are known separately.
    conflict_ids = load_conflict_ids()

    sampled_conflicts = key_set.intersection(conflict_ids)

    # Same family encoder and same training-only fitting.
    family_encoder = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=True,
        dtype=np.float32,
    )

    family_values = {
        part: sampled[part][["family_l1"]]
        .fillna("UNCLASSIFIED")
        .astype(str)
        for part in PARTITIONS
    }

    family_train = family_encoder.fit_transform(
        family_values["train"]
    )

    features_a = {}
    features_b = {}

    for part in PARTITIONS:

        indexes = np.fromiter(
            (
                key_to_row_a[str(key)]
                for key in sampled[part]["pik"]
            ),
            dtype=np.int32,
            count=len(sampled[part]),
        )

        fp_a = fingerprints_a[indexes]
        fp_b = fingerprints_b[indexes]

        family_part = (
            family_train
            if part == "train"
            else family_encoder.transform(
                family_values[part]
            )
        )

        features_a[part] = hstack(
            [fp_a, family_part],
            format="csr",
            dtype=np.float32,
        )

        features_b[part] = hstack(
            [fp_b, family_part],
            format="csr",
            dtype=np.float32,
        )

    # Identical target arrays.
    y = {}

    for part in PARTITIONS:

        encoded = sampled[part]["label"].map(
            LABEL_TO_INT
        )

        if encoded.isna().any():
            raise ValueError(
                f"Unexpected labels in {part}."
            )

        y[part] = encoded.to_numpy(
            dtype=np.int8
        )

    feature_info = {

        "unique_sampled_compounds": len(key_to_row_a),

        "sampled_conflict_compounds": len(
            sampled_conflicts
        ),

        "changed_fingerprint_compounds": (
            changed_fingerprint_rows
        ),

        "changed_fingerprint_bits": (
            changed_fingerprint_bits
        ),

        "branch_a_feature_dimension": (
            features_a["train"].shape[1]
        ),

        "branch_b_feature_dimension": (
            features_b["train"].shape[1]
        ),

    }

    return features_a, features_b, y, feature_info


# ============================================================
# 8. TRAIN AND EVALUATE ONE BRANCH
# ============================================================

def train_and_evaluate(
    branch_name,
    features,
    sampled,
    y,
    args,
):

    print(f"\nTraining {branch_name}...")

    model = LogisticRegression(
        solver="liblinear",
        class_weight="balanced",
        max_iter=args.max_iter,
        random_state=args.seed,
    )

    start = time.perf_counter()

    model.fit(
        features["train"],
        y["train"],
    )

    fit_seconds = time.perf_counter() - start

    if list(model.classes_) != [0, 1]:
        raise RuntimeError(
            f"Unexpected model classes: {model.classes_}"
        )

    p_cal = model.predict_proba(
        features["calib"]
    )

    p_test = model.predict_proba(
        features["test"]
    )

    p_active = p_test[:, 1]

    sets, quantile = split_conformal_prediction_sets(
        p_cal,
        y["calib"],
        p_test,
        args.alpha,
    )

    y_test = y["test"]

    sizes = sets.sum(axis=1).astype(int)

    covered = sets[
        np.arange(len(y_test)),
        y_test,
    ]

    metrics = metric_summary(
        y_test,
        p_active,
    )

    conformal = {

        "alpha": args.alpha,

        "calibration_nonconformity_quantile": (
            float(quantile)
        ),

        "empirical_test_coverage": float(
            covered.mean()
        ),

        "mean_prediction_set_size": float(
            sizes.mean()
        ),

        "empty_set_count": int(
            (sizes == 0).sum()
        ),

        "singleton_set_count": int(
            (sizes == 1).sum()
        ),

        "two_label_set_count": int(
            (sizes == 2).sum()
        ),

    }

    predictions = sampled["test"][
        [
            "pik",
            "accession",
            "family_l1",
            "label",
        ]
    ].copy()

    predictions["p_active"] = p_active.astype(float)

    predictions["predicted_label"] = np.where(
        p_active >= 0.5,
        "ACTIVE",
        "INACTIVE",
    )

    predictions["conformal_set"] = [
        "|".join(
            INT_TO_LABEL[i]
            for i, included in enumerate(row)
            if included
        ) or "EMPTY"
        for row in sets
    ]

    predictions["conformal_set_size"] = sizes

    predictions["split"] = args.split

    result = {

        "branch": branch_name,

        "sample_sizes": {
            part: len(sampled[part])
            for part in PARTITIONS
        },

        "test_metrics": metrics,

        "conformal_diagnostic": conformal,

        "model": {
            "estimator": "LogisticRegression",
            "solver": "liblinear",
            "class_weight": "balanced",
            "max_iter": args.max_iter,
            "random_state": args.seed,
            "threshold": 0.5,
        },

        "fit_seconds": round(
            fit_seconds,
            4,
        ),

    }

    return result, predictions


# ============================================================
# 9. OPTIONAL REPRODUCTION CHECK AGAINST SAVED BASELINE
# ============================================================

def compare_existing_baseline(
    branch_a_result,
    args,
    limits,
):

    reference_path = (
        config.REPORTS
        / "model_baseline"
        / (
            f"baseline_metrics_{args.split}"
            "_morgan_family.json"
        )
    )

    if not reference_path.exists():

        return {
            "available": False,
            "reason": "Existing baseline metrics JSON not found.",
        }

    with reference_path.open(encoding="utf-8") as handle:
        reference = json.load(handle)

    compatible = (
        reference.get("split") == args.split
        and reference.get("seed") == args.seed
        and reference.get("sample_caps") == limits
        and reference.get("model", {}).get("max_iter")
        == args.max_iter
        and reference.get("conformal_diagnostic", {}).get("alpha")
        == args.alpha
        and reference.get("features", {}).get("compound")
        == (
            f"RDKit Morgan binary fingerprint, "
            f"radius={args.radius}, bits={args.fp_bits}"
        )
    )

    if not compatible:

        return {
            "available": True,
            "compatible_configuration": False,
            "reason": (
                "Reference baseline exists, but its "
                "configuration differs from this experiment."
            ),
            "reference_path": str(reference_path),
        }

    reference_metrics = reference["test_metrics"]

    checks = {}

    for name, value in branch_a_result["test_metrics"].items():

        expected = reference_metrics.get(name)

        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isinstance(expected, (int, float))
        ):

            checks[name] = math.isclose(
                float(value),
                float(expected),
                rel_tol=0,
                abs_tol=1e-12,
            )

        else:

            checks[name] = value == expected

    return {

        "available": True,

        "compatible_configuration": True,

        "all_test_metrics_match": all(
            checks.values()
        ),

        "individual_metric_checks": checks,

        "reference_path": str(reference_path),

    }


# ============================================================
# 10. MAIN EXPERIMENT
# ============================================================

def run_experiment(args):

    print("\n" + "=" * 70)
    print("TRUSTDTI WEEK 09: INCHI NORMALIZATION SENSITIVITY")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nStep 1: Loading conflict identifiers...")

    conflict_ids = load_conflict_ids()

    print("Conflicting compounds:", len(conflict_ids))

    print("\nStep 2: Reproducing original compound mapping...")

    valid_compounds, original_mapping = (
        load_original_mapping()
    )

    print(
        "Original baseline compound mappings:",
        len(original_mapping),
    )

    missing_conflicts = (
        conflict_ids - set(original_mapping)
    )

    if missing_conflicts:
        raise ValueError(
            f"{len(missing_conflicts)} conflicting IDs "
            "are missing from original mapping."
        )

    print("\nStep 3: Validating Standard InChI round-trips...")

    (
        normalized_mapping,
        validation_records,
        total_structures,
    ) = build_normalized_mapping(
        valid_compounds,
        original_mapping,
        conflict_ids,
        args.radius,
        args.fp_bits,
    )

    print("Validated compound groups:", len(validation_records))
    print("Validated input structures:", total_structures)

    print("\nStep 4: Preparing identical training samples...")

    (
        sampled,
        limits,
        available_counts,
        integrity,
        manifest,
    ) = prepare_experiment(args)

    print("Available partitions:", available_counts)

    print(
        "Sampled partitions:",
        {
            part: len(sampled[part])
            for part in PARTITIONS
        },
    )

    print("\nStep 5: Building two fingerprint feature sets...")

    (
        features_a,
        features_b,
        y,
        feature_info,
    ) = build_feature_matrices(
        sampled,
        original_mapping,
        normalized_mapping,
        args,
    )

    print("\nFeature comparison:")
    print(json.dumps(feature_info, indent=2))

    # Confirm all non-molecular features have identical dimensions.
    for part in PARTITIONS:

        if (
            features_a[part].shape
            != features_b[part].shape
        ):
            raise RuntimeError(
                f"Feature dimensions differ for {part}."
            )

    print("\nStep 6: Training Branch A...")

    result_a, predictions_a = train_and_evaluate(
        "A_original_first_selected_smiles",
        features_a,
        sampled,
        y,
        args,
    )

    print("\nStep 7: Training Branch B...")

    result_b, predictions_b = train_and_evaluate(
        "B_standard_inchi_roundtrip",
        features_b,
        sampled,
        y,
        args,
    )

    # --------------------------------------------------------
    # Probability-level paired comparison.
    # --------------------------------------------------------

    prob_a = predictions_a["p_active"].to_numpy()

    prob_b = predictions_b["p_active"].to_numpy()

    probability_difference = np.abs(
        prob_a - prob_b
    )

    label_changed = (
        predictions_a["predicted_label"].to_numpy()
        != predictions_b["predicted_label"].to_numpy()
    )

    conformal_changed = (
        predictions_a["conformal_set"].to_numpy()
        != predictions_b["conformal_set"].to_numpy()
    )

    metric_names = [
        "accuracy",
        "balanced_accuracy",
        "precision_active",
        "recall_active",
        "f1_active",
        "roc_auc",
        "average_precision",
        "brier_score",
        "expected_calibration_error_15_bins",
    ]

    metric_differences = {}

    for metric in metric_names:

        value_a = result_a["test_metrics"][metric]

        value_b = result_b["test_metrics"][metric]

        if value_a is None or value_b is None:

            metric_differences[metric] = None

        else:

            metric_differences[metric] = (
                float(value_b) - float(value_a)
            )

    comparison = {

        "test_rows": len(prob_a),

        "mean_absolute_probability_difference": float(
            probability_difference.mean()
        ),

        "maximum_absolute_probability_difference": float(
            probability_difference.max()
        ),

        "predicted_labels_changed": int(
            label_changed.sum()
        ),

        "predicted_label_change_percentage": float(
            label_changed.mean() * 100
        ),

        "conformal_sets_changed": int(
            conformal_changed.sum()
        ),

        "metric_differences_branch_b_minus_branch_a": (
            metric_differences
        ),

    }

    # --------------------------------------------------------
    # Existing baseline reproduction check.
    # --------------------------------------------------------

    baseline_check = compare_existing_baseline(
        result_a,
        args,
        limits,
    )

    # --------------------------------------------------------
    # Save paired predictions.
    # --------------------------------------------------------

    paired = predictions_a[
        [
            "pik",
            "accession",
            "family_l1",
            "label",
        ]
    ].copy()

    paired["p_active_original"] = prob_a

    paired["p_active_inchi_normalized"] = prob_b

    paired["predicted_label_original"] = (
        predictions_a["predicted_label"].to_numpy()
    )

    paired["predicted_label_normalized"] = (
        predictions_b["predicted_label"].to_numpy()
    )

    paired["conformal_set_original"] = (
        predictions_a["conformal_set"].to_numpy()
    )

    paired["conformal_set_normalized"] = (
        predictions_b["conformal_set"].to_numpy()
    )

    paired["absolute_probability_difference"] = (
        probability_difference
    )

    paired["prediction_changed"] = label_changed

    paired["conformal_set_changed"] = conformal_changed

    # --------------------------------------------------------
    # Complete experiment report.
    # --------------------------------------------------------

    report = {

        "project": "TrustDTI",

        "experiment": (
            "Week 09: Standard InChI normalization sensitivity"
        ),

        "split": args.split,

        "seed": args.seed,

        "sample_caps": limits,

        "actual_partition_rows": {
            part: len(sampled[part])
            for part in PARTITIONS
        },

        "available_partition_rows": available_counts,

        "manifest_rows": int(manifest["rows"]),

        "split_integrity": integrity,

        "normalization_validation": {

            "conflict_groups": len(validation_records),

            "input_structures": total_structures,

            "successful_groups": len(validation_records),

            "failed_groups": 0,

        },

        "feature_comparison": feature_info,

        "branch_a": result_a,

        "branch_b": result_b,

        "paired_comparison": comparison,

        "existing_baseline_reproduction_check": (
            baseline_check
        ),

        "limitations": [

            "Only 95 known compound representation conflicts "
            "receive InChI round-trip normalization.",

            "Standard InChI normalization can remove certain "
            "representational distinctions, including undefined "
            "stereochemical information.",

            "Identical fingerprints do not prove identical "
            "biological behaviour.",

            "Results describe sampled partitions unless sample "
            "caps cover the complete partitions.",

            "No improvement in predictive performance is assumed.",

        ],

    }

    # --------------------------------------------------------
    # Save files in gitignored processed-data location.
    # --------------------------------------------------------

    prefix = f"week09_inchi_{args.split}"

    report_path = OUTPUT_DIR / f"{prefix}_metrics.json"

    predictions_path = (
        OUTPUT_DIR / f"{prefix}_paired_predictions.csv"
    )

    validation_path = (
        OUTPUT_DIR / f"{prefix}_normalization_validation.csv"
    )

    with report_path.open("w", encoding="utf-8") as handle:

        json.dump(
            report,
            handle,
            indent=2,
        )

    paired.to_csv(
        predictions_path,
        index=False,
    )

    pd.DataFrame(validation_records).to_csv(
        validation_path,
        index=False,
    )

    # --------------------------------------------------------
    # Print results.
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL EXPERIMENT RESULTS")
    print("=" * 70)

    print("\nBRANCH A: ORIGINAL BASELINE")

    print(
        json.dumps(
            result_a["test_metrics"],
            indent=2,
        )
    )

    print("\nBRANCH B: INCHI NORMALIZED")

    print(
        json.dumps(
            result_b["test_metrics"],
            indent=2,
        )
    )

    print("\nPAIRED COMPARISON")

    print(
        json.dumps(
            comparison,
            indent=2,
        )
    )

    print("\nEXISTING BASELINE REPRODUCTION CHECK")

    print(
        json.dumps(
            baseline_check,
            indent=2,
        )
    )

    print("\nSaved experiment outputs:")

    print(report_path)
    print(predictions_path)
    print(validation_path)

    print("\nEXPERIMENT COMPLETED.")


# ============================================================
# 11. COMMAND-LINE ARGUMENTS
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--split",
        choices=tuple(SPLIT_COLUMNS),
        default="random",
    )

    # Match the earlier 5k / 1k / 2k pilot experiments.
    parser.add_argument(
        "--max-train-rows",
        type=int,
        default=5000,
    )

    parser.add_argument(
        "--max-calib-rows",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--max-test-rows",
        type=int,
        default=2000,
    )

    parser.add_argument(
        "--radius",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--fp-bits",
        type=int,
        default=2048,
    )

    parser.add_argument(
        "--alpha",
        type=float,
        default=0.1,
    )

    parser.add_argument(
        "--max-iter",
        type=int,
        default=200,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    for name in [
        "max_train_rows",
        "max_calib_rows",
        "max_test_rows",
    ]:

        if getattr(args, name) < 0:
            parser.error(
                f"--{name.replace('_', '-')} must be non-negative."
            )

    if (
        args.radius < 0
        or args.fp_bits < 64
        or args.max_iter < 1
    ):

        parser.error(
            "Require radius >= 0, fp-bits >= 64, max-iter >= 1."
        )

    if not 0 < args.alpha < 1:
        parser.error(
            "--alpha must be between 0 and 1."
        )

    return args


# ============================================================
# 12. ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_experiment(parse_args())
