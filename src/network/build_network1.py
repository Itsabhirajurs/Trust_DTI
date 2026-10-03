"""Stage 2 step 2 — build Network 1: one labelled row per (compound, protein) pair + 4 splits.

Implements the Week 2 decisions:
  D-011 label only from affinity dose-response (IC50/Ki/Kd/EC50); qHTS only as inactive evidence
  D-012 ACTIVE median pChEMBL >= 6.5; INACTIVE <= 5.0 or weak/censored/comment/qhts; GRAY excluded
  D-014 compound identity = salt-stripped parent InChIKey (from standardize_compounds)
  D-015 keep proteins with >= 10 labelled pairs
  D-016 temporal cutoff 2020
  D-018 median aggregation, keep IQR, drop transcription/author-error rows
  D-019 four splits (random, drug-cold by scaffold, target-cold by protein, temporal), seed 42,
        each with a calibration slice carved from its own train; leakage check must pass

Output (gitignored): data/processed/network1_v1.parquet
Manifest (committed):  reports/week2/network1_v1_manifest.json

Run: python -m src.network.build_network1   (after standardize_compounds)
"""
import json

import numpy as np
import pandas as pd

from src import config

V = config.CHEMBL_VERSION
SEED = 42
ACT_CUT, INACT_CUT = 6.5, 5.0
MIN_PAIRS_PER_PROTEIN = 10
TEMPORAL_CUTOFF = 2020
TEST_FRAC, CALIB_FRAC = 0.15, 0.15  # of groups (or pairs for random); train = the rest
AFFINITY_DR = ["IC50", "Ki", "Kd", "EC50"]
QHTS = ["Potency", "AC50"]
INACTIVE_COMMENT = r"^\s*(?:inactive|not active|no activity|no significant activity|not significant|non[- ]?active)\b"
BAD_VALIDITY = ["Potential transcription error", "Potential author error"]

OUT = config.PROCESSED / "network1_v1.parquet"
MANIFEST = config.REPORTS / "week2" / "network1_v1_manifest.json"


def assign_groups(keys, seed, test_frac, calib_frac):
    """Shuffle unique group keys and split into test / calib / train. Returns dict key->partition."""
    rng = np.random.default_rng(seed)
    keys = np.array(sorted(set(keys)))
    rng.shuffle(keys)
    n = len(keys)
    n_test = int(round(n * test_frac))
    n_calib = int(round(n * calib_frac))
    part = {}
    for i, k in enumerate(keys):
        part[k] = "test" if i < n_test else ("calib" if i < n_test + n_calib else "train")
    return part


def _uniq_pairs(a, mask, name):
    """Unique (pik, accession) rows where mask is True, tagged with a True boolean column (vectorised)."""
    d = a.loc[mask, ["pik", "accession"]].drop_duplicates()
    d[name] = True
    return d


def main():
    import gc
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    # --- load (drop the big free-text column as soon as its signal is extracted) ---
    a = pd.read_parquet(config.INTERIM / f"chembl{V}_human_sp_activities.parquet",
                        columns=["molregno", "tid", "standard_type", "standard_relation", "standard_value",
                                 "standard_units", "activity_comment", "data_validity_comment", "doc_year"])
    a = a[~a.data_validity_comment.isin(BAD_VALIDITY)].drop(columns="data_validity_comment")
    a["comment_inactive"] = a.activity_comment.str.lower().str.contains(INACTIVE_COMMENT, regex=True, na=False)
    a = a.drop(columns="activity_comment")  # free the ~1 GB text column immediately
    for c in ["standard_type", "standard_relation", "standard_units"]:
        a[c] = a[c].astype("category")
    print(f"  loaded {len(a):,} rows", flush=True)

    t = pd.read_parquet(config.INTERIM / f"chembl{V}_human_sp_targets.parquet") \
          .sort_values(["tid", "component_id"]).drop_duplicates("tid")[["tid", "accession", "family_l1"]]
    std = pd.read_parquet(config.INTERIM / "compounds_standardized.parquet")
    std_ok = std[(std.status == "ok") & std.parent_inchikey.notna()]
    mol2pik = std_ok[["molregno", "parent_inchikey"]].rename(columns={"parent_inchikey": "pik"})
    pik2scaf = std_ok.rename(columns={"parent_inchikey": "pik"}).drop_duplicates("pik")[["pik", "scaffold"]]
    del std
    gc.collect()

    a = a.merge(t, on="tid").merge(mol2pik, on="molregno", how="inner")  # inner: drop failed standardisation
    a = a.drop(columns=["tid", "molregno"])
    print(f"  mapped to parent InChIKey: {len(a):,} rows", flush=True)

    # --- median potency per (pik, accession) from exact dose-response affinities ---
    is_dr = a.standard_type.isin(AFFINITY_DR) & (a.standard_units == "nM") & (a.standard_value > 0)
    exact = a[is_dr & (a.standard_relation == "=")].copy()
    exact["p"] = 9.0 - np.log10(exact.standard_value)
    g = exact.groupby(["pik", "accession"], observed=True).p
    med = g.agg(median_p="median", n_exact="count")
    q = g.quantile([.25, .75]).unstack()           # vectorised IQR, no lambdas
    med["iqr"] = q[0.75] - q[0.25]
    med = med.reset_index()
    del exact
    gc.collect()
    print(f"  pairs with an exact affinity: {len(med):,}", flush=True)

    # --- inactive-signal pairs (vectorised unique-pair frames, no Python sets) ---
    cens = _uniq_pairs(a, is_dr & a.standard_relation.isin([">", ">=", ">>"]) & (a.standard_value >= 10_000), "has_cens")
    comm = _uniq_pairs(a, a.comment_inactive, "has_comment")
    qhts = _uniq_pairs(a, a.standard_type.isin(QHTS) & a.standard_relation.isin([">", ">=", ">>"])
                       & (a.standard_units == "nM") & (a.standard_value >= 10_000), "has_qhts")
    yr = a.groupby(["pik", "accession"], observed=True).doc_year.min().rename("year").reset_index()
    del a
    gc.collect()
    print("  signals extracted; assembling labels", flush=True)

    # --- assemble labelable pairs via outer merges (vectorised) ---
    df = med
    for d in (cens, comm, qhts):
        df = df.merge(d, on=["pik", "accession"], how="outer")
    for c in ["has_cens", "has_comment", "has_qhts"]:
        df[c] = df[c].fillna(False)

    has_p = df.median_p.notna()
    label = np.where(has_p & (df.median_p >= ACT_CUT), "ACTIVE",
             np.where(has_p & (df.median_p <= INACT_CUT), "INACTIVE",
             np.where(has_p, "GRAY",
             np.where(df.has_cens | df.has_comment | df.has_qhts, "INACTIVE", "UNTESTED"))))
    df["label"] = label
    labelled = df[df.label.isin(["ACTIVE", "INACTIVE"])].copy()

    # --- attach scaffold, family, year (yr was computed before `a` was freed) ---
    labelled = labelled.merge(pik2scaf, on="pik", how="left")
    fam = t.drop_duplicates("accession")[["accession", "family_l1"]]
    labelled = labelled.merge(fam, on="accession", how="left")
    labelled = labelled.merge(yr, on=["pik", "accession"], how="left")

    # --- min data per protein (D-015) ---
    counts = labelled.accession.value_counts()
    keep_prot = counts[counts >= MIN_PAIRS_PER_PROTEIN].index
    before = len(labelled)
    labelled = labelled[labelled.accession.isin(keep_prot)].reset_index(drop=True)

    # scaffold group key: use scaffold, but acyclic (empty) -> fall back to the compound itself
    labelled["scaffold_group"] = np.where(labelled.scaffold.fillna("") == "",
                                           "ACYCLIC::" + labelled.pik, labelled.scaffold)

    # --- splits (D-019) ---
    rng = np.random.default_rng(SEED)
    # random: per-pair stratified by label
    labelled["split_random"] = "train"
    for lab, g in labelled.groupby("label"):
        idx = g.index.to_numpy().copy(); rng.shuffle(idx)
        n_test = int(round(len(idx) * TEST_FRAC)); n_cal = int(round(len(idx) * CALIB_FRAC))
        labelled.loc[idx[:n_test], "split_random"] = "test"
        labelled.loc[idx[n_test:n_test + n_cal], "split_random"] = "calib"
    # drug-cold: by scaffold group
    g = assign_groups(labelled.scaffold_group, SEED + 1, TEST_FRAC, CALIB_FRAC)
    labelled["split_drugcold"] = labelled.scaffold_group.map(g)
    # target-cold: by accession
    g = assign_groups(labelled.accession, SEED + 2, TEST_FRAC, CALIB_FRAC)
    labelled["split_targetcold"] = labelled.accession.map(g)
    # temporal: < cutoff train (minus a calib carve), >= cutoff test, undated excluded
    labelled["split_temporal"] = pd.NA
    pre = labelled.year.notna() & (labelled.year < TEMPORAL_CUTOFF)
    post = labelled.year.notna() & (labelled.year >= TEMPORAL_CUTOFF)
    labelled.loc[post, "split_temporal"] = "test"
    pre_idx = labelled.index[pre].to_numpy().copy(); rng.shuffle(pre_idx)
    n_cal = int(round(len(pre_idx) * CALIB_FRAC))
    labelled.loc[pre_idx[:n_cal], "split_temporal"] = "calib"
    labelled.loc[pre_idx[n_cal:], "split_temporal"] = "train"

    labelled["provenance"] = "measured"

    # --- leakage checks ---
    def groups_in(colsplit, groupcol):
        tr = set(labelled.loc[labelled[colsplit] == "train", groupcol])
        ca = set(labelled.loc[labelled[colsplit] == "calib", groupcol])
        te = set(labelled.loc[labelled[colsplit] == "test", groupcol])
        return {"train_test_overlap": len(tr & te), "calib_test_overlap": len(ca & te),
                "train_calib_overlap": len(tr & ca)}
    leak = {
        "drugcold_by_scaffold": groups_in("split_drugcold", "scaffold_group"),
        "targetcold_by_accession": groups_in("split_targetcold", "accession"),
        "temporal_calib_vs_test_by_year": {
            "calib_max_year": int(labelled.loc[labelled.split_temporal == "calib", "year"].max()),
            "test_min_year": int(labelled.loc[labelled.split_temporal == "test", "year"].min())},
    }
    leak_ok = (leak["drugcold_by_scaffold"]["train_test_overlap"] == 0
               and leak["drugcold_by_scaffold"]["calib_test_overlap"] == 0
               and leak["targetcold_by_accession"]["train_test_overlap"] == 0
               and leak["targetcold_by_accession"]["calib_test_overlap"] == 0
               and leak["temporal_calib_vs_test_by_year"]["calib_max_year"] < TEMPORAL_CUTOFF)

    # --- save ---
    cols = ["pik", "accession", "family_l1", "label", "median_p", "n_exact", "iqr",
            "has_cens", "has_comment", "has_qhts", "scaffold", "scaffold_group", "year",
            "split_random", "split_drugcold", "split_targetcold", "split_temporal", "provenance"]
    out = labelled[cols].copy()
    out["high_disagreement"] = out.iqr >= 1.0
    out.to_parquet(OUT, index=False)

    manifest = {
        "rows": len(out), "dropped_below_min_protein_pairs": int(before - len(out)),
        "label_counts": out.label.value_counts().to_dict(),
        "distinct_compounds": int(out.pik.nunique()), "distinct_proteins": int(out.accession.nunique()),
        "distinct_scaffold_groups": int(out.scaffold_group.nunique()),
        "high_disagreement_pairs": int(out.high_disagreement.sum()),
        "params": {"active_cut": ACT_CUT, "inactive_cut": INACT_CUT, "min_pairs_per_protein": MIN_PAIRS_PER_PROTEIN,
                   "temporal_cutoff": TEMPORAL_CUTOFF, "seed": SEED, "test_frac": TEST_FRAC, "calib_frac": CALIB_FRAC},
        "split_distributions": {c: {str(k): int(v) for k, v in out[c].value_counts(dropna=False).items()}
                                for c in ["split_random", "split_drugcold", "split_targetcold", "split_temporal"]},
        "leakage_check": leak, "leakage_check_passed": bool(leak_ok),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, default=str))
    print(json.dumps(manifest, indent=2, default=str))
    if not leak_ok:
        raise SystemExit("LEAKAGE CHECK FAILED — see manifest")


if __name__ == "__main__":
    main()
