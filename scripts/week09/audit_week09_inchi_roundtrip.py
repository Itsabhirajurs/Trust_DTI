
from pathlib import Path
from itertools import combinations

import pandas as pd

from rdkit import Chem, DataStructs, __version__
from rdkit.Chem import inchi, rdFingerprintGenerator


# ============================================================
# 1. CONFIGURATION
# ============================================================

INPUT_PATH = Path(
    "outputs/week09_compound_conflict_audit/"
    "compound_structure_details.csv"
)

OUTPUT_DIR = Path(
    "outputs/week09_compound_conflict_audit"
)

RADIUS = 2
FP_SIZE = 2048


# ============================================================
# 2. LOAD DATA
# ============================================================

details = pd.read_csv(
    INPUT_PATH,
    usecols=["parent_inchikey", "input_smiles"],
    dtype={
        "parent_inchikey": "string",
        "input_smiles": "string",
    },
)

required = [
    "parent_inchikey",
    "input_smiles",
]

for column in required:
    if column not in details.columns:
        raise ValueError(f"Missing column: {column}")

generator = rdFingerprintGenerator.GetMorganGenerator(
    radius=RADIUS,
    fpSize=FP_SIZE,
)

print("\n" + "=" * 65)
print("WEEK 09: STANDARD INCHI ROUND-TRIP AUDIT")
print("=" * 65)

print("RDKit version:", __version__)
print("Input structures:", len(details))
print(
    "Distinct compound groups:",
    details["parent_inchikey"].nunique()
)


# ============================================================
# 3. ROUND-TRIP EACH STRUCTURE
# ============================================================

records = []

for index, row in details.iterrows():

    key = str(row["parent_inchikey"]).strip().upper()
    smiles = str(row["input_smiles"]).strip()

    record = {
        "parent_inchikey": key,
        "input_smiles": smiles,
        "parse_success": False,
        "standard_inchi": None,
        "generated_inchikey": None,
        "roundtrip_inchi": None,
        "roundtrip_inchikey": None,
        "roundtrip_canonical_smiles": None,
        "roundtrip_fingerprint_bits": None,
        "roundtrip_success": False,
        "error": None,
    }

    try:

        # Original molecular structure.
        mol = Chem.MolFromSmiles(smiles)

        if mol is None:
            raise ValueError("Original SMILES parsing failed")

        record["parse_success"] = True

        # ----------------------------------------------------
        # A. Convert original molecule into Standard InChI.
        # ----------------------------------------------------

        standard_inchi = inchi.MolToInchi(mol)

        generated_key = inchi.MolToInchiKey(mol)

        record["standard_inchi"] = standard_inchi
        record["generated_inchikey"] = generated_key

        # ----------------------------------------------------
        # B. Reconstruct the molecule from Standard InChI.
        # ----------------------------------------------------

        reconstructed = inchi.MolFromInchi(standard_inchi)

        if reconstructed is None:
            raise ValueError("InChI reconstruction failed")

        # ----------------------------------------------------
        # C. Convert reconstructed molecule back to InChI.
        # ----------------------------------------------------

        record["roundtrip_inchi"] = inchi.MolToInchi(
            reconstructed
        )

        record["roundtrip_inchikey"] = inchi.MolToInchiKey(
            reconstructed
        )

        # ----------------------------------------------------
        # D. Canonical SMILES after round-trip.
        # ----------------------------------------------------

        canonical_smiles = Chem.MolToSmiles(
            reconstructed,
            canonical=True,
            isomericSmiles=True,
        )

        record["roundtrip_canonical_smiles"] = (
            canonical_smiles
        )

        # ----------------------------------------------------
        # E. Morgan fingerprint after round-trip.
        # ----------------------------------------------------

        fingerprint = generator.GetFingerprint(
            reconstructed
        )

        record["roundtrip_fingerprint_bits"] = (
            fingerprint.ToBitString()
        )

        record["roundtrip_success"] = True

    except Exception as error:

        record["error"] = str(error)

    records.append(record)

    if (index + 1) % 20 == 0 or index + 1 == len(details):

        print(
            f"Processed {index + 1}/{len(details)}"
        )


# ============================================================
# 4. CREATE DETAIL OUTPUT
# ============================================================

roundtrip_details = pd.DataFrame(records)


# ============================================================
# 5. GROUP-LEVEL COMPARISON
# ============================================================

summary_records = []

for key, group in roundtrip_details.groupby(
    "parent_inchikey"
):

    valid = group[
        group["roundtrip_success"]
    ].copy()

    smiles_count = valid[
        "roundtrip_canonical_smiles"
    ].nunique()

    fingerprint_count = valid[
        "roundtrip_fingerprint_bits"
    ].nunique()

    inchi_count = valid[
        "roundtrip_inchi"
    ].nunique()

    key_count = valid[
        "roundtrip_inchikey"
    ].nunique()

    fingerprints = []

    for bits in valid["roundtrip_fingerprint_bits"]:

        if isinstance(bits, str):

            fp = DataStructs.CreateFromBitString(bits)

            fingerprints.append(fp)

    similarities = [
        DataStructs.TanimotoSimilarity(fp1, fp2)
        for fp1, fp2 in combinations(fingerprints, 2)
    ]

    if similarities:
        min_similarity = min(similarities)
        mean_similarity = sum(similarities) / len(similarities)
    else:
        min_similarity = None
        mean_similarity = None

    summary_records.append({

        "parent_inchikey": key,

        "input_structures": len(group),

        "successful_roundtrips": len(valid),

        "roundtrip_inchi_count": inchi_count,

        "roundtrip_inchikey_count": key_count,

        "roundtrip_canonical_smiles_count": smiles_count,

        "roundtrip_fingerprint_count": fingerprint_count,

        "tanimoto_min": min_similarity,

        "tanimoto_mean": mean_similarity,

        "roundtrip_conflict_resolved": (
            len(valid) > 0
            and fingerprint_count == 1
        ),

    })


roundtrip_summary = pd.DataFrame(summary_records)


# ============================================================
# 6. SAVE RESULTS
# ============================================================

detail_output = (
    OUTPUT_DIR / "inchi_roundtrip_details.csv"
)

summary_output = (
    OUTPUT_DIR / "inchi_roundtrip_summary.csv"
)

roundtrip_details.to_csv(
    detail_output,
    index=False,
)

roundtrip_summary.to_csv(
    summary_output,
    index=False,
)


# ============================================================
# 7. FINAL RESULTS
# ============================================================

print("\n" + "=" * 65)
print("ROUND-TRIP RESULTS")
print("=" * 65)

print(
    "Total groups:",
    len(roundtrip_summary)
)

print(
    "Groups with identical reconstructed fingerprints:",
    int(
        (
            roundtrip_summary[
                "roundtrip_fingerprint_count"
            ] == 1
        ).sum()
    )
)

print(
    "Groups with different reconstructed fingerprints:",
    int(
        (
            roundtrip_summary[
                "roundtrip_fingerprint_count"
            ] > 1
        ).sum()
    )
)

print(
    "Groups with multiple reconstructed InChIs:",
    int(
        (
            roundtrip_summary[
                "roundtrip_inchi_count"
            ] > 1
        ).sum()
    )
)

print(
    "Groups with failed round-trips:",
    int(
        (
            roundtrip_summary[
                "successful_roundtrips"
            ] < roundtrip_summary[
                "input_structures"
            ]
        ).sum()
    )
)

print("\nAll group results:")

print(
    roundtrip_summary.to_string(index=False)
)

print("\nSaved:")
print(detail_output)
print(summary_output)

print("\nAUDIT COMPLETED.")
