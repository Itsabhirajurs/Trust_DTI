"""Week 1 D3 — ChEMBL vs BindingDB overlap on (InChIKey, UniProt accession).

The two databases import from each other: ChEMBL 37 carries 'BindingDB Patent
Bioactivity Data' as a source, and ~52% of BindingDB's human single-chain rows are
curated *from* ChEMBL. A naive overlap is therefore inflated by construction, so
overlap is reported three ways:
  A. everything vs everything (naive)
  B. ChEMBL minus its BindingDB-sourced records vs everything in BindingDB
  C. independent-only: ChEMBL minus BindingDB-sourced vs BindingDB minus ChEMBL-sourced
C is the honest answer to "what would a BindingDB merge add?".

Also: a 20-pair potency spot-check on independently-sourced overlapping pairs.

Run: python -m src.ingest.profile_overlap   (after chembl_extract + bindingdb_extract)
"""
import json

import numpy as np
import pandas as pd

from src import config
from src.ingest.relations import nm_to_p

V = config.CHEMBL_VERSION
OUT = config.STAGE0
BDB = config.INTERIM / f"bindingdb_{config.BINDINGDB_RELEASE}_human_single_chain.parquet"


def chembl_bindingdb_src_ids(sources: pd.DataFrame) -> list:
    m = sources.src_short_name.str.contains("BINDINGDB", case=False, na=False) | \
        sources.src_description.str.contains("BindingDB", case=False, na=False)
    return sorted(sources.loc[m, "src_id"].astype(int).tolist())


def overlap(a: pd.DataFrame, b: pd.DataFrame, label: str) -> dict:
    ca, cb = set(a.inchikey.dropna()), set(b.inchikey.dropna())
    pa_, pb = set(a.accession.dropna()), set(b.accession.dropna())
    ka = set(zip(a.inchikey, a.accession)); kb = set(zip(b.inchikey, b.accession))
    ca14 = {k[:14] for k in ca}; cb14 = {k[:14] for k in cb}
    return {
        "comparison": label,
        "compounds_both": len(ca & cb), "compounds_chembl_only": len(ca - cb), "compounds_bdb_only": len(cb - ca),
        "compounds_both_connectivity14": len(ca14 & cb14), "compounds_bdb_only_connectivity14": len(cb14 - ca14),
        "proteins_both": len(pa_ & pb), "proteins_chembl_only": len(pa_ - pb), "proteins_bdb_only": len(pb - pa_),
        "pairs_both": len(ka & kb), "pairs_chembl_only": len(ka - kb), "pairs_bdb_only": len(kb - ka),
    }


def spot_check(ch: pd.DataFrame, bdb: pd.DataFrame, n: int = 20) -> tuple[pd.DataFrame, dict]:
    """Compare exact IC50/Ki potencies for pairs present in both *independent* subsets."""
    rows = []
    for ep, col in [("IC50", "ic50"), ("Ki", "ki")]:
        c = ch[(ch.standard_type == ep) & (ch.standard_relation == "=") & (ch.standard_units == "nM")
               & ch.standard_value.gt(0)]
        c = c.assign(p=nm_to_p(c.standard_value)).groupby(["inchikey", "accession"]).p.median().rename("p_chembl")
        b = bdb[(bdb[f"{col}_relation"] == "=") & bdb[f"{col}_nm"].gt(0)]
        b = b.assign(p=nm_to_p(b[f"{col}_nm"])).groupby(["inchikey", "accession"]).p.median().rename("p_bdb")
        j = pd.concat([c, b], axis=1, join="inner").reset_index()
        j["endpoint"] = ep
        rows.append(j)
    allj = pd.concat(rows, ignore_index=True)
    allj["abs_diff"] = (allj.p_chembl - allj.p_bdb).abs()
    agg = {
        "overlapping_exact_pairs": len(allj),
        "median_abs_diff_log_units": float(allj.abs_diff.median()) if len(allj) else None,
        "share_within_0.5_log": float((allj.abs_diff <= 0.5).mean()) if len(allj) else None,
        "share_within_1.0_log": float((allj.abs_diff <= 1.0).mean()) if len(allj) else None,
    }
    sample = allj.sample(min(n, len(allj)), random_state=0).sort_values(["endpoint", "accession"])
    return sample, agg


def main() -> None:
    sources = pd.read_csv(OUT / "chembl_sources.csv")
    bdb_src = chembl_bindingdb_src_ids(sources)

    ch = pd.read_parquet(config.INTERIM / f"chembl{V}_human_sp_activities.parquet",
                         columns=["inchikey", "tid", "act_src_id", "standard_type", "standard_relation",
                                  "standard_value", "standard_units"])
    tgt = pd.read_parquet(config.INTERIM / f"chembl{V}_human_sp_targets.parquet").sort_values(["tid", "component_id"]).drop_duplicates("tid")
    ch = ch.merge(tgt[["tid", "accession"]], on="tid").dropna(subset=["inchikey", "accession"])
    bdb = pd.read_parquet(BDB).rename(columns={"uniprot": "accession"}).dropna(subset=["inchikey", "accession"])
    bdb["accession"] = bdb.accession.str.split(",").str[0].str.strip()

    ch_indep = ch[~ch.act_src_id.isin(bdb_src)]
    bdb_indep = bdb[bdb.curation_source.str.strip() != "ChEMBL"]

    ov = pd.DataFrame([
        overlap(ch, bdb, "A_naive_all_vs_all"),
        overlap(ch_indep, bdb, "B_chembl_minus_bdbsrc_vs_bdb_all"),
        overlap(ch_indep, bdb_indep, "C_independent_vs_independent"),
    ])
    ov.to_csv(OUT / "d3_overlap.csv", index=False, lineterminator="\n")

    # what does independent BindingDB add, by its curation source?
    ch_pairs = set(zip(ch.inchikey, ch.accession))
    ch_prots = set(ch.accession)
    bysrc = []
    for src, g in bdb_indep.groupby("curation_source"):
        pairs = set(zip(g.inchikey, g.accession))
        bysrc.append({"bdb_curation_source": src, "rows": len(g), "pairs": len(pairs),
                      "pairs_not_in_chembl": len(pairs - ch_pairs),
                      "proteins_not_in_chembl": len(set(g.accession) - ch_prots)})
    pd.DataFrame(bysrc).sort_values("pairs_not_in_chembl", ascending=False) \
      .to_csv(OUT / "d3_bdb_novel_by_source.csv", index=False, lineterminator="\n")

    sample, agg = spot_check(ch_indep, bdb_indep)
    sample.to_csv(OUT / "d3_potency_spotcheck_20.csv", index=False, float_format="%.3f", lineterminator="\n")

    summary = {"chembl_bindingdb_src_ids": bdb_src,
               "chembl_rows_from_bindingdb_src": int(ch.act_src_id.isin(bdb_src).sum()),
               "chembl_rows_total_keyed": len(ch),
               "bdb_rows_from_chembl": int((bdb.curation_source.str.strip() == "ChEMBL").sum()),
               "bdb_rows_total_keyed": len(bdb),
               "potency_agreement_independent": agg}
    (OUT / "d3_overlap_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(ov.T.to_string()); print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
