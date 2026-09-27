# Data manifest

Raw source files live in `data/raw/` (gitignored — multi-GB and not ours to redistribute).
This file is the committed record of exactly which files every result in the repo was built from.
Never overwrite a raw file in place; a new release gets a new filename and a new row here.

## Raw sources

| File | Release | Source URL | Downloaded | Size (bytes) | Checksum (publisher's) | Verified |
|---|---|---|---|---|---|---|
| `chembl_37_sqlite.tar.gz` | ChEMBL 37 (prepared 2026-05-01) | https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_37_sqlite.tar.gz | 2026-09-27 | 5,764,252,857 | SHA-256 `33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281` (EBI `checksums.txt`) | ✅ match |
| `BindingDB_All_202609_tsv.zip` | BindingDB 202609 | https://www.bindingdb.org/rwd/bind/downloads/BindingDB_All_202609_tsv.zip | 2026-09-27 | 593,578,299 | MD5 `19db177dc630e556bd1449db408767ca` (`BindingDB_All_202609_tsv.md5`) | ✅ match |

### Notes
- ChEMBL extracted to `raw/chembl_37/chembl_37_sqlite/chembl_37.db` (30,480,314,368 bytes). Sanity: `version` row
  `ChEMBL_37` dated 2026-05-01; `COUNT(*) FROM activities` = 24,527,044 = release notes.
- ChEMBL: download was resumed (`curl -C -`) from a 264,921,088-byte partial file left by an earlier interrupted
  attempt (2026-09-22). Integrity is established solely by the SHA-256 match, not by file size.
- BindingDB: the zip contains one member, `BindingDB_All.tsv` (8,984,698,089 bytes; 3,237,052 data lines, 640 columns).
  It includes 5 blank lines and 1 NUL-byte line (upstream artefacts; carry no records).

## Derived (interim, gitignored — regenerate with the listed command)

| File | Built by | Rows |
|---|---|---|
| `interim/bindingdb_202609_human_single_chain.parquet` | `python -m src.ingest.bindingdb_extract` | 2,343,392 |
| `interim/chembl37_human_sp_activities.parquet` | `python -m src.ingest.chembl_extract` | _pending_ |
| `interim/chembl37_human_sp_targets.parquet` | `python -m src.ingest.chembl_extract` | _pending_ |
