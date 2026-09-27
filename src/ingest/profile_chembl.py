"""Week 1 D2 + D4 (+ the D5 family table) — profile the human single-protein ChEMBL extract.

Reads the parquet written by chembl_extract.py and writes small, deterministic
CSV/PNG outputs to reports/stage0/. No scope decisions are made here — these are
the numbers Week 2 will use to make them.

Run: python -m src.ingest.profile_chembl
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config
from src.ingest.relations import CENSORED_RELATIONS

V = config.CHEMBL_VERSION
ACT = config.INTERIM / f"chembl{V}_human_sp_activities.parquet"
TGT = config.INTERIM / f"chembl{V}_human_sp_targets.parquet"
OUT = config.STAGE0

# Inactive-like free-text comments. A Week 1 *estimate* only — the precise
# measured-inactive count and its rules are a Week 2 task.
INACTIVE_PATTERNS = {
    "inactive_or_not_active": r"^\s*(?:inactive|not active|no activity|no significant activity|not significant|non[- ]?active)\b",
    "lt50pct_at_10uM_no_curve": r"^\s*inhibition < 50% @ 10 um",
}
# Deliberately NOT inactive: 'inconclusive', 'not determined', 'nd', 'na' — these are closer to UNTESTED.


def _csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False, float_format="%.4g", lineterminator="\n")


def load() -> pd.DataFrame:
    act = pd.read_parquet(ACT)
    tgt = pd.read_parquet(TGT).sort_values(["tid", "component_id"]).drop_duplicates("tid")
    return act.merge(tgt[["tid", "accession", "family_l1", "family_l2"]], on="tid", how="left")


def headline(df: pd.DataFrame) -> dict:
    exact = df[(df.standard_relation == "=") & df.standard_value.notna()]
    h = {
        "activity_rows": len(df),
        "distinct_compounds_molregno": df.molregno.nunique(),
        "distinct_compounds_inchikey": df.inchikey.nunique(),
        "compounds_missing_inchikey": int(df.loc[df.inchikey.isna(), "molregno"].nunique()),
        "distinct_targets_tid": df.tid.nunique(),
        "distinct_proteins_accession": df.accession.nunique(),
        "pairs_any_activity": int(df[["molregno", "accession"]].drop_duplicates().shape[0]),
        "pairs_with_pchembl": int(df.loc[df.pchembl_value.notna(), ["molregno", "accession"]].drop_duplicates().shape[0]),
        "pairs_with_exact_value": int(exact[["molregno", "accession"]].drop_duplicates().shape[0]),
        "rows_censored_relation": int(df.standard_relation.isin(CENSORED_RELATIONS).sum()),
        "rows_censored_with_null_pchembl": int((df.standard_relation.isin(CENSORED_RELATIONS) & df.pchembl_value.isna()).sum()),
        "approved_drugs_max_phase_4": int(df.loc[df.max_phase == 4, "molregno"].nunique()),
    }
    return {k: int(v) for k, v in h.items()}


def skew(df: pd.DataFrame) -> dict:
    pairs = df[["molregno", "accession"]].drop_duplicates()
    per_prot = pairs.groupby("accession").size().sort_values(ascending=False)
    per_cmp = pairs.groupby("molregno").size().sort_values(ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, s, what in [(axes[0], per_prot, "protein"), (axes[1], per_cmp, "compound")]:
        bins = np.logspace(0, np.log10(s.max() + 1), 40)
        ax.hist(s, bins=bins, color="#2a6f97")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel(f"distinct partners per {what} (log)"); ax.set_ylabel(f"# {what}s (log)")
        ax.set_title(f"Interactions per {what} (n={len(s):,}, median={int(s.median())})")
    fig.suptitle(f"ChEMBL {V} human single-protein: compound–protein pairs with ≥1 activity record")
    fig.tight_layout(); fig.savefig(OUT / "skew_interactions.png", dpi=120); plt.close(fig)

    def top_share(s, frac):
        k = max(1, int(round(len(s) * frac)))
        return float(s.iloc[:k].sum() / s.sum())

    return {
        "proteins_median_partners": float(per_prot.median()),
        "proteins_with_lt10_partners": int((per_prot < 10).sum()),
        "proteins_with_ge100_partners": int((per_prot >= 100).sum()),
        "top10pct_proteins_share_of_pairs": round(top_share(per_prot, 0.10), 4),
        "compounds_median_partners": float(per_cmp.median()),
        "compounds_with_1_partner": int((per_cmp == 1).sum()),
    }


def family_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (l1, l2), g in df.groupby(["family_l1", "family_l2"], dropna=False):
        p = g.pchembl_value.dropna()
        pairs = g[["molregno", "accession"]].drop_duplicates()
        per_prot = pairs.groupby("accession").size()
        rows.append({
            "family_l1": l1, "family_l2": l2,
            "proteins": g.accession.nunique(),
            "compounds": g.molregno.nunique(),
            "pairs": len(pairs),
            "activity_rows": len(g),
            "median_pairs_per_protein": float(per_prot.median()),
            "proteins_ge100_pairs": int((per_prot >= 100).sum()),
            "median_confidence": float(g.confidence_score.median()),
            "share_conf9": float((g.confidence_score == 9).mean()),
            "pchembl_n": len(p),
            "pchembl_median": float(p.median()) if len(p) else np.nan,
            "pchembl_iqr": float(p.quantile(.75) - p.quantile(.25)) if len(p) else np.nan,
            "pchembl_skew": float(p.skew()) if len(p) > 2 else np.nan,
            "share_ge_pchembl6": float((p >= 6).mean()) if len(p) else np.nan,
            "censored_rows": int(g.standard_relation.isin(CENSORED_RELATIONS).sum()),
        })
    return pd.DataFrame(rows).sort_values("pairs", ascending=False)


def d4_tables(df: pd.DataFrame, sources: pd.DataFrame) -> dict:
    t = {}
    t["confidence_score"] = df.confidence_score.value_counts(dropna=False).rename_axis("confidence_score").reset_index(name="rows").sort_values("confidence_score")
    t["standard_type_top40"] = df.standard_type.value_counts(dropna=False).head(40).rename_axis("standard_type").reset_index(name="rows")
    t["standard_relation"] = df.standard_relation.value_counts(dropna=False).rename_axis("standard_relation").reset_index(name="rows")
    t["assay_type"] = df.assay_type.value_counts(dropna=False).rename_axis("assay_type").reset_index(name="rows")
    src = df.groupby("act_src_id").agg(rows=("activity_id", "size"),
                                       pairs=("molregno", "size"),
                                       with_pchembl=("pchembl_value", lambda s: int(s.notna().sum())),
                                       missing_doc_year=("doc_year", lambda s: int(s.isna().sum())))
    src["pairs"] = df.groupby("act_src_id").apply(lambda g: g[["molregno", "accession"]].drop_duplicates().shape[0], include_groups=False)
    t["sources"] = src.reset_index().merge(sources, left_on="act_src_id", right_on="src_id", how="left") \
                      .drop(columns="src_id").sort_values("rows", ascending=False)
    comment = df.activity_comment.str.strip().str.lower()
    t["activity_comment_top40"] = comment.value_counts(dropna=False).head(40).rename_axis("activity_comment").reset_index(name="rows")
    t["data_validity_comment"] = df.data_validity_comment.value_counts(dropna=False).rename_axis("data_validity_comment").reset_index(name="rows")
    t["potential_duplicate"] = df.potential_duplicate.value_counts(dropna=False).rename_axis("potential_duplicate").reset_index(name="rows")
    miss_cols = ["standard_value", "standard_relation", "standard_units", "pchembl_value", "confidence_score", "doc_year", "inchikey", "accession"]
    t["missingness"] = pd.DataFrame({"column": miss_cols,
                                     "missing_rows": [int(df[c].isna().sum()) for c in miss_cols],
                                     "missing_share": [float(df[c].isna().mean()) for c in miss_cols]})
    yr = df.doc_year.dropna().astype(int)
    t["doc_year_by_5y"] = (yr // 5 * 5).value_counts().sort_index().rename_axis("year_bin_start").reset_index(name="rows")
    return t


def inactive_estimate(df: pd.DataFrame) -> dict:
    lc = df.activity_comment.str.lower()
    by_pattern = {k: lc.str.contains(rx, regex=True, na=False) for k, rx in INACTIVE_PATTERNS.items()}
    comment_inactive = pd.concat(by_pattern, axis=1).any(axis=1)
    conc_types = df.standard_type.isin(["IC50", "Ki", "Kd", "EC50"])
    nm = df.standard_units == "nM"
    censored_weak = conc_types & nm & df.standard_relation.isin([">", ">=", ">>"]) & (df.standard_value >= 10_000)
    any_inactive = comment_inactive | censored_weak
    pairs = lambda m: int(df.loc[m, ["molregno", "accession"]].drop_duplicates().shape[0])
    return {
        **{f"rows_comment_{k}": int(m.sum()) for k, m in by_pattern.items()},
        "rows_comment_inactive_like": int(comment_inactive.sum()),
        "rows_comment_inconclusive_NOT_counted": int((lc.str.strip() == "inconclusive").sum()),
        "rows_censored_ge_10uM": int(censored_weak.sum()),
        "rows_either": int(any_inactive.sum()),
        "pairs_either": pairs(any_inactive),
        "pairs_either_conf9": pairs(any_inactive & (df.confidence_score == 9)),
        "note": "Week 1 estimate only; the precise measured-inactive count and rule set is a Week 2 task.",
    }


def pchembl_plot(df: pd.DataFrame, fam: pd.DataFrame) -> None:
    top = fam[~fam.family_l2.isin(["Unclassified", "Multiple"])].nlargest(3, "pchembl_n").family_l2.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    bins = np.arange(2, 12.25, 0.25)
    axes[0].hist(df.pchembl_value.dropna(), bins=bins, color="#2a6f97")
    axes[0].set_title(f"pChEMBL, all human single-protein (n={df.pchembl_value.notna().sum():,})")
    for f in top:
        p = df.loc[df.family_l2 == f, "pchembl_value"].dropna()
        axes[1].hist(p, bins=bins, histtype="step", density=True, linewidth=1.6, label=f"{f} (n={len(p):,})")
    axes[1].set_title("pChEMBL by family (density), top 3 by volume"); axes[1].legend(fontsize=8)
    for ax in axes:
        ax.set_xlabel("pChEMBL"); ax.axvline(6, color="grey", ls="--", lw=0.8)
    fig.tight_layout(); fig.savefig(OUT / "pchembl_distribution.png", dpi=120); plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()
    sources = pd.read_csv(OUT / "chembl_sources.csv")
    summary = {"headline": headline(df), "skew": skew(df), "inactive_estimate": inactive_estimate(df)}
    fam = family_table(df)
    _csv(fam, "family_table.csv")
    l1 = fam.groupby("family_l1")[["proteins", "compounds", "pairs", "activity_rows"]].sum() \
            .sort_values("pairs", ascending=False).reset_index()
    l1["proteins"] = df.groupby("family_l1").accession.nunique().reindex(l1.family_l1).values
    l1["compounds"] = df.groupby("family_l1").molregno.nunique().reindex(l1.family_l1).values
    _csv(l1, "family_l1_counts.csv")
    for name, t in d4_tables(df, sources).items():
        _csv(t, f"d4_{name}.csv")
    pchembl_plot(df, fam)
    (OUT / "chembl_profile_summary.json").write_text(json.dumps(summary, indent=2, default=float) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
