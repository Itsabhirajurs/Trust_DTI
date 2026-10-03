"""Week 2 scope analysis — produce the evidence to lock Network 1's label/scope rules.

Reads the Stage 1 extract and writes decision-grounding tables to reports/week2/.
Makes NO decisions; it quantifies the options so DECISIONS.md can cite real numbers.

Covers the open issues in docs/STATUS.md:
  A endpoint families (which standard_types are usable affinities)
  B pChEMBL distribution for dose-response exact values (where is the natural cut?)
  C active/inactive threshold sensitivity (grid of cuts -> label counts, with/without PubChem)
  D measured-inactive sources (comment / censored / measured-weak)
  E minimum data per protein (how many proteins survive, with both actives and inactives)
  F temporal cutoff (how much train/test among dated records at candidate years)
  G class balance under the recommended scheme

Run: python -m src.ingest.analyze_scope_week2
"""
import json

import numpy as np
import pandas as pd

from src import config

V = config.CHEMBL_VERSION
OUT = config.REPORTS / "week2"
PUBCHEM = 7

AFFINITY_DR = ["IC50", "Ki", "Kd", "EC50"]          # dose-response affinities we threshold on
QHTS = ["Potency", "AC50"]                           # qHTS-derived, noisier
INACTIVE_COMMENT = r"^\s*(?:inactive|not active|no activity|no significant activity|not significant|non[- ]?active)\b"


def _csv(df, name):
    df.to_csv(OUT / name, index=False, float_format="%.4g", lineterminator="\n")


def load():
    a = pd.read_parquet(config.INTERIM / f"chembl{V}_human_sp_activities.parquet",
                        columns=["molregno", "tid", "standard_type", "standard_relation", "standard_value",
                                 "standard_units", "pchembl_value", "act_src_id", "confidence_score",
                                 "doc_year", "activity_comment"])
    t = pd.read_parquet(config.INTERIM / f"chembl{V}_human_sp_targets.parquet") \
          .sort_values(["tid", "component_id"]).drop_duplicates("tid")[["tid", "accession", "family_l1"]]
    return a.merge(t, on="tid")


def build_pair_labels(a, act_cut, inact_cut, use_qhts_inactive=True):
    """Collapse to one row per (compound, protein) and assign a provisional 3-state label.
    Returns a DataFrame: molregno, accession, family_l1, n_dr_exact, median_p, label."""
    dr = a[a.standard_type.isin(AFFINITY_DR)].copy()
    exact = dr[(dr.standard_relation == "=") & (dr.standard_units == "nM") & (dr.standard_value > 0)].copy()
    exact["p"] = 9.0 - np.log10(exact.standard_value)
    med = exact.groupby(["molregno", "accession"]).p.agg(["median", "count"]).rename(
        columns={"median": "median_p", "count": "n_dr_exact"})

    # inactive signals that don't need an exact value
    cens_inact = dr[dr.standard_relation.isin([">", ">=", ">>"]) & (dr.standard_units == "nM")
                    & (dr.standard_value >= 10_000)][["molregno", "accession"]].drop_duplicates()
    cens_inact["has_cens_inactive"] = True
    comm = a[a.activity_comment.str.lower().str.contains(INACTIVE_COMMENT, regex=True, na=False)][
        ["molregno", "accession"]].drop_duplicates()
    comm["has_comment_inactive"] = True
    qhts_inact = pd.DataFrame(columns=["molregno", "accession", "has_qhts_inactive"])
    if use_qhts_inactive:
        q = a[a.standard_type.isin(QHTS) & (a.standard_relation.isin([">", ">=", ">>"]))
              & (a.standard_units == "nM") & (a.standard_value >= 10_000)][["molregno", "accession"]].drop_duplicates()
        q["has_qhts_inactive"] = True
        qhts_inact = q

    all_pairs = a[["molregno", "accession", "family_l1"]].drop_duplicates(["molregno", "accession"])
    df = all_pairs.merge(med, on=["molregno", "accession"], how="left") \
                  .merge(cens_inact, on=["molregno", "accession"], how="left") \
                  .merge(comm, on=["molregno", "accession"], how="left") \
                  .merge(qhts_inact, on=["molregno", "accession"], how="left")
    for c in ["has_cens_inactive", "has_comment_inactive", "has_qhts_inactive"]:
        df[c] = df[c].fillna(False)
    df["n_dr_exact"] = df["n_dr_exact"].fillna(0).astype(int)

    label = pd.Series("UNTESTED", index=df.index)
    has_p = df.median_p.notna()
    label[has_p & (df.median_p >= act_cut)] = "ACTIVE"
    label[has_p & (df.median_p <= inact_cut)] = "INACTIVE"
    label[has_p & (df.median_p > inact_cut) & (df.median_p < act_cut)] = "GRAY"
    weak = ~has_p & (df.has_cens_inactive | df.has_comment_inactive | df.has_qhts_inactive)
    label[weak] = "INACTIVE"
    df["label"] = label
    return df


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a = load()
    summary = {}

    # A. endpoint families
    st = a.standard_type.value_counts()
    def bucket(name):
        if name in AFFINITY_DR: return "affinity_dose_response"
        if name in QHTS: return "qHTS"
        low = str(name).lower()
        if "k_on" in low or "k_off" in low or low in ("kon", "koff"): return "kinetics"
        if "inhib" in low or "control" in low or "activity" in low or "residual" in low or "%" in low or "effect" in low: return "percent_or_single_point"
        return "other"
    bucketed = st.rename_axis("standard_type").reset_index(name="rows")
    bucketed["bucket"] = bucketed.standard_type.map(bucket)
    _csv(bucketed.head(50), "A_standard_type_top50.csv")
    _csv(bucketed.groupby("bucket").rows.sum().sort_values(ascending=False).reset_index(), "A_endpoint_buckets.csv")
    summary["endpoint_buckets"] = bucketed.groupby("bucket").rows.sum().sort_values(ascending=False).to_dict()

    # B. pChEMBL distribution for dose-response exact values, overall and excl PubChem
    dr = a[a.standard_type.isin(AFFINITY_DR) & (a.standard_relation == "=") & (a.standard_units == "nM") & (a.standard_value > 0)].copy()
    dr["p"] = 9.0 - np.log10(dr.standard_value)
    def dist(s):
        return {q: round(float(np.percentile(s, q)), 3) for q in (5, 10, 25, 50, 75, 90, 95)}
    summary["pchembl_dr_exact"] = {"n": int(len(dr)), "all": dist(dr.p),
                                   "excl_pubchem": dist(dr.loc[dr.act_src_id != PUBCHEM, "p"])}

    # C. threshold sensitivity grid
    grid = []
    for act in (6.0, 6.5, 7.0):
        for inact in (5.0, 5.5):
            lab = build_pair_labels(a, act, inact)
            vc = lab.label.value_counts()
            grid.append({"active_cut": act, "inactive_cut": inact,
                         "ACTIVE": int(vc.get("ACTIVE", 0)), "INACTIVE": int(vc.get("INACTIVE", 0)),
                         "GRAY": int(vc.get("GRAY", 0)), "UNTESTED": int(vc.get("UNTESTED", 0)),
                         "active_per_inactive": round(vc.get("ACTIVE", 0) / max(vc.get("INACTIVE", 1), 1), 3)})
    _csv(pd.DataFrame(grid), "C_threshold_grid.csv")
    summary["threshold_grid"] = grid

    # Recommended scheme for D-G: active>=6.5, inactive<=5.0
    lab = build_pair_labels(a, 6.5, 5.0)
    _csv(lab.label.value_counts().rename_axis("label").reset_index(name="pairs"), "D_label_counts_recommended.csv")
    lab_labeled = lab[lab.label.isin(["ACTIVE", "INACTIVE"])]

    # D. inactive source breakdown
    inact = lab[lab.label == "INACTIVE"]
    summary["inactive_sources"] = {
        "total_inactive_pairs": int(len(inact)),
        "from_exact_weak_measure": int((inact.median_p.notna()).sum()),
        "from_censored_only": int((inact.median_p.isna() & inact.has_cens_inactive).sum()),
        "from_comment_only": int((inact.median_p.isna() & ~inact.has_cens_inactive & inact.has_comment_inactive).sum()),
        "from_qhts_only": int((inact.median_p.isna() & ~inact.has_cens_inactive & ~inact.has_comment_inactive & inact.has_qhts_inactive).sum()),
    }

    # E. minimum data per protein (target-cold viability)
    perprot = lab_labeled.groupby("accession").label.value_counts().unstack(fill_value=0)
    perprot["total"] = perprot.sum(axis=1)
    rows = []
    for m in (5, 10, 20, 50, 100):
        keep = perprot[perprot.total >= m]
        both = keep[(keep.get("ACTIVE", 0) >= 1) & (keep.get("INACTIVE", 0) >= 1)]
        rows.append({"min_labeled_pairs": m, "proteins": int(len(keep)),
                     "proteins_with_both_classes": int(len(both)),
                     "labeled_pairs_retained": int(keep.total.sum())})
    _csv(pd.DataFrame(rows), "E_min_data_per_protein.csv")
    summary["min_data_per_protein"] = rows

    # F. temporal cutoff (among dated labeled pairs). A pair's year = min doc_year of its records.
    yr = a.groupby(["molregno", "accession"]).doc_year.min().rename("year").reset_index()
    lp = lab_labeled.merge(yr, on=["molregno", "accession"], how="left")
    dated = lp[lp.year.notna()]
    rows = []
    for cut in (2018, 2019, 2020, 2021):
        tr = int((dated.year < cut).sum()); te = int((dated.year >= cut).sum())
        rows.append({"cutoff_year": cut, "train_pairs_pre": tr, "test_pairs_post": te,
                     "pct_test": round(te / max(tr + te, 1) * 100, 1)})
    _csv(pd.DataFrame(rows), "F_temporal_cutoff.csv")
    summary["temporal"] = {"labeled_pairs_with_year": int(len(dated)),
                           "labeled_pairs_without_year": int(len(lp) - len(dated)), "cutoffs": rows}

    # G. class balance
    vc = lab_labeled.label.value_counts()
    summary["recommended_scheme"] = {"active_cut": 6.5, "inactive_cut": 5.0,
                                     "ACTIVE": int(vc.get("ACTIVE", 0)), "INACTIVE": int(vc.get("INACTIVE", 0)),
                                     "active_per_inactive": round(vc.get("ACTIVE", 0) / max(vc.get("INACTIVE", 1), 1), 3)}

    (OUT / "week2_scope_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
