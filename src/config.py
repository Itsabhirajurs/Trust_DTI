"""Project-wide paths and pinned source-data versions.

Every script imports paths from here so a data release bump is a one-line change
that shows up in git history.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"
STAGE0 = REPORTS / "stage0"

# --- pinned source releases (see data/MANIFEST.md) ---
CHEMBL_VERSION = "37"
CHEMBL_DB = RAW / f"chembl_{CHEMBL_VERSION}" / f"chembl_{CHEMBL_VERSION}_sqlite" / f"chembl_{CHEMBL_VERSION}.db"

BINDINGDB_RELEASE = "202609"
BINDINGDB_ZIP = RAW / f"BindingDB_All_{BINDINGDB_RELEASE}_tsv.zip"

# --- Week 1 restriction criteria (Briefing §3.2) — not a Week 2 scope decision ---
TARGET_TYPE = "SINGLE PROTEIN"
ORGANISM = "Homo sapiens"
