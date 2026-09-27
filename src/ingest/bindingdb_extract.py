"""Week 1 D3 — stream BindingDB's 9 GB TSV and keep human, single-chain rows.

Output: data/interim/bindingdb_<release>_human_single_chain.parquet (one row per
BindingDB measurement row, raw potency strings kept alongside parsed relation/value
for each endpoint so censored measurements are never lost).

Run: python -m src.ingest.bindingdb_extract
"""
import csv
import io
import json
import zipfile

import pandas as pd

from src import config
from src.ingest.relations import split_relation

ORG_COL = "Target Source Organism According to Curator or DataSource"
CHAIN_COL = "Number of Protein Chains in Target (>1 implies a multichain complex)"
ENDPOINTS = {"Ki (nM)": "ki", "IC50 (nM)": "ic50", "Kd (nM)": "kd", "EC50 (nM)": "ec50"}

KEEP = {
    "BindingDB Reactant_set_id": "reactant_set_id",
    "Ligand SMILES": "smiles",
    "Ligand InChI Key": "inchikey",
    "BindingDB MonomerID": "monomer_id",
    "Target Name": "target_name",
    ORG_COL: "organism",
    CHAIN_COL: "n_chains",
    "Curation/DataSource": "curation_source",
    "PMID": "pmid",
    "PubChem AID": "pubchem_aid",
    "Patent Number": "patent_number",
    "Date of publication": "pub_date",
    "ChEMBL ID of Ligand": "ligand_chembl_id",
    "UniProt (SwissProt) Primary ID of Target Chain 1": "uniprot_swissprot",
    "UniProt (TrEMBL) Primary ID of Target Chain 1": "uniprot_trembl",
    **{k: f"{v}_raw" for k, v in ENDPOINTS.items()},
}

OUT = config.INTERIM / f"bindingdb_{config.BINDINGDB_RELEASE}_human_single_chain.parquet"
STATS = config.STAGE0 / "bindingdb_extract_stats.json"


def main(chunksize: int = 250_000) -> None:
    z = zipfile.ZipFile(config.BINDINGDB_ZIP)
    member = z.infolist()[0].filename
    stats = {"rows_total": 0, "rows_human": 0, "rows_human_single_chain": 0}
    parts = []
    with z.open(member) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
        reader = pd.read_csv(
            text, sep="\t", usecols=list(KEEP), dtype=str, chunksize=chunksize,
            quoting=csv.QUOTE_NONE, on_bad_lines="warn", engine="c",
        )
        for chunk in reader:
            stats["rows_total"] += len(chunk)
            chunk = chunk.rename(columns=KEEP)
            human = chunk["organism"].str.strip() == config.ORGANISM
            stats["rows_human"] += int(human.sum())
            sc = human & (pd.to_numeric(chunk["n_chains"], errors="coerce") == 1)
            chunk = chunk[sc].copy()
            stats["rows_human_single_chain"] += len(chunk)
            for ep in ENDPOINTS.values():
                parsed = split_relation(chunk[f"{ep}_raw"])
                chunk[f"{ep}_relation"] = parsed["relation"]
                chunk[f"{ep}_nm"] = parsed["value"]
                chunk[f"{ep}_unparsed"] = parsed["unparsed"]
            parts.append(chunk)
            print(f"  {stats['rows_total']:>10,} rows read, {stats['rows_human_single_chain']:>9,} kept", flush=True)

    df = pd.concat(parts, ignore_index=True)
    df["uniprot"] = df["uniprot_swissprot"].fillna(df["uniprot_trembl"]).str.strip()
    df.to_parquet(OUT, index=False)
    for ep in ENDPOINTS.values():
        stats[f"{ep}_unparsed_nonblank"] = int(df[f"{ep}_unparsed"].sum())
    stats["missing_uniprot"] = int(df["uniprot"].isna().sum())
    stats["missing_inchikey"] = int(df["inchikey"].isna().sum())
    config.STAGE0.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
