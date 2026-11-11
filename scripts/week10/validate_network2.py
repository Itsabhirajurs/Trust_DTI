from __future__ import annotations

"""Validate source-specific and overall-direct Network 2 tables independently."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd


BRIDGE_PATH = PROJECT_ROOT / "outputs/week09_network2/uniprot_opentargets_primary_bridge.csv"
SOURCE_PATH = PROJECT_ROOT / "data/processed/network2_direct_associations.parquet"
OVERALL_PATH = PROJECT_ROOT / "data/processed/network2_overall_direct.parquet"
OUTPUT_PATH = PROJECT_ROOT / "outputs/week10/network2_validation_audit.json"


def _score_summary(series: pd.Series) -> dict[str, Any]:
    values = pd.to_numeric(series, errors="coerce")
    finite = values.dropna()
    out_of_range = int(((finite < 0) | (finite > 1)).sum())
    return {
        "rows": int(len(values)),
        "null_or_non_numeric": int(values.isna().sum()),
        "minimum": float(finite.min()) if len(finite) else None,
        "maximum": float(finite.max()) if len(finite) else None,
        "out_of_range_0_1": out_of_range,
    }


def _mapping_audit(frame: pd.DataFrame, bridge: pd.DataFrame) -> dict[str, Any]:
    expected = bridge.set_index("uniprot_accession")["ensembl_gene_id"].to_dict()
    mapped = frame["uniprot_accession"].astype(str).map(expected)
    observed = frame["targetId"].astype(str)
    mismatch = mapped.isna() | observed.ne(mapped)
    unknown_accession = mapped.isna()
    return {
        "rows": int(len(frame)),
        "unknown_uniprot_accession_rows": int(unknown_accession.sum()),
        "uniprot_to_target_mismatch_rows": int(mismatch.sum()),
        "unique_uniprot_accessions": int(frame["uniprot_accession"].nunique()),
        "unique_target_ids": int(frame["targetId"].nunique()),
    }


def validate_frames(
    source: pd.DataFrame,
    overall: pd.DataFrame,
    bridge: pd.DataFrame,
) -> dict[str, Any]:
    required_bridge = {"uniprot_accession", "ensembl_gene_id"}
    required_source = {
        "targetId", "diseaseId", "aggregationType", "aggregationValue",
        "associationScore", "evidenceCount", "uniprot_accession",
        "edge_provenance", "opentargets_release",
    }
    required_overall = {
        "targetId", "diseaseId", "aggregationType", "aggregationValue",
        "associationScore", "evidenceCount", "uniprot_accession",
        "edge_provenance", "opentargets_release", "disease_name",
    }
    for name, frame, required in (
        ("bridge", bridge, required_bridge),
        ("source_specific", source, required_source),
        ("overall_direct", overall, required_overall),
    ):
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"{name} input missing required columns: {missing}")

    if bridge["uniprot_accession"].duplicated().any():
        raise ValueError("Primary bridge must have one row per UniProt accession.")
    if bridge["ensembl_gene_id"].duplicated().any():
        raise ValueError("Primary bridge must have one row per Ensembl target ID.")

    bridge_map = bridge[["uniprot_accession", "ensembl_gene_id"]].copy()
    source_mapping = _mapping_audit(source, bridge_map)
    overall_mapping = _mapping_audit(overall, bridge_map)

    source_keys = ["targetId", "diseaseId", "aggregationValue"]
    overall_keys = ["targetId", "diseaseId"]
    source_duplicates = int(source.duplicated(source_keys, keep=False).sum())
    overall_duplicates = int(overall.duplicated(overall_keys, keep=False).sum())

    source_type_counts = (
        source["aggregationType"].fillna("<NULL>").astype(str).value_counts().to_dict()
    )
    source_missing_mask = (
        source["aggregationValue"].isna()
        | source["aggregationValue"].fillna("").astype(str).str.strip().eq("")
    )
    source_missing_source_id = int(source_missing_mask.sum())
    source_provenance_bad = int((source["edge_provenance"] != "curated").sum())
    overall_provenance_bad = int((overall["edge_provenance"] != "curated").sum())
    overall_type_counts = (
        overall["aggregationType"].fillna("<NULL>").astype(str).value_counts().to_dict()
    )
    overall_value_nonempty_mask = (
        overall["aggregationValue"].notna()
        & overall["aggregationValue"].fillna("").astype(str).str.strip().ne("")
    )
    overall_value_nonnull = int(overall_value_nonempty_mask.sum())

    source_releases = set(source["opentargets_release"].dropna().astype(str))
    overall_releases = set(overall["opentargets_release"].dropna().astype(str))

    disease_name_missing_mask = (
        overall["disease_name"].isna()
        | overall["disease_name"].fillna("").astype(str).str.strip().eq("")
    )
    disease_name_missing = int(disease_name_missing_mask.sum())
    source_score = _score_summary(source["associationScore"])
    overall_score = _score_summary(overall["associationScore"])

    checks = {
        "bridge_one_to_one_accession": not bridge["uniprot_accession"].duplicated().any(),
        "bridge_one_to_one_target": not bridge["ensembl_gene_id"].duplicated().any(),
        "source_mapping_consistent": source_mapping["uniprot_to_target_mismatch_rows"] == 0,
        "overall_mapping_consistent": overall_mapping["uniprot_to_target_mismatch_rows"] == 0,
        "source_rows_are_datasource_level": set(source_type_counts).issubset({"datasourceId"}),
        "overall_rows_are_overall": set(overall_type_counts).issubset({"overall"}),
        "overall_aggregation_value_empty": overall_value_nonnull == 0,
        "source_release_is_26_09": source_releases == {"26.09"},
        "overall_release_is_26_09": overall_releases == {"26.09"},
        "source_id_present": source_missing_source_id == 0,
        "source_keys_unique": source_duplicates == 0,
        "overall_target_disease_keys_unique": overall_duplicates == 0,
        "source_score_within_0_1": source_score["out_of_range_0_1"] == 0,
        "overall_score_within_0_1": overall_score["out_of_range_0_1"] == 0,
        "source_provenance_curated": source_provenance_bad == 0,
        "overall_provenance_curated": overall_provenance_bad == 0,
    }
    warnings = []
    if disease_name_missing:
        warnings.append(
            f"{disease_name_missing} overall-direct rows lack a disease name after the metadata join."
        )
    if source_score["null_or_non_numeric"]:
        warnings.append("Some source-specific association scores are null or non-numeric.")
    if overall_score["null_or_non_numeric"]:
        warnings.append("Some overall-direct association scores are null or non-numeric.")

    return {
        "project": "TrustDTI",
        "task": "Network 2 quality validation",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "release": "26.09",
        "checks": checks,
        "all_critical_checks_passed": all(checks.values()),
        "warnings": warnings,
        "bridge": {
            "rows": int(len(bridge)),
            "unique_uniprot_accessions": int(bridge["uniprot_accession"].nunique()),
            "unique_ensembl_ids": int(bridge["ensembl_gene_id"].nunique()),
        },
        "source_specific": {
            **source_mapping,
            "rows_with_duplicate_keys": source_duplicates,
            "aggregation_type_counts": {
                str(key): int(value) for key, value in source_type_counts.items()
            },
            "rows_missing_source_id": source_missing_source_id,
            "rows_with_non_curated_provenance": source_provenance_bad,
            "association_score": source_score,
            "unique_disease_ids": int(source["diseaseId"].nunique()),
            "unique_target_disease_pairs": int(
                source[["targetId", "diseaseId"]].drop_duplicates().shape[0]
            ),
            "datasource_counts": {
                str(key): int(value)
                for key, value in source["aggregationValue"].value_counts().to_dict().items()
            },
        },
        "overall_direct": {
            **overall_mapping,
            "rows_with_duplicate_target_disease_keys": overall_duplicates,
            "aggregation_type_counts": {
                str(key): int(value) for key, value in overall_type_counts.items()
            },
            "rows_with_nonempty_aggregation_value": overall_value_nonnull,
            "rows_with_non_curated_provenance": overall_provenance_bad,
            "rows_missing_disease_name": disease_name_missing,
            "association_score": overall_score,
            "unique_disease_ids": int(overall["diseaseId"].nunique()),
            "unique_target_disease_pairs": int(
                overall[["targetId", "diseaseId"]].drop_duplicates().shape[0]
            ),
        },
        "interpretation": (
            "Source-specific and overall-direct association scores are separate Open Targets "
            "products. They are prioritisation scores, not probabilities or causal proof."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", type=Path, default=BRIDGE_PATH)
    parser.add_argument("--source", type=Path, default=SOURCE_PATH)
    parser.add_argument("--overall", type=Path, default=OVERALL_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    for path in (args.bridge, args.source, args.overall):
        if not path.exists():
            raise SystemExit(f"Required input is missing: {path}")

    bridge = pd.read_csv(args.bridge, dtype=str)
    source_columns = [
        "targetId", "diseaseId", "aggregationType", "aggregationValue",
        "associationScore", "evidenceCount", "uniprot_accession",
        "edge_provenance", "opentargets_release",
    ]
    overall_columns = [
        "targetId", "diseaseId", "aggregationType", "aggregationValue",
        "associationScore", "evidenceCount", "uniprot_accession",
        "edge_provenance", "opentargets_release", "disease_name",
    ]
    source = pd.read_parquet(args.source, columns=source_columns)
    overall = pd.read_parquet(args.overall, columns=overall_columns)
    result = validate_frames(source, overall, bridge)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nSaved validation audit: {args.output}")

    if not result["all_critical_checks_passed"]:
        raise SystemExit("NETWORK 2 VALIDATION FAILED. Review checks and audit.")


if __name__ == "__main__":
    main()
