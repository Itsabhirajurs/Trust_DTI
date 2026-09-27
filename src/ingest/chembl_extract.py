"""Week 1 D2 — one-time extract of every activity on a human SINGLE PROTEIN target.

Restriction is only Briefing §3.2 (target_type + organism). Nothing else is filtered:
every standard_relation, standard_type, confidence score and source is kept, and
there is deliberately NO `pchembl_value IS NOT NULL` filter (Briefing §3.4 — that
filter silently drops every censored row; for imatinib it keeps 833 of 4,878 rows).

Outputs (data/interim/, gitignored):
  chembl37_human_sp_activities.parquet  one row per activity
  chembl37_human_sp_targets.parquet     one row per target: tid, accession, family
and reports/stage0/chembl_sources.csv, chembl_extract_stats.json (committed).

Run: python -m src.ingest.chembl_extract
"""
import json
import sqlite3

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src import config
from src.ingest.families import assign_families

V = config.CHEMBL_VERSION
OUT_ACT = config.INTERIM / f"chembl{V}_human_sp_activities.parquet"
OUT_TGT = config.INTERIM / f"chembl{V}_human_sp_targets.parquet"
STATS = config.STAGE0 / "chembl_extract_stats.json"

TARGET_SQL = """
SELECT td.tid, td.chembl_id AS target_chembl_id, td.pref_name AS target_name,
       tc.component_id, cs.accession, cs.organism AS component_organism
FROM target_dictionary td
JOIN target_components tc ON tc.tid = td.tid
JOIN component_sequences cs ON cs.component_id = tc.component_id
WHERE td.target_type = ? AND td.organism = ?
"""

ACTIVITY_SQL = """
SELECT act.activity_id, act.assay_id, act.doc_id, act.molregno,
       act.src_id            AS act_src_id,
       act.standard_type, act.standard_relation, act.standard_value, act.standard_units,
       act.standard_flag, act.pchembl_value,
       act.activity_comment, act.data_validity_comment, act.potential_duplicate,
       a.assay_type, a.confidence_score, a.src_id AS assay_src_id, a.tid,
       md.chembl_id          AS molecule_chembl_id, md.max_phase,
       cst.standard_inchi_key AS inchikey,
       d.year                AS doc_year
FROM activities act
JOIN assays a              ON a.assay_id = act.assay_id
JOIN target_dictionary td  ON td.tid = a.tid
JOIN molecule_dictionary md ON md.molregno = act.molregno
LEFT JOIN compound_structures cst ON cst.molregno = act.molregno
LEFT JOIN docs d           ON d.doc_id = act.doc_id
WHERE td.target_type = ? AND td.organism = ?
"""

SCHEMA = pa.schema([
    ("activity_id", pa.int64()), ("assay_id", pa.int64()), ("doc_id", pa.int64()), ("molregno", pa.int64()),
    ("act_src_id", pa.int64()),
    ("standard_type", pa.string()), ("standard_relation", pa.string()), ("standard_value", pa.float64()),
    ("standard_units", pa.string()), ("standard_flag", pa.int64()), ("pchembl_value", pa.float64()),
    ("activity_comment", pa.string()), ("data_validity_comment", pa.string()), ("potential_duplicate", pa.int64()),
    ("assay_type", pa.string()), ("confidence_score", pa.int64()), ("assay_src_id", pa.int64()), ("tid", pa.int64()),
    ("molecule_chembl_id", pa.string()), ("max_phase", pa.float64()), ("inchikey", pa.string()), ("doc_year", pa.int64()),
])


def main(chunksize: int = 1_000_000) -> None:
    con = sqlite3.connect(f"file:{config.CHEMBL_DB}?mode=ro", uri=True)
    params = (config.TARGET_TYPE, config.ORGANISM)
    stats = {"chembl_version": con.execute(
        "SELECT name FROM version WHERE comments LIKE 'ChEMBL Release%'").fetchone()[0]}

    # --- targets + families ---
    tgt = pd.read_sql_query(TARGET_SQL, con, params=params)
    stats["targets"] = int(tgt.tid.nunique())
    stats["targets_with_multiple_components"] = int((tgt.groupby("tid").size() > 1).sum())
    cc = pd.read_sql_query("SELECT component_id, protein_class_id FROM component_class", con)
    pc = pd.read_sql_query("SELECT protein_class_id, parent_id, pref_name, class_level FROM protein_classification", con)
    fam = assign_families(cc[cc.component_id.isin(tgt.component_id)], pc)
    tgt = tgt.merge(fam, on="component_id", how="left")
    tgt["family_l1"] = tgt["family_l1"].fillna("Unclassified")
    tgt["family_l2"] = tgt["family_l2"].fillna("Unclassified")
    stats["components_with_conflicting_l1"] = int((tgt.family_l1 == "Multiple").sum())
    tgt.to_parquet(OUT_TGT, index=False)

    pd.read_sql_query("SELECT src_id, src_short_name, src_description FROM source ORDER BY src_id", con) \
      .to_csv(config.STAGE0 / "chembl_sources.csv", index=False)

    # --- activities, streamed to parquet ---
    n = 0
    writer = pq.ParquetWriter(OUT_ACT, SCHEMA)
    for chunk in pd.read_sql_query(ACTIVITY_SQL, con, params=params, chunksize=chunksize):
        for col in SCHEMA.names:
            if SCHEMA.field(col).type == pa.int64():
                chunk[col] = chunk[col].astype("Int64")
        writer.write_table(pa.Table.from_pandas(chunk[SCHEMA.names], schema=SCHEMA, preserve_index=False))
        n += len(chunk)
        print(f"  {n:>11,} activity rows written", flush=True)
    writer.close()
    stats["activity_rows"] = n
    stats["activities_table_total_rows"] = con.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    con.close()

    config.STAGE0.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
