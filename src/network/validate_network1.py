
"""Validate the local Network 1 dataset against its committed manifest."""

import json

import pandas as pd
import pyarrow.parquet as pq

from src import config


DATA_PATH = config.PROCESSED / "network1_v1.parquet"
MANIFEST_PATH = config.REPORTS / "week2" / "network1_v1_manifest.json"

COLUMNS = [
    "pik",
    "label",
    "split_random",
    "split_drugcold",
    "split_targetcold",
    "split_temporal",
    "scaffold_group",
    "accession",
    "year",
]


def check(name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    suffix = f" — {details}" if details else ""
    print(f"[{status}] {name}{suffix}")
    return bool(passed)


def counts(series):
    """Return counts as ordinary strings and integers, including missing values."""
    result = series.astype("string").fillna("<NA>").value_counts()
    return {str(key): int(value) for key, value in result.items()}


def group_overlaps(df, split_column, group_column):
    """Count overlap between train, calibration and test groups."""
    groups = {
        part: set(
            df.loc[df[split_column].eq(part), group_column]
            .dropna()
            .astype(str)
        )
        for part in ("train", "calib", "test")
    }
    return {
        "train-test": len(groups["train"] & groups["test"]),
        "calib-test": len(groups["calib"] & groups["test"]),
        "train-calib": len(groups["train"] & groups["calib"]),
    }


def main():
    if not DATA_PATH.exists():
        raise SystemExit(f"Dataset not found: {DATA_PATH}")
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"Manifest not found: {MANIFEST_PATH}")

    with MANIFEST_PATH.open(encoding="utf-8") as file:
        manifest = json.load(file)

    parquet = pq.ParquetFile(DATA_PATH)
    schema = set(parquet.schema.names)
    missing = sorted(set(COLUMNS) - schema)

    if missing:
        raise SystemExit(f"Required columns missing from dataset: {missing}")

    df = pd.read_parquet(DATA_PATH, columns=COLUMNS)
    results = []

    print("\n=== Network 1 validation ===")
    results.append(check(
        "Dataset row count matches manifest",
        len(df) == manifest["rows"],
        f"actual={len(df):,}, expected={manifest['rows']:,}",
    ))

    actual_labels = counts(df["label"])
    expected_labels = manifest["label_counts"]
    results.append(check(
        "Label counts match manifest",
        actual_labels == expected_labels,
        f"actual={actual_labels}",
    ))

    for column, expected in manifest["split_distributions"].items():
        actual = counts(df[column])
        results.append(check(
            f"{column} counts match manifest",
            actual == expected,
            f"actual={actual}",
        ))

    duplicate_pairs = int(df.duplicated(["pik", "accession"]).sum())
    results.append(check(
        "One row per compound-protein pair",
        duplicate_pairs == 0,
        f"duplicate pairs={duplicate_pairs:,}",
    ))

    for split_column, group_column, description in [
        ("split_drugcold", "scaffold_group", "Drug-cold scaffold separation"),
        ("split_targetcold", "accession", "Target-cold protein separation"),
    ]:
        overlaps = group_overlaps(df, split_column, group_column)
        results.append(check(
            description,
            all(value == 0 for value in overlaps.values()),
            f"overlaps={overlaps}",
        ))

    temporal_split = df["split_temporal"].astype("string")
    years = pd.to_numeric(df["year"], errors="coerce")
    cutoff = manifest["params"]["temporal_cutoff"]

    unassigned = temporal_split.isna()
    missing_year = years.isna()
    results.append(check(
        "Unassigned temporal rows match missing publication years",
        bool((unassigned == missing_year).all()),
        f"unassigned={int(unassigned.sum()):,}, missing years={int(missing_year.sum()):,}",
    ))

    for part in ("train", "calib"):
        mask = temporal_split.eq(part).fillna(False)
        subset = years[mask].dropna()
        valid = (
            len(subset) == int(mask.sum())
            and len(subset) > 0
            and subset.max() < cutoff
        )
        results.append(check(
            f"Temporal {part} years precede cutoff",
            bool(valid),
            f"cutoff={cutoff}",
        ))

    test_mask = temporal_split.eq("test").fillna(False)
    test_years = years[test_mask].dropna()
    temporal_test_valid = (
        len(test_years) == int(test_mask.sum())
        and len(test_years) > 0
        and test_years.min() >= cutoff
    )
    results.append(check(
        "Temporal test years meet cutoff",
        bool(temporal_test_valid),
        f"cutoff={cutoff}",
    ))

    print(f"\nResult: {sum(results)}/{len(results)} checks passed.")
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
