from pathlib import Path
from itertools import combinations
import json
import sys

import numpy as np
import pandas as pd

from rdkit import Chem, DataStructs
from rdkit.Chem import (
    inchi,
    rdFingerprintGenerator,
    rdMolDescriptors,
)
from rdkit.Chem.MolStandardize import rdMolStandardize


# ============================================================
# 1. CONFIGURATION
# ============================================================

NETWORK1_PATH = Path("data/processed/network1_v1.parquet")
COMPOUNDS_PATH = Path("data/interim/compounds_standardized.parquet")

OUTPUT_DIR = Path("outputs/week09_compound_conflict_audit")

MORGAN_RADIUS = 2
MORGAN_FP_SIZE = 2048

# Candidate column names for the compound identifier in Network 1.
POSSIBLE_COMPOUND_COLUMNS = [
    "pik",  # Network 1 compound identifier
    "compound_id",
    "compound_inchikey",
    "parent_inchikey",
    "inchikey",
    "molecule_inchikey",
    "drug_id",
    "compound_key",
]


# ============================================================
# 2. CHECK INPUT FILES
# ============================================================

print("\n" + "=" * 65)
print("WEEK 09: COMPOUND MAPPING CONFLICT AUDIT")
print("=" * 65)

if not NETWORK1_PATH.exists():
    raise FileNotFoundError(
        f"Network 1 dataset not found: {NETWORK1_PATH}\n"
        "Run this code from the Trust_DTI repository root."
    )

if not COMPOUNDS_PATH.exists():
    raise FileNotFoundError(
        f"Compound dataset not found: {COMPOUNDS_PATH}"
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("\nInput files found.")
print("Loading Parquet datasets...")


# ============================================================
# 3. LOAD DATASETS
# ============================================================

network1 = pd.read_parquet(NETWORK1_PATH)
compounds = pd.read_parquet(COMPOUNDS_PATH)

print("\nNetwork 1 shape:", network1.shape)
print("Compound table shape:", compounds.shape)

print("\nNetwork 1 columns:")
print(network1.columns.tolist())

print("\nCompound table columns:")
print(compounds.columns.tolist())


# ============================================================
# 4. VALIDATE REQUIRED COMPOUND TABLE COLUMNS
# ============================================================

required_columns = [
    "parent_smiles",
    "parent_inchikey",
    "molregno",
]

missing_columns = [
    col for col in required_columns
    if col not in compounds.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns in compound table: {missing_columns}"
    )


# ============================================================
# 5. IDENTIFY THE NETWORK 1 COMPOUND ID COLUMN
# ============================================================

def normalize_key(series):
    """
    Normalize identifier values for reliable matching.
    """
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
    )


compound_keys = set(
    normalize_key(compounds["parent_inchikey"])
    .dropna()
    .tolist()
)

candidate_columns = [
    col for col in POSSIBLE_COMPOUND_COLUMNS
    if col in network1.columns
]

if not candidate_columns:
    raise ValueError(
        "Could not identify a possible compound identifier column.\n"
        "Check the Network 1 columns printed above and add its "
        "identifier column to POSSIBLE_COMPOUND_COLUMNS."
    )

column_scores = []

for col in candidate_columns:

    values = normalize_key(network1[col]).dropna()

    matched_values = values[values.isin(compound_keys)]

    column_scores.append({
        "column": col,
        "matched_rows": int(len(matched_values)),
        "matched_unique_ids": int(matched_values.nunique()),
    })

scores_df = pd.DataFrame(column_scores)

print("\nCompound identifier column matching:")
print(scores_df.to_string(index=False))

best_column = (
    scores_df.sort_values(
        ["matched_unique_ids", "matched_rows"],
        ascending=False
    )
    .iloc[0]["column"]
)

best_score = scores_df.loc[
    scores_df["column"] == best_column,
    "matched_unique_ids"
].iloc[0]

if best_score == 0:
    raise ValueError(
        "No Network 1 compound identifiers matched the compound "
        "table's parent_inchikey values. Check the identifier columns."
    )

NETWORK1_COMPOUND_COL = best_column

print("\nSelected Network 1 compound column:", NETWORK1_COMPOUND_COL)

network1_ids = set(
    normalize_key(network1[NETWORK1_COMPOUND_COL])
    .dropna()
    .tolist()
)

matched_network1_ids = network1_ids.intersection(compound_keys)

print("Distinct Network 1 compound IDs:", len(network1_ids))
print("IDs matched to compound table:", len(matched_network1_ids))
print(
    "Mapping coverage:",
    round(
        len(matched_network1_ids) / len(network1_ids) * 100,
        4
    ),
    "%"
)


# ============================================================
# 6. IDENTIFY CONFLICTING COMPOUND MAPPINGS
# ============================================================

compounds["parent_inchikey_normalized"] = normalize_key(
    compounds["parent_inchikey"]
)

compounds["parent_smiles_normalized"] = (
    compounds["parent_smiles"]
    .astype("string")
    .str.strip()
)

network1_compounds = compounds[
    compounds["parent_inchikey_normalized"].isin(
        matched_network1_ids
    )
].copy()

network1_compounds = network1_compounds.dropna(
    subset=[
        "parent_inchikey_normalized",
        "parent_smiles_normalized",
    ]
)

smiles_counts = (
    network1_compounds
    .groupby("parent_inchikey_normalized")[
        "parent_smiles_normalized"
    ]
    .nunique()
)

conflict_keys = sorted(
    smiles_counts[smiles_counts > 1].index.tolist()
)

print("\n" + "=" * 65)
print("CONFLICT IDENTIFICATION")
print("=" * 65)

print("Network 1 compound IDs with multiple SMILES:", len(conflict_keys))

if len(conflict_keys) == 0:
    print("No conflicting mappings found.")
    sys.exit(0)

if len(conflict_keys) != 95:
    print(
        "\nNOTE: The number of conflicts differs from the previous "
        "audit result of 95. Check the selected identifier column "
        "and dataset versions."
    )

print("\nFirst 10 conflicting identifiers:")
for key in conflict_keys[:10]:
    print(" ", key)


# ============================================================
# 7. INITIALIZE RDKit TOOLS
# ============================================================

fingerprint_generator = rdFingerprintGenerator.GetMorganGenerator(
    radius=MORGAN_RADIUS,
    fpSize=MORGAN_FP_SIZE,
)

tautomer_enumerator = rdMolStandardize.TautomerEnumerator()


# ============================================================
# 8. HELPER FUNCTIONS
# ============================================================

def safe_string(value):
    """
    Return a clean string or an empty string.
    """
    if pd.isna(value):
        return ""

    return str(value).strip()


def unique_nonempty(values):
    """
    Count distinct non-empty values.
    """
    cleaned = {
        safe_string(value)
        for value in values
        if safe_string(value)
    }

    return len(cleaned)


def analyze_smiles(smiles, stored_inchikey):
    """
    Analyze one standardized SMILES representation.

    Returns:
        Chemical identifiers
        Canonical structures
        Tautomer representation
        Formula
        Morgan fingerprint
        Validation status
    """

    result = {
        "input_smiles": smiles,
        "stored_inchikey": stored_inchikey,
        "parse_success": False,
        "canonical_isomeric_smiles": None,
        "canonical_nonisomeric_smiles": None,
        "standard_inchi": None,
        "generated_inchikey": None,
        "generated_key_matches_stored": False,
        "canonical_tautomer_smiles": None,
        "molecular_formula": None,
        "atom_count": None,
        "bond_count": None,
        "formal_charge": None,
        "morgan_fingerprint": None,
        "morgan_fingerprint_bits": None,
        "error": None,
    }

    try:

        # Parse the SMILES.
        mol = Chem.MolFromSmiles(smiles)

        if mol is None:
            result["error"] = "RDKit could not parse SMILES"
            return result

        result["parse_success"] = True

        # ----------------------------------------------------
        # A. Canonical SMILES
        # ----------------------------------------------------

        result["canonical_isomeric_smiles"] = Chem.MolToSmiles(
            mol,
            canonical=True,
            isomericSmiles=True,
        )

        result["canonical_nonisomeric_smiles"] = Chem.MolToSmiles(
            mol,
            canonical=True,
            isomericSmiles=False,
        )

        # ----------------------------------------------------
        # B. Standard InChI and InChIKey
        # ----------------------------------------------------

        standard_inchi = inchi.MolToInchi(mol)

        generated_key = inchi.MolToInchiKey(mol)

        result["standard_inchi"] = standard_inchi

        result["generated_inchikey"] = generated_key

        result["generated_key_matches_stored"] = (
            generated_key == stored_inchikey
        )

        # ----------------------------------------------------
        # C. Canonical tautomer
        # ----------------------------------------------------

        canonical_tautomer = tautomer_enumerator.Canonicalize(mol)

        result["canonical_tautomer_smiles"] = Chem.MolToSmiles(
            canonical_tautomer,
            canonical=True,
            isomericSmiles=True,
        )

        # ----------------------------------------------------
        # D. Molecular properties
        # ----------------------------------------------------

        result["molecular_formula"] = (
            rdMolDescriptors.CalcMolFormula(mol)
        )

        result["atom_count"] = mol.GetNumAtoms()

        result["bond_count"] = mol.GetNumBonds()

        result["formal_charge"] = Chem.GetFormalCharge(mol)

        # ----------------------------------------------------
        # E. Morgan fingerprint
        # ----------------------------------------------------

        fingerprint = fingerprint_generator.GetFingerprint(mol)

        result["morgan_fingerprint"] = fingerprint

        result["morgan_fingerprint_bits"] = (
            fingerprint.ToBitString()
        )

        return result

    except Exception as error:

        result["error"] = str(error)

        return result


# ============================================================
# 9. AUDIT ALL CONFLICT GROUPS
# ============================================================

summary_records = []
detail_records = []

print("\n" + "=" * 65)
print("ANALYZING CONFLICTING STRUCTURES")
print("=" * 65)

for index, stored_key in enumerate(conflict_keys, start=1):

    group = network1_compounds[
        network1_compounds["parent_inchikey_normalized"]
        == stored_key
    ].copy()

    # One analysis per distinct raw SMILES.
    unique_smiles = sorted(
        group["parent_smiles_normalized"]
        .dropna()
        .unique()
        .tolist()
    )

    structures = []

    for smiles in unique_smiles:

        matching_rows = group[
            group["parent_smiles_normalized"] == smiles
        ]

        molregno_values = sorted(
            matching_rows["molregno"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        multi_fragment_values = []

        if "had_multi_fragment" in matching_rows.columns:

            multi_fragment_values = sorted(
                matching_rows["had_multi_fragment"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

        analysis = analyze_smiles(
            smiles=smiles,
            stored_inchikey=stored_key,
        )

        analysis["parent_inchikey"] = stored_key

        analysis["molregno_values"] = "; ".join(
            molregno_values
        )

        analysis["had_multi_fragment_values"] = "; ".join(
            multi_fragment_values
        )

        structures.append(analysis)

        # Keep fingerprint out of CSV output.
        detail_row = {
            key: value
            for key, value in analysis.items()
            if key != "morgan_fingerprint"
        }

        detail_records.append(detail_row)

    # --------------------------------------------------------
    # Extract valid structures
    # --------------------------------------------------------

    valid_structures = [
        structure
        for structure in structures
        if structure["parse_success"]
    ]

    valid_fingerprints = [
        structure["morgan_fingerprint"]
        for structure in valid_structures
        if structure["morgan_fingerprint"] is not None
    ]

    # --------------------------------------------------------
    # Pairwise Morgan Tanimoto similarities
    # --------------------------------------------------------

    pairwise_similarities = []

    for fp1, fp2 in combinations(valid_fingerprints, 2):

        similarity = DataStructs.TanimotoSimilarity(
            fp1,
            fp2,
        )

        pairwise_similarities.append(similarity)

    if pairwise_similarities:

        min_similarity = float(
            np.min(pairwise_similarities)
        )

        max_similarity = float(
            np.max(pairwise_similarities)
        )

        mean_similarity = float(
            np.mean(pairwise_similarities)
        )

    else:

        min_similarity = None
        max_similarity = None
        mean_similarity = None

    # --------------------------------------------------------
    # Count distinct chemical representations
    # --------------------------------------------------------

    standard_inchis = {
        s["standard_inchi"]
        for s in valid_structures
        if s["standard_inchi"]
    }

    generated_keys = {
        s["generated_inchikey"]
        for s in valid_structures
        if s["generated_inchikey"]
    }

    canonical_isomeric = {
        s["canonical_isomeric_smiles"]
        for s in valid_structures
        if s["canonical_isomeric_smiles"]
    }

    canonical_nonisomeric = {
        s["canonical_nonisomeric_smiles"]
        for s in valid_structures
        if s["canonical_nonisomeric_smiles"]
    }

    canonical_tautomers = {
        s["canonical_tautomer_smiles"]
        for s in valid_structures
        if s["canonical_tautomer_smiles"]
    }

    molecular_formulas = {
        s["molecular_formula"]
        for s in valid_structures
        if s["molecular_formula"]
    }

    fingerprint_bitstrings = {
        s["morgan_fingerprint_bits"]
        for s in valid_structures
        if s["morgan_fingerprint_bits"]
    }

    all_keys_match = (
        len(valid_structures) > 0
        and all(
            s["generated_key_matches_stored"]
            for s in valid_structures
        )
    )

    # --------------------------------------------------------
    # Create group-level summary
    # --------------------------------------------------------

    summary_record = {

        "parent_inchikey": stored_key,

        "raw_smiles_count": len(unique_smiles),

        "parse_success_count": len(valid_structures),

        "parse_failure_count": (
            len(structures) - len(valid_structures)
        ),

        "standard_inchi_count": len(standard_inchis),

        "generated_inchikey_count": len(generated_keys),

        "all_generated_keys_match_stored": all_keys_match,

        "canonical_isomeric_smiles_count": len(
            canonical_isomeric
        ),

        "canonical_nonisomeric_smiles_count": len(
            canonical_nonisomeric
        ),

        "canonical_tautomer_count": len(
            canonical_tautomers
        ),

        "molecular_formula_count": len(
            molecular_formulas
        ),

        "morgan_fingerprint_count": len(
            fingerprint_bitstrings
        ),

        "pairwise_comparison_count": len(
            pairwise_similarities
        ),

        "morgan_tanimoto_min": min_similarity,

        "morgan_tanimoto_mean": mean_similarity,

        "morgan_tanimoto_max": max_similarity,

        "standard_inchi_identical": (
            len(standard_inchis) == 1
            and len(valid_structures) > 0
        ),

        "canonical_tautomers_identical": (
            len(canonical_tautomers) == 1
            and len(valid_structures) > 0
        ),

        "morgan_fingerprints_identical": (
            len(fingerprint_bitstrings) == 1
            and len(valid_structures) > 0
        ),

        "molecular_formulas_identical": (
            len(molecular_formulas) == 1
            and len(valid_structures) > 0
        ),

    }

    summary_records.append(summary_record)

    if index % 10 == 0 or index == len(conflict_keys):

        print(
            f"Processed {index}/{len(conflict_keys)} "
            f"conflicting compound groups"
        )


# ============================================================
# 10. CREATE OUTPUT DATAFRAMES
# ============================================================

summary_df = pd.DataFrame(summary_records)

detail_df = pd.DataFrame(detail_records)


# ============================================================
# 11. SAVE AUDIT RESULTS
# ============================================================

summary_path = (
    OUTPUT_DIR / "compound_conflict_summary.csv"
)

details_path = (
    OUTPUT_DIR / "compound_structure_details.csv"
)

summary_df.to_csv(
    summary_path,
    index=False,
)

detail_df.to_csv(
    details_path,
    index=False,
)


# ============================================================
# 12. FINAL AUDIT SUMMARY
# ============================================================

print("\n" + "=" * 65)
print("FINAL COMPOUND CONFLICT AUDIT")
print("=" * 65)

print("\nTotal conflicting compound groups:", len(summary_df))

print(
    "Groups where all generated InChIKeys match stored key:",
    int(summary_df["all_generated_keys_match_stored"].sum()),
)

print(
    "Groups with identical Standard InChI:",
    int(summary_df["standard_inchi_identical"].sum()),
)

print(
    "Groups with identical canonical tautomer:",
    int(summary_df["canonical_tautomers_identical"].sum()),
)

print(
    "Groups with identical molecular formula:",
    int(summary_df["molecular_formulas_identical"].sum()),
)

print(
    "Groups with identical Morgan fingerprints:",
    int(summary_df["morgan_fingerprints_identical"].sum()),
)

print(
    "Groups with different Morgan fingerprints:",
    int(
        (
            summary_df["morgan_fingerprint_count"] > 1
        ).sum()
    ),
)

print("\nMorgan Tanimoto similarity statistics:")

print(
    summary_df[
        [
            "morgan_tanimoto_min",
            "morgan_tanimoto_mean",
            "morgan_tanimoto_max",
        ]
    ].describe().round(4)
)

print("\nFirst 15 group-level results:")

display_columns = [
    "parent_inchikey",
    "raw_smiles_count",
    "standard_inchi_count",
    "canonical_tautomer_count",
    "molecular_formula_count",
    "morgan_fingerprint_count",
    "morgan_tanimoto_mean",
    "all_generated_keys_match_stored",
]

print(
    summary_df[display_columns]
    .head(15)
    .to_string(index=False)
)

print("\nOutput files:")
print("1.", summary_path)
print("2.", details_path)

print("\nAUDIT COMPLETED SUCCESSFULLY.")