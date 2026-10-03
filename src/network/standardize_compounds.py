"""Stage 2 step 1 — standardise every in-scope compound with RDKit.

For each distinct molregno in the ChEMBL extract: parse its canonical SMILES, keep the
largest organic fragment (strips salts/counter-ions), neutralise charges, recompute a
canonical parent SMILES and InChIKey, and compute its Bemis-Murcko scaffold. Scaffolds
are computed HERE, before any split, so the drug-cold split cannot leak (Briefing §3.6).

Failures are recorded with a status, never silently dropped.

Output (gitignored): data/interim/compounds_standardized.parquet
Stats (committed): reports/week2/standardize_stats.json

Run: python -m src.network.standardize_compounds
"""
import json
import sqlite3

import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold

from src import config

RDLogger.DisableLog("rdApp.*")
V = config.CHEMBL_VERSION
OUT = config.INTERIM / "compounds_standardized.parquet"
STATS = config.REPORTS / "week2" / "standardize_stats.json"

_chooser = rdMolStandardize.LargestFragmentChooser()
_uncharger = rdMolStandardize.Uncharger()


def standardize_one(smiles: str):
    """Return dict(parent_smiles, parent_inchikey, scaffold, had_multi_fragment, status)."""
    if not smiles:
        return dict(parent_smiles=None, parent_inchikey=None, scaffold=None, had_multi_fragment=False, status="empty_smiles")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return dict(parent_smiles=None, parent_inchikey=None, scaffold=None, had_multi_fragment=("." in smiles), status="unparseable")
    multi = "." in smiles
    try:
        parent = _chooser.choose(mol)
        parent = _uncharger.uncharge(parent)
        psmiles = Chem.MolToSmiles(parent)
        pinchikey = Chem.MolToInchiKey(parent)
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=parent)  # "" for acyclic molecules
        return dict(parent_smiles=psmiles, parent_inchikey=pinchikey or None, scaffold=scaffold,
                    had_multi_fragment=multi, status="ok")
    except Exception as e:  # noqa: BLE001 — record, never drop
        return dict(parent_smiles=None, parent_inchikey=None, scaffold=None, had_multi_fragment=multi,
                    status=f"error:{type(e).__name__}")


def main():
    STATS.parent.mkdir(parents=True, exist_ok=True)
    molregnos = pd.read_parquet(config.INTERIM / f"chembl{V}_human_sp_activities.parquet",
                                columns=["molregno"]).molregno.drop_duplicates()
    con = sqlite3.connect(f"file:{config.CHEMBL_DB}?mode=ro", uri=True)
    ids = molregnos.tolist()
    smiles = {}
    for i in range(0, len(ids), 50_000):
        chunk = ids[i:i + 50_000]
        q = "SELECT molregno, canonical_smiles FROM compound_structures WHERE molregno IN (%s)" % ",".join(map(str, chunk))
        for mr, smi in con.execute(q):
            smiles[mr] = smi
    con.close()

    rows = []
    n = 0
    for mr in ids:
        r = standardize_one(smiles.get(mr))
        r["molregno"] = mr
        rows.append(r)
        n += 1
        if n % 100_000 == 0:
            print(f"  {n:>9,} / {len(ids):,} standardised", flush=True)
    df = pd.DataFrame(rows)
    df["inchikey_block"] = df.parent_inchikey.str[:14]
    df.to_parquet(OUT, index=False)

    stats = {
        "compounds_in": len(ids),
        "status_counts": df.status.value_counts().to_dict(),
        "had_multi_fragment": int(df.had_multi_fragment.sum()),
        "distinct_parent_inchikey": int(df.parent_inchikey.nunique()),
        "distinct_inchikey_block": int(df.inchikey_block.nunique()),
        "distinct_scaffold_nonempty": int(df.loc[df.scaffold.fillna("") != "", "scaffold"].nunique()),
        "acyclic_empty_scaffold": int((df.scaffold.fillna("") == "").sum()),
    }
    STATS.write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
