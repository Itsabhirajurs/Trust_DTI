import pandas as pd
from pathlib import Path

# --------------------------------------------------
# Load audit results and Network 1
# --------------------------------------------------

summary_path = Path(
    "outputs/week09_compound_conflict_audit/"
    "compound_conflict_summary.csv"
)

network1_path = Path(
    "data/processed/network1_v1.parquet"
)

summary = pd.read_csv(summary_path)
network1 = pd.read_parquet(network1_path)

# --------------------------------------------------
# Identify conflicting compound IDs
# --------------------------------------------------

conflict_ids = set(
    summary["parent_inchikey"]
    .astype("string")
    .str.strip()
    .str.upper()
)

network1["pik_clean"] = (
    network1["pik"]
    .astype("string")
    .str.strip()
    .str.upper()
)

network1["is_conflicting_compound"] = (
    network1["pik_clean"].isin(conflict_ids)
)

# --------------------------------------------------
# Overall impact
# --------------------------------------------------

total_rows = len(network1)

affected_rows = int(
    network1["is_conflicting_compound"].sum()
)

affected_compounds = (
    network1.loc[
        network1["is_conflicting_compound"],
        "pik_clean"
    ].nunique()
)

print("\n" + "=" * 60)
print("WEEK 09: CONFLICT IMPACT ON NETWORK 1")
print("=" * 60)

print("Total Network 1 observations:", total_rows)
print("Affected observations:", affected_rows)
print("Affected distinct compounds:", affected_compounds)

print(
    "Percentage of observations affected:",
    round(affected_rows / total_rows * 100, 5),
    "%"
)

# --------------------------------------------------
# Impact across all split strategies
# --------------------------------------------------

split_columns = [
    "split_random",
    "split_drugcold",
    "split_targetcold",
    "split_temporal",
]

for split_col in split_columns:

    print("\n" + "-" * 60)
    print("SPLIT:", split_col)
    print("-" * 60)

    result = (
        network1
        .groupby(split_col, dropna=False)
        .agg(
            total_rows=("pik_clean", "size"),
            affected_rows=("is_conflicting_compound", "sum"),
            distinct_compounds=("pik_clean", "nunique"),
            affected_compounds=(
                "is_conflicting_compound",
                "sum"
            ),
        )
    )

    result["affected_percentage"] = (
        result["affected_rows"]
        / result["total_rows"]
        * 100
    )

    print(result.round(4).to_string())

# --------------------------------------------------
# Inspect the nine tautomer disagreements
# --------------------------------------------------

print("\n" + "=" * 60)
print("CANONICAL TAUTOMER DISAGREEMENTS")
print("=" * 60)

tautomer_disagreements = summary[
    ~summary["canonical_tautomers_identical"]
]

print("Total:", len(tautomer_disagreements))

print(
    tautomer_disagreements[
        [
            "parent_inchikey",
            "standard_inchi_count",
            "canonical_tautomer_count",
            "morgan_fingerprint_count",
            "morgan_tanimoto_min",
        ]
    ].to_string(index=False)
)

# --------------------------------------------------
# Inspect the ten lowest fingerprint similarities
# --------------------------------------------------

print("\n" + "=" * 60)
print("TEN LOWEST MORGAN SIMILARITIES")
print("=" * 60)

lowest_similarity = summary.sort_values(
    "morgan_tanimoto_min",
    ascending=True
).head(10)

print(
    lowest_similarity[
        [
            "parent_inchikey",
            "morgan_tanimoto_min",
            "canonical_tautomer_count",
            "morgan_fingerprint_count",
        ]
    ].to_string(index=False)
)