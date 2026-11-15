
from pathlib import Path
from itertools import combinations

import pandas as pd

from rdkit import Chem, DataStructs, __version__
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.MolStandardize import rdMolStandardize


# ============================================================
# 1. CONFIGURATION
# ============================================================

COMPOUND_PATH = Path(
    "data/interim/compounds_standardized.parquet"
)

SUMMARY_PATH = Path(
    "outputs/week09_compound_conflict_audit/"
    "compound_conflict_summary.csv"
)

OUTPUT_DIR = Path(
    "outputs/week09_compound_conflict_audit"
)

RADIUS = 2
FP_SIZE = 2048


# ============================================================
# 2. LOAD DATA
# ============================================================

compounds = pd.read_parquet(COMPOUND_PATH)
previous_summary = pd.read_csv(SUMMARY_PATH)

conflict_ids = set(
    previous_summary["parent_inchikey"]
    .astype("string")
    .str.strip()
    .str.upper()
)

compounds["key_clean"] = (
    compounds["parent_inchikey"]
    .astype("string")
    .str.strip()
    .str.upper()
)

compounds["smiles_clean"] = (
    compounds["parent_smiles"]
    .astype("string")
    .str.strip()
)

conflict_data = compounds[
    compounds["key_clean"].isin(conflict_ids)
    & compounds["smiles_clean"].notna()
].copy()


# ============================================================
# 3. INITIALIZE RDKit
# ============================================================

generator = rdFingerprintGenerator.GetMorganGenerator(
    radius=RADIUS,
    fpSize=FP_SIZE,
)

tautomer_enumerator = (
    rdMolStandardize.TautomerEnumerator()
)


# ============================================================
# 4. HELPER FUNCTION
# ============================================================

def calculate_pairwise_similarities(fingerprints):

    similarities = []

    for fp1, fp2 in combinations(fingerprints, 2):

        similarity = DataStructs.TanimotoSimilarity(
            fp1,
            fp2,
        )

        similarities.append(similarity)

    if not similarities:

        return {
            "min": None,
            "mean": None,
            "max": None,
            "pair_count": 0,
        }

    return {
        "min": min(similarities),
        "mean": sum(similarities) / len(similarities),
        "max": max(similarities),
        "pair_count": len(similarities),
    }


# ============================================================
# 5. ANALYZE ALL 95 CONFLICT GROUPS
# ============================================================

summary_records = []
detail_records = []

print("\n" + "=" * 65)
print("WEEK 09: TAUTOMER FINGERPRINT NORMALIZATION")
print("=" * 65)

print("RDKit version:", __version__)
print("Conflicting compounds:", len(conflict_ids))

for index, key in enumerate(sorted(conflict_ids), start=1):

    group = conflict_data[
        conflict_data["key_clean"] == key
    ]

    smiles_list = (
        group["smiles_clean"]
        .drop_duplicates()
        .tolist()
    )

    raw_fingerprints = []
    tautomer_fingerprints = []

    canonical_tautomer_smiles = []

    parse_failures = 0

    # --------------------------------------------------------
    # Analyze every distinct SMILES representation
    # --------------------------------------------------------

    for smiles in smiles_list:

        try:

            mol = Chem.MolFromSmiles(smiles)

            if mol is None:

                parse_failures += 1
                continue

            # Original representation fingerprint.
            raw_fp = generator.GetFingerprint(mol)

            raw_fingerprints.append(raw_fp)

            # Canonicalize the tautomer.
            tautomer_mol = (
                tautomer_enumerator.Canonicalize(mol)
            )

            tautomer_smiles = Chem.MolToSmiles(
                tautomer_mol,
                canonical=True,
                isomericSmiles=True,
            )

            canonical_tautomer_smiles.append(
                tautomer_smiles
            )

            # Fingerprint after tautomer normalization.
            tautomer_fp = generator.GetFingerprint(
                tautomer_mol
            )

            tautomer_fingerprints.append(
                tautomer_fp
            )

            detail_records.append({

                "parent_inchikey": key,

                "input_smiles": smiles,

                "canonical_tautomer_smiles": (
                    tautomer_smiles
                ),

                "raw_fingerprint_bits": (
                    raw_fp.ToBitString()
                ),

                "tautomer_fingerprint_bits": (
                    tautomer_fp.ToBitString()
                ),

            })

        except Exception as error:

            parse_failures += 1

            print(
                "\nError processing:",
                key,
                str(error)
            )

    # --------------------------------------------------------
    # Count distinct fingerprints
    # --------------------------------------------------------

    raw_bitstrings = {
        fp.ToBitString()
        for fp in raw_fingerprints
    }

    tautomer_bitstrings = {
        fp.ToBitString()
        for fp in tautomer_fingerprints
    }

    distinct_tautomers = set(
        canonical_tautomer_smiles
    )

    # --------------------------------------------------------
    # Pairwise similarities
    # --------------------------------------------------------

    raw_similarity = calculate_pairwise_similarities(
        raw_fingerprints
    )

    normalized_similarity = (
        calculate_pairwise_similarities(
            tautomer_fingerprints
        )
    )

    # --------------------------------------------------------
    # Group summary
    # --------------------------------------------------------

    record = {

        "parent_inchikey": key,

        "input_smiles_count": len(smiles_list),

        "parse_failures": parse_failures,

        "canonical_tautomer_count": len(
            distinct_tautomers
        ),

        "raw_morgan_fingerprint_count": len(
            raw_bitstrings
        ),

        "normalized_morgan_fingerprint_count": len(
            tautomer_bitstrings
        ),

        "raw_tanimoto_min": raw_similarity["min"],

        "raw_tanimoto_mean": raw_similarity["mean"],

        "normalized_tanimoto_min": (
            normalized_similarity["min"]
        ),

        "normalized_tanimoto_mean": (
            normalized_similarity["mean"]
        ),

        "normalized_tanimoto_max": (
            normalized_similarity["max"]
        ),

        "pairwise_comparisons": (
            normalized_similarity["pair_count"]
        ),

        "fingerprint_conflict_resolved": (
            len(raw_bitstrings) > 1
            and len(tautomer_bitstrings) == 1
        ),

        "fingerprints_still_different": (
            len(tautomer_bitstrings) > 1
        ),

    }

    summary_records.append(record)

    if index % 10 == 0 or index == len(conflict_ids):

        print(
            f"Processed {index}/{len(conflict_ids)}"
        )


# ============================================================
# 6. SAVE RESULTS
# ============================================================

summary_df = pd.DataFrame(summary_records)

detail_df = pd.DataFrame(detail_records)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

summary_output = (
    OUTPUT_DIR / "tautomer_fingerprint_summary.csv"
)

detail_output = (
    OUTPUT_DIR / "tautomer_fingerprint_details.csv"
)

summary_df.to_csv(
    summary_output,
    index=False,
)

detail_df.to_csv(
    detail_output,
    index=False,
)


# ============================================================
# 7. FINAL RESULTS
# ============================================================

print("\n" + "=" * 65)
print("TAUTOMER NORMALIZATION RESULTS")
print("=" * 65)

print(
    "Total conflict groups:",
    len(summary_df)
)

print(
    "Groups with identical raw fingerprints:",
    int(
        (
            summary_df[
                "raw_morgan_fingerprint_count"
            ] == 1
        ).sum()
    )
)

print(
    "Groups with identical normalized fingerprints:",
    int(
        (
            summary_df[
                "normalized_morgan_fingerprint_count"
            ] == 1
        ).sum()
    )
)

print(
    "Groups where normalization resolved the conflict:",
    int(
        summary_df[
            "fingerprint_conflict_resolved"
        ].sum()
    )
)

print(
    "Groups with fingerprints still different:",
    int(
        summary_df[
            "fingerprints_still_different"
        ].sum()
    )
)

print(
    "Groups with parsing failures:",
    int(
        (
            summary_df["parse_failures"] > 0
        ).sum()
    )
)

print("\nSimilarity comparison:")

print(
    summary_df[
        [
            "raw_tanimoto_mean",
            "normalized_tanimoto_mean",
        ]
    ].describe().round(4)
)

print("\nFirst 15 results:")

print(
    summary_df[
        [
            "parent_inchikey",
            "raw_morgan_fingerprint_count",
            "normalized_morgan_fingerprint_count",
            "raw_tanimoto_mean",
            "normalized_tanimoto_mean",
            "fingerprint_conflict_resolved",
        ]
    ].head(15).to_string(index=False)
)

print("\nOutput files:")
print(summary_output)
print(detail_output)

print("\nAUDIT COMPLETED.")
