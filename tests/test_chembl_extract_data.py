"""Data-level regression tests on the real ChEMBL extract (skipped if the data is not on disk).

Guards the Briefing §3.4 trap: no extraction step may drop censored rows or
filter on pchembl_value being non-null.
"""
import sqlite3

import pandas as pd
import pytest

from src import config
from src.ingest.chembl_extract import OUT_ACT
from src.ingest.relations import CENSORED_RELATIONS

needs_data = pytest.mark.skipif(not (OUT_ACT.exists() and config.CHEMBL_DB.exists()),
                                reason="ChEMBL DB / extract not on disk")

CENSORED = tuple(f"'{r}'" for r in sorted(CENSORED_RELATIONS))


@needs_data
def test_imatinib_censored_rows_survive_extraction():
    con = sqlite3.connect(f"file:{config.CHEMBL_DB}?mode=ro", uri=True)
    expected = con.execute(f"""
        SELECT COUNT(*) FROM activities a
        JOIN assays s ON s.assay_id = a.assay_id
        JOIN target_dictionary t ON t.tid = s.tid
        JOIN molecule_dictionary m ON m.molregno = a.molregno
        WHERE m.chembl_id = 'CHEMBL941' AND t.target_type = ? AND t.organism = ?
          AND a.standard_relation IN ({",".join(CENSORED)})""",
        (config.TARGET_TYPE, config.ORGANISM)).fetchone()[0]
    df = pd.read_parquet(OUT_ACT, columns=["molecule_chembl_id", "standard_relation"],
                         filters=[("molecule_chembl_id", "==", "CHEMBL941")])
    got = df.standard_relation.isin(CENSORED_RELATIONS).sum()
    assert expected > 0
    assert got == expected


@needs_data
def test_extract_does_not_filter_on_pchembl():
    df = pd.read_parquet(OUT_ACT, columns=["pchembl_value", "standard_relation"])
    assert df.pchembl_value.isna().sum() > 0
    cens = df.standard_relation.isin(CENSORED_RELATIONS)
    assert cens.sum() > 0
    # every censored row is pchembl-null in ChEMBL; if this ever fails, the source semantics changed
    assert df.loc[cens, "pchembl_value"].isna().all()


@pytest.mark.slow  # full scan of 24.5M activities (~1 h on a laptop); run with `pytest -m slow`
@needs_data
def test_activity_row_count_matches_sql():
    con = sqlite3.connect(f"file:{config.CHEMBL_DB}?mode=ro", uri=True)
    expected = con.execute("""
        SELECT COUNT(*) FROM activities a JOIN assays s ON s.assay_id = a.assay_id
        JOIN target_dictionary t ON t.tid = s.tid
        WHERE t.target_type = ? AND t.organism = ?""", (config.TARGET_TYPE, config.ORGANISM)).fetchone()[0]
    import pyarrow.parquet as pq
    assert pq.ParquetFile(OUT_ACT).metadata.num_rows == expected
