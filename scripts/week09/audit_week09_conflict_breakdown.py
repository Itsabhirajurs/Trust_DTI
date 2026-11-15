
from pathlib import Path
import pandas as pd

# ============================================================
# 1. LOAD DATA
# ============================================================

summary = pd.read_csv(
    "outputs/week09_compound_conflict_audit/"
    "compound_conflict_summary.csv"
)

network1 = pd.read_parquet(
    "data/processed/network1_v1.parquet"
)

compounds = pd.read_parquet(
    "data/interim/compounds_standardized.parquet"
)

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

network1["is_conflict"] = (
    network1["pik_clean"].isin(conflict_ids)
)

print("=" * 65)
print("WEEK 09: CONFLICT BREAKDOWN")
print("=" * 65)


# ============================================================
# 2. CORRECT UNIQUE COMPOUND COUNTS PER FOLD
# ============================================================

split_columns = [
    "split_random",
    "split_drugcold",
    "split_targetcold",
    "split_temporal",
]

for split_col in split_columns:

    print("\n" + "-" * 65)
    print("SPLIT:", split_col)
    print("-" * 65)

    rows = []

    for fold, group in network1.groupby(
        split_col,
        dropna=False
    ):

        affected = group[group["is_conflict"]]

        rows.append({
            "fold": (
                "<UNASSIGNED>"
                if pd.isna(fold)
                else str(fold)
            ),
            "total_rows": len(group),
            "affected_rows": len(affected),
            "unique_compounds": group["pik_clean"].nunique(),
            "affected_unique_compounds": (
                affected["pik_clean"].nunique()
            ),
            "affected_percentage": (
                len(affected) / len(group) * 100
                if len(group) else 0
            ),
        })

    print(
        pd.DataFrame(rows)
        .round(5)
        .to_string(index=False)
    )

    # Check whether a compound appears in multiple folds.
    assigned = network1[
        network1["is_conflict"]
        & network1[split_col].notna()
    ]

    membership = (
        assigned.groupby("pik_clean")[split_col]
        .nunique()
    )

    multi_fold = membership[membership > 1]

    print(
        "\nConflicting compounds appearing in multiple "
        "assigned folds:",
        len(multi_fold)
    )


# ============================================================
# 3. LABEL DISTRIBUTION
# ============================================================

print("\n" + "=" * 65)
print("LABEL DISTRIBUTION")
print("=" * 65)

label_counts = pd.crosstab(
    network1["label"],
    network1["is_conflict"],
    margins=True
)

label_counts.columns = [
    "Unaffected",
    "Affected",
    "Total"
]

print(label_counts)

print("\nColumn-wise percentages:")

print(
    pd.crosstab(
        network1["label"],
        network1["is_conflict"],
        normalize="columns"
    ).mul(100).round(3)
)


# ============================================================
# 4. PROVENANCE DISTRIBUTION
# ============================================================

print("\n" + "=" * 65)
print("PROVENANCE OF AFFECTED OBSERVATIONS")
print("=" * 65)

affected = network1[network1["is_conflict"]].copy()

print(
    affected["provenance"]
    .value_counts(dropna=False)
    .to_string()
)


# ============================================================
# 5. CHECK HOW MANY CONFLICTS ENTER THE BASELINE MODEL
# ============================================================

print("\n" + "=" * 65)
print("BASELINE MODEL EXPOSURE")
print("=" * 65)

valid_compounds = compounds[
    (compounds["status"] == "ok")
    & compounds["parent_inchikey"].notna()
    & compounds["parent_smiles"].notna()
].copy()

valid_compounds["key_clean"] = (
    valid_compounds["parent_inchikey"]
    .astype("string")
    .str.strip()
    .str.upper()
)

# Reproduce the existing model's first-row selection.
model_compound_map = valid_compounds.drop_duplicates(
    "parent_inchikey"
)

model_keys = set(model_compound_map["key_clean"])

represented_conflicts = conflict_ids.intersection(model_keys)

print(
    "Total conflicting compounds:",
    len(conflict_ids)
)

print(
    "Conflicting compounds retained after status filtering:",
    len(represented_conflicts)
)

print(
    "Conflicting compounds missing from baseline map:",
    len(conflict_ids - model_keys)
)

print(
    "\nNote: This reproduces the existing first-row selection "
    "policy; it does not change the model."
)


# ============================================================
# 6. COMPOUND-LEVEL OBSERVATION COUNTS
# ============================================================

print("\n" + "=" * 65)
print("MOST FREQUENTLY AFFECTED COMPOUNDS")
print("=" * 65)

compound_impact = (
    affected.groupby("pik_clean")
    .agg(
        observations=("pik_clean", "size"),
        distinct_targets=("accession", "nunique"),
        active_observations=(
            "label",
            lambda x: (x == "ACTIVE").sum()
        ),
        inactive_observations=(
            "label",
            lambda x: (x == "INACTIVE").sum()
        ),
        first_year=("year", "min"),
        last_year=("year", "max"),
    )
    .sort_values("observations", ascending=False)
)

print(compound_impact.head(15).to_string())


# ============================================================
# 7. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 65)
print("BREAKDOWN COMPLETE")
print("=" * 65)

print("Affected observations:", len(affected))
print(
    "Affected distinct compounds:",
    affected["pik_clean"].nunique()
)
print("Results are read-only; no project data was modified.")
