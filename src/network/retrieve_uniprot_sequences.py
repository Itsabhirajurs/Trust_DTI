"""Retrieve and validate UniProt sequences for Network 1 accessions.

Writes local, gitignored intermediate artifacts. It does not modify Network 1.
Run from the repository root:
    python src/network/retrieve_uniprot_sequences.py
"""

from io import StringIO
from pathlib import Path
import time

import pandas as pd
import requests

INPUT = Path("data/processed/network1_v1.parquet")
OUTPUT = Path("data/interim/uniprot_human_sequences.parquet")
MISSING = Path("data/interim/uniprot_unmatched_accessions.csv")
FASTA = Path("data/interim/uniprot_human_sequences.fasta")
API = "https://rest.uniprot.org/uniprotkb/search"
BATCH_SIZE = 50
VALID_AA = set("ACDEFGHIKLMNPQRSTVWYBXZJUO")


def main() -> None:
    network = pd.read_parquet(INPUT, columns=["accession"])
    accessions = sorted(
        network["accession"].dropna().astype(str).str.strip().unique()
    )
    if not accessions:
        raise SystemExit("Network 1 contains no accessions.")

    print("=== TRUSTDTI: BULK PROTEIN SEQUENCE RETRIEVAL ===")
    print("Unique input accessions:", len(accessions))
    print("Batch size:", BATCH_SIZE)

    session = requests.Session()
    session.headers.update({"User-Agent": "TrustDTI-research/1.0"})
    records: dict[str, dict] = {}

    for start in range(0, len(accessions), BATCH_SIZE):
        batch = accessions[start : start + BATCH_SIZE]
        query = "(" + " OR ".join(f"accession:{acc}" for acc in batch) + ")"
        params = {
            "query": query,
            "format": "tsv",
            "fields": "accession,protein_name,organism_name,length,sequence",
            "size": 500,
        }

        response = None
        for attempt in range(4):
            try:
                response = session.get(API, params=params, timeout=60)
                if response.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2**attempt)
                    continue
                response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)

        if response is None or response.status_code != 200:
            raise RuntimeError("UniProt request failed after retries.")

        table = pd.read_csv(StringIO(response.text), sep="\t", dtype=str)
        for _, row in table.iterrows():
            accession = str(row.get("Entry", "")).strip()
            sequence = str(row.get("Sequence", "")).strip().upper()
            if not accession or not sequence or sequence == "NAN":
                continue
            records[accession] = {
                "accession": accession,
                "protein_name": row.get("Protein names", ""),
                "organism": row.get("Organism", ""),
                "reported_length": pd.to_numeric(
                    row.get("Length"), errors="coerce"
                ),
                "sequence": sequence,
            }

        completed = min(start + BATCH_SIZE, len(accessions))
        print(
            f"Processed query batch: {completed}/{len(accessions)} "
            f"| Unique records returned so far: {len(records)}"
        )
        time.sleep(0.2)

    result = pd.DataFrame(records.values())
    if result.empty:
        raise RuntimeError("No protein sequences were retrieved.")

    result["actual_length"] = result["sequence"].str.len()
    result["length_matches"] = result["reported_length"] == result["actual_length"]
    result["valid_amino_acids"] = result["sequence"].map(
        lambda seq: bool(seq) and all(letter in VALID_AA for letter in seq)
    )
    result["is_human"] = result["organism"].str.contains(
        "Homo sapiens", case=False, na=False
    )

    requested = set(accessions)
    returned = set(result["accession"])
    missing = sorted(requested - returned)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MISSING.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT, index=False)
    pd.DataFrame({"accession": missing}).to_csv(MISSING, index=False)

    with FASTA.open("w", encoding="utf-8") as handle:
        for row in result.itertuples(index=False):
            handle.write(f">{row.accession} {row.protein_name}\n")
            for index in range(0, len(row.sequence), 80):
                handle.write(row.sequence[index : index + 80] + "\n")

    print("\n=== RETRIEVAL SUMMARY ===")
    print("Network accessions:", len(requested))
    print("Unique UniProt entries returned:", len(result))
    print("Exact accession matches:", len(requested & returned))
    print("Unmatched accessions:", len(missing))
    print("Human entries:", int(result["is_human"].sum()))
    print("Valid amino-acid sequences:", int(result["valid_amino_acids"].sum()))
    print("Reported and actual lengths match:", int(result["length_matches"].sum()))
    print("Output dataset:", OUTPUT)
    print("FASTA file:", FASTA)
    print("Unmatched list:", MISSING)
    print("Review unmatched identifiers before proceeding.")


if __name__ == "__main__":
    main()
