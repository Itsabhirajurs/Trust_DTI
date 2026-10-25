"""One-record smoke test for UniProt sequence retrieval used by TrustDTI Stage 3."""

from io import StringIO

import pandas as pd
import requests

DATASET = "data/processed/network1_v1.parquet"
API = "https://rest.uniprot.org/uniprotkb/search"


def main() -> None:
    network = pd.read_parquet(DATASET, columns=["accession"])
    accessions = (
        network["accession"].dropna().astype(str).str.strip().drop_duplicates()
    )
    if accessions.empty:
        raise SystemExit("Network 1 contains no accessions to test.")

    accession = accessions.iloc[0]
    print("=== UNIPROT SEQUENCE RETRIEVAL TEST ===")
    print("Test accession:", accession)

    response = requests.get(
        API,
        params={
            "query": f"accession:{accession}",
            "format": "tsv",
            "fields": "accession,protein_name,organism_name,length,sequence",
            "size": 5,
        },
        timeout=30,
    )
    response.raise_for_status()
    result = pd.read_csv(StringIO(response.text), sep="\t", dtype=str)

    if result.empty:
        raise SystemExit("FAIL: UniProt returned no matching records.")

    acc_col = next((c for c in result.columns if c.strip().lower() == "entry"), None)
    seq_col = next((c for c in result.columns if c.strip().lower() == "sequence"), None)
    org_col = next((c for c in result.columns if c.strip().lower() == "organism"), None)
    name_col = next((c for c in result.columns if c.strip().lower() == "protein names"), None)
    length_col = next((c for c in result.columns if c.strip().lower() == "length"), None)

    if None in (acc_col, seq_col, org_col, name_col, length_col):
        raise SystemExit(f"FAIL: Unexpected UniProt columns: {result.columns.tolist()}")

    matches = result[result[acc_col].astype(str).str.strip() == accession]
    if matches.empty:
        raise SystemExit("CHECK NEEDED: Returned records did not exactly match the accession.")

    row = matches.iloc[0]
    sequence = str(row[seq_col]).strip().upper()
    valid_letters = set("ACDEFGHIKLMNPQRSTVWYBXZJUO")
    valid = bool(sequence) and all(letter in valid_letters for letter in sequence)
    actual_length = len(sequence)
    reported_length = pd.to_numeric(row[length_col], errors="coerce")

    print("Exact accession match: YES")
    print("Organism:", row[org_col])
    print("Protein:", row[name_col])
    print("Reported sequence length:", reported_length)
    print("Actual sequence length:", actual_length)
    print("Sequence characters valid:", valid)
    print("First 30 sequence characters:", sequence[:30])

    if not valid or reported_length != actual_length:
        raise SystemExit("CHECK NEEDED: Sequence validation failed.")
    print("RESULT: SINGLE-PROTEIN RETRIEVAL TEST PASSED")


if __name__ == "__main__":
    main()
