"""Week 1 follow-up — how much does PubChem qHTS data shift per-family pChEMBL?

Writes reports/stage0/pchembl_source_confounding.csv: for each level-2 family with
≥10k pChEMBL values, the median pChEMBL overall, excluding PubChem (src_id 7), and
PubChem only, plus PubChem's share. Evidence for Stage 0 open issue #1.

Run: python -m src.ingest.profile_source_confounding
"""
import pandas as pd

from src import config

V = config.CHEMBL_VERSION
PUBCHEM_SRC_ID = 7


def main(min_n: int = 10_000) -> None:
    a = pd.read_parquet(config.INTERIM / f"chembl{V}_human_sp_activities.parquet",
                        columns=["tid", "act_src_id", "pchembl_value"])
    t = pd.read_parquet(config.INTERIM / f"chembl{V}_human_sp_targets.parquet", columns=["tid", "family_l2"])
    a = a[a.pchembl_value.notna()].merge(t, on="tid")
    a["pubchem"] = a.act_src_id == PUBCHEM_SRC_ID
    rows = []
    for fam, g in a.groupby("family_l2"):
        if len(g) < min_n or fam in ("Multiple", "Unclassified"):
            continue
        rows.append({
            "family_l2": fam, "pchembl_n": len(g), "pubchem_share": g.pubchem.mean(),
            "median_all": g.pchembl_value.median(),
            "median_excl_pubchem": g.loc[~g.pubchem, "pchembl_value"].median(),
            "median_pubchem_only": g.loc[g.pubchem, "pchembl_value"].median() if g.pubchem.any() else float("nan"),
        })
    out = pd.DataFrame(rows)
    out["shift_when_excluding_pubchem"] = out.median_excl_pubchem - out.median_all
    out = out.sort_values("pchembl_n", ascending=False)
    out.to_csv(config.STAGE0 / "pchembl_source_confounding.csv", index=False, float_format="%.4g", lineterminator="\n")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
