from __future__ import annotations

"""Evaluate manually annotated retrieval outputs across four matched policies.

Counter-evidence recall is measured only against the pooled, annotated retrieved
corpus for this fixed candidate set. It is not exhaustive literature-corpus recall.
"""

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "outputs/week10/retrieval_annotation_sheet.csv"
DEFAULT_OUTPUT = ROOT / "outputs/week10/retrieval_policy_comparison.json"
DEFAULT_CANDIDATES = ROOT / "data/processed/week10_candidates.csv"
DEFAULT_STRATEGY_KEY = ROOT / "outputs/week10/retrieval_strategy_key.csv"
DEFAULT_STRATEGY_MANIFEST = ROOT / "outputs/week10/retrieval_strategy_manifest.csv"
STRATEGIES = ("fixed", "uncertainty_only", "disease_only", "combined")
VALID_LABELS = {"SUPPORT", "CONTRADICT", "UNKNOWN"}


def expand_blinded_annotations(
    annotations: pd.DataFrame,
    strategy_manifest: pd.DataFrame,
    strategy_key: pd.DataFrame,
) -> pd.DataFrame:
    """Attach blinded article labels to each retrieval-policy exposure."""
    pair_key = ["candidate_id", "record_id"]
    required_annotations = set(pair_key + ["direction_label"])
    required_manifest = set(pair_key + ["strategy_code"])
    required_key = {"strategy_code", "strategy"}

    for name, frame, required in (
        ("annotations", annotations, required_annotations),
        ("strategy manifest", strategy_manifest, required_manifest),
        ("strategy key", strategy_key, required_key),
    ):
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"{name} missing required columns: {missing}")

    if annotations.duplicated(pair_key).any():
        raise ValueError("Blinded worksheet must contain one row per candidate-publication.")
    if strategy_key["strategy_code"].duplicated().any():
        raise ValueError("Strategy key contains duplicate codes.")
    if strategy_manifest.duplicated(pair_key + ["strategy_code"]).any():
        raise ValueError("Strategy manifest contains duplicate candidate-publication-policy rows.")

    strategy_lookup = dict(zip(strategy_key["strategy_code"], strategy_key["strategy"]))
    manifest = strategy_manifest.copy()
    manifest["strategy"] = manifest["strategy_code"].map(strategy_lookup)
    if manifest["strategy"].isna().any() or manifest["strategy"].eq("").any():
        raise ValueError("Strategy manifest contains a code not found in the strategy key.")

    missing_annotations = (
        manifest[pair_key].drop_duplicates()
        .merge(annotations[pair_key], on=pair_key, how="left", indicator=True)
    )
    if missing_annotations["_merge"].eq("left_only").any():
        raise ValueError("Some retrieved candidate-publications are absent from the annotation sheet.")

    orphan_annotations = (
        annotations[pair_key].drop_duplicates()
        .merge(manifest[pair_key].drop_duplicates(), on=pair_key, how="left", indicator=True)
    )
    if orphan_annotations["_merge"].eq("left_only").any():
        raise ValueError("Annotation sheet contains candidate-publications absent from the retrieval manifest.")

    expanded = manifest.merge(
        annotations,
        on=pair_key,
        how="left",
        validate="many_to_one",
    )
    return expanded


def evaluate(frame: pd.DataFrame, budget: int, expected_candidate_count: int | None = None) -> dict:
    required = {"candidate_id", "strategy", "record_id", "direction_label"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Annotation file missing columns: {missing}")

    work = frame.copy()
    work["strategy"] = work["strategy"].astype(str).str.lower()
    work["direction_label"] = work["direction_label"].fillna("").astype(str).str.upper().str.strip()
    unknown_strategies = sorted(set(work["strategy"]) - set(STRATEGIES))
    if unknown_strategies:
        raise ValueError(f"Unexpected strategies: {unknown_strategies}")

    invalid = sorted(set(work["direction_label"]) - (VALID_LABELS | {""}))
    if invalid:
        raise ValueError(f"Invalid direction labels: {invalid}")

    duplicate_key = ["candidate_id", "strategy", "record_id"]
    if work.duplicated(duplicate_key).any():
        raise ValueError("Duplicate candidate-strategy-record rows; deduplicate before evaluation.")

    # A paper's direction must be identical regardless of which policy retrieved it.
    directional = work[work["direction_label"].isin(VALID_LABELS)]
    consistency = directional.groupby(["candidate_id", "record_id"])["direction_label"].nunique()
    if (consistency > 1).any():
        raise ValueError(
            "Conflicting annotations for the same candidate/publication across strategies."
        )

    counts = work.groupby(["candidate_id", "strategy"]).size()
    if not counts.empty and (counts > budget).any():
        raise ValueError("Observed unique document count exceeds the matched per-candidate budget.")

    complete = work[work["direction_label"].isin(VALID_LABELS)].copy()
    pooled_contradictions = (
        complete.loc[complete["direction_label"].eq("CONTRADICT")]
        .groupby("candidate_id")["record_id"]
        .apply(set)
        .to_dict()
    )

    observed_candidate_count = int(work["candidate_id"].nunique())
    candidate_denominator = expected_candidate_count or observed_candidate_count
    if candidate_denominator < observed_candidate_count:
        raise ValueError("Expected candidate count is smaller than observed candidates.")

    results = {}
    for strategy in STRATEGIES:
        subset = work[work["strategy"].eq(strategy)]
        labelled = subset[subset["direction_label"].isin(VALID_LABELS)]
        support = int(labelled["direction_label"].eq("SUPPORT").sum())
        contradict = int(labelled["direction_label"].eq("CONTRADICT").sum())
        unknown = int(labelled["direction_label"].eq("UNKNOWN").sum())
        docs = len(subset)
        denominator = support + contradict + unknown
        counter_retrieved = (
            labelled.loc[labelled["direction_label"].eq("CONTRADICT")]
            .groupby("candidate_id")["record_id"]
            .apply(set)
            .to_dict()
        )
        numerator = 0
        recall_denominator = 0
        for candidate_id, pooled in pooled_contradictions.items():
            recall_denominator += len(pooled)
            numerator += len(counter_retrieved.get(candidate_id, set()) & pooled)

        results[strategy] = {
            "candidate_count_with_any_retrieval": int(subset["candidate_id"].nunique()),
            "candidate_retrieval_coverage": (
                float(subset["candidate_id"].nunique() / candidate_denominator)
                if candidate_denominator else 0.0
            ),
            "retrieved_documents": int(docs),
            "mean_documents_per_candidate_with_retrieval": (
                float(docs / subset["candidate_id"].nunique()) if docs else 0.0
            ),
            "annotation_coverage": float(denominator / docs) if docs else None,
            "relevant_evidence_precision_support_or_contradict": (
                float((support + contradict) / denominator) if denominator else None
            ),
            "support_count": support,
            "contradict_count": contradict,
            "unknown_count": unknown,
            "support_share_of_directional_evidence": (
                float(support / (support + contradict)) if support + contradict else None
            ),
            "counter_evidence_share_of_directional_evidence": (
                float(contradict / (support + contradict)) if support + contradict else None
            ),
            "pooled_candidate_set_counter_evidence_recall": (
                float(numerator / recall_denominator) if recall_denominator else None
            ),
        }

    return {
        "budget_per_candidate": budget,
        "candidate_count_in_annotation_file": observed_candidate_count,
        "candidate_count_in_fixed_pool": candidate_denominator,
        "unique_candidate_publications_in_pool": int(
            work[["candidate_id", "record_id"]].drop_duplicates().shape[0]
        ),
        "total_annotation_rows": int(len(work)),
        "completed_annotation_rows": int(len(complete)),
        "annotation_completion_fraction": float(len(complete) / len(work)) if len(work) else 0.0,
        "strategies": results,
        "interpretation": (
            "Precision is the fraction of annotated retrieved records judged SUPPORT or CONTRADICT. "
            "Pooled candidate-set counter-evidence recall uses the union of CONTRADICT-labelled "
            "records retrieved by these four strategies as its denominator; it is not recall over "
            "all literature. UNKNOWN remains a separate label and is not counted as CONTRADICT."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--budget-per-candidate", type=int, default=10)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--strategy-key", type=Path, default=DEFAULT_STRATEGY_KEY)
    parser.add_argument("--strategy-manifest", type=Path, default=DEFAULT_STRATEGY_MANIFEST)
    args = parser.parse_args()
    if args.budget_per_candidate < 0:
        parser.error("budget must be non-negative.")
    if not args.input.exists():
        raise SystemExit(f"Annotation file not found: {args.input}")
    frame = pd.read_csv(args.input, dtype=str).fillna("")
    if "strategy" not in frame.columns:
        if not args.strategy_key.exists() or not args.strategy_manifest.exists():
            raise SystemExit(
                "Blinded annotation worksheet requires both the strategy key and "
                "retrieval strategy manifest. Keep them private until annotation is complete."
            )
        key = pd.read_csv(args.strategy_key, dtype=str).fillna("")
        manifest = pd.read_csv(args.strategy_manifest, dtype=str).fillna("")
        frame = expand_blinded_annotations(frame, manifest, key)
    expected_candidate_count = None
    if args.candidates.exists():
        expected_candidate_count = len(pd.read_csv(args.candidates))
    result = evaluate(
        frame,
        args.budget_per_candidate,
        expected_candidate_count=expected_candidate_count,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
