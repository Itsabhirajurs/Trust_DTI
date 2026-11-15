
from pathlib import Path
import pandas as pd

# ============================================================
# 1. LOAD DATA
# ============================================================

compounds = pd.read_parquet(
    "data/interim/compounds_standardized.parquet"
)

network1 = pd.read_parquet(
    "data/processed/network1_v1.parquet"
)

summary = pd.read_csv(
    "outputs/week09_compound_conflict_audit/"
    "compound_conflict_summary.csv"
)

conflict_ids = set(
    summary["parent_inchikey"]
    .astype("string")
    .str.strip()
    .str.upper()
)

# Preserve original row positions.
compounds["source_row"] = range(len(compounds))

# ============================================================
# 2. REPRODUCE BASELINE FILTERING
# ============================================================

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

conflict_rows = valid_compounds[
    valid_compounds["key_clean"].isin(conflict_ids)
].copy()

# Reproduce the baseline's first-row selection.
baseline_map = valid_compounds.drop_duplicates(
    subset=["parent_inchikey"],
    keep="first"
).copy()

baseline_conflicts = baseline_map[
    baseline_map["key_clean"].isin(conflict_ids)
].copy()

# ============================================================
# 3. COUNT OBSERVATIONS PER CONFLICTING COMPOUND
# ============================================================

network1["pik_clean"] = (
    network1["pik"]
    .astype("string")
    .str.strip()
    .str.upper()
)

observation_counts = (
    network1.groupby("pik_clean")
    .agg(
        total_observations=("pik_clean", "size"),
        active_observations=(
            "label",
            lambda x: (x == "ACTIVE").sum()
        ),
        inactive_observations=(
            "label",
            lambda x: (x == "INACTIVE").sum()
        ),
    )
)

# ============================================================
# 4. INSPECT ACTUAL CHOSEN REPRESENTATIONS
# ============================================================

records = []

for key in sorted(conflict_ids):

    group = conflict_rows[
        conflict_rows["key_clean"] == key
    ].sort_values("source_row")

    chosen = baseline_conflicts[
        baseline_conflicts["key_clean"] == key
    ]

    if chosen.empty:
        continue

    selected = chosen.iloc[0]

    obs = observation_counts.loc[key]

    alternative_smiles = (
        group["parent_smiles"]
        .drop_duplicates()
        .tolist()
    )

    records.append({

        "parent_inchikey": key,

        "mapping_rows": len(group),

        "distinct_smiles": (
            group["parent_smiles"].nunique()
        ),

        "distinct_molregno": (
            group["molregno"].nunique()
        ),

        "selected_molregno": selected["molregno"],

        "selected_source_row": selected["source_row"],

        "selected_smiles": selected["parent_smiles"],

        "alternative_smiles": " || ".join(
            str(x)
            for x in alternative_smiles
        ),

        "first_valid_mapping_selected": (
            selected["source_row"]
            == group["source_row"].min()
        ),

        "total_observations": int(
            obs["total_observations"]
        ),

        "active_observations": int(
            obs["active_observations"]
        ),

        "inactive_observations": int(
            obs["inactive_observations"]
        ),

    })


# ============================================================
# 5. SAVE RESULTS
# ============================================================

result = pd.DataFrame(records)

result = result.sort_values(
    "total_observations",
    ascending=False
)

output_path = Path(
    "outputs/week09_compound_conflict_audit/"
    "baseline_selected_representations.csv"
)

result.to_csv(output_path, index=False)

# ============================================================
# 6. PRINT FINDINGS
# ============================================================

print("\n" + "=" * 65)
print("BASELINE REPRESENTATION SELECTION AUDIT")
print("=" * 65)

print("Total conflicting compounds:", len(conflict_ids))

print("Compounds retained by baseline:", len(result))

print(
    "Compounds where first valid mapping was selected:",
    int(result["first_valid_mapping_selected"].sum())
)

print(
    "Compounds with multiple distinct SMILES:",
    int((result["distinct_smiles"] > 1).sum())
)

print("\nTop 15 compounds by observation count:")

columns = [
    "parent_inchikey",
    "total_observations",
    "active_observations",
    "inactive_observations",
    "selected_molregno",
    "distinct_smiles",
    "first_valid_mapping_selected",
]

print(
    result[columns]
    .head(15)
    .to_string(index=False)
)

print("\nFirst 5 selected representations:")

for _, row in result.head(5).iterrows():

    print("\nInChIKey:", row["parent_inchikey"])
    print("Selected molregno:", row["selected_molregno"])
    print("Selected SMILES:", row["selected_smiles"])
    print("Alternative SMILES:", row["alternative_smiles"])

print("\nSaved:", output_path)

print("\nAUDIT COMPLETED.")
