# Week 3 references

## Data files (verified)
| File | Checksum (publisher's) | Result |
|---|---|---|
| `chembl_37_sqlite.tar.gz` (5,764,252,857 bytes) | SHA-256 `33c20374…290d281` from EBI `checksums.txt` | match |
| `BindingDB_All_202609_tsv.zip` (593,578,299 bytes) | MD5 `19db177d…767ca` from BindingDB `.md5` | match |

Full record: `data/MANIFEST.md`.

## Code (all in the GitHub repo)
| What | Where |
|---|---|
| Paths and pinned data versions | `src/config.py` |
| ChEMBL extraction | `src/ingest/chembl_extract.py` |
| BindingDB streaming extraction | `src/ingest/bindingdb_extract.py` |
| Censored-value parsing | `src/ingest/relations.py` |
| Protein-family assignment | `src/ingest/families.py` |
| Profiling (counts, quality, plots) | `src/ingest/profile_chembl.py` |
| ChEMBL vs BindingDB overlap | `src/ingest/profile_overlap.py` |
| PubChem effect on potency | `src/ingest/profile_source_confounding.py` |
| Tests | `tests/` (run `pytest`; full-database check: `pytest -m slow`) |
| Results (small, committed) | `reports/stage0/` |
| Stage 0 report | `docs/stage0_report.md` |

Repository: https://github.com/Itsabhirajurs/Trust_DTI

## Tools and documentation
- ChEMBL schema documentation: https://chembl.gitbook.io/chembl-interface-documentation/ (table and field meanings)
- EBI ChEMBL downloads and checksums: https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/
- pandas: https://pandas.pydata.org/docs/ · Apache Arrow / Parquet: https://arrow.apache.org/docs/python/
- SQLite: https://www.sqlite.org/docs.html · pytest: https://docs.pytest.org/
- ChEMBL web client: https://github.com/chembl/chembl_webresource_client

## Literature
- Zdrazil B. et al. *The ChEMBL Database in 2023.* Nucleic Acids Research 52(D1), 2024. (Data sources inside ChEMBL, including deposited PubChem and BindingDB data.)
- Bento A.P. et al. *The ChEMBL bioactivity database: an update.* Nucleic Acids Research 42(D1), 2014. (pChEMBL definition: −log10 of molar potency, exact values only.)
- Liu T. et al. *BindingDB in 2024.* Nucleic Acids Research 53(D1), 2025. (BindingDB curation sources, including ChEMBL.)
- Kim S. et al. *PubChem 2025 update.* Nucleic Acids Research 53(D1), 2025. (Background on the screening data behind the "Potency" endpoint.)
