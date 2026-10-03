# Stage 1: Data (status: done and verified)

## Why this stage exists
Everything downstream (network, embeddings, model, calibration, evidence search) depends on what comes out of here. Bad data in means confident, wrong predictions out, and nothing later can repair it. Stage 1 therefore has four jobs:
1. **Acquire** real measurements of drug–protein interactions.
2. **Prove** they were not corrupted on the way in.
3. **Restrict** them to the project's universe (human, single-protein targets) and nothing more.
4. **Understand** their shape *before* writing any threshold or label rule, so those rules rest on evidence.

Week 1's gate: raw extracts on disk with dated versions recorded; both team members can run the same profiling and get the same answer; a first table of protein counts by family.

## Why ChEMBL (and what lost)
| Option | Why not primary |
|---|---|
| DrugBank | Smaller; bulk data is behind a commercial licence, a poor fit for a reproducible project |
| PubChem alone | Huge but mostly single-concentration screening data with weaker metadata. We later saw PubChem data inside ChEMBL distort potency |
| BindingDB alone | Good curation but smaller (3.2M vs 24.5M) and it largely overlaps ChEMBL |
| **ChEMBL** | Largest open, curated source, run by EMBL-EBI. Records the relation operator, units, assay confidence and original source of every value, which our correctness rules need |

**BindingDB** was a cross-check, not a second primary source. The open question was "does merging it enlarge the network?". The honest answer (below) was "not much for now".

**Why the SQLite dump:** one file, no database server, queries run locally and instantly. It let us run the same query two ways (web client and direct SQL) and prove they agree. The cost is a 5.8 GB download (30 GB unpacked).

## Why the restriction is only `SINGLE PROTEIN` + `Homo sapiens`
Those two filters *define* the project's universe: a prediction "this drug binds this protein" is only unambiguous with exactly one human protein in question. Everything else (potency thresholds, assay types, what "inactive" means) is a **Week 2 decision made from the real distribution**. Filtering earlier would silently shape the data before anyone could decide. This is also why no step may filter on `pchembl_value IS NOT NULL`: it would delete 68.7% of the scoped rows, every censored measurement among them.

## What we did, in order
1. **Found the ground unstable.** A "download" of 265 MB out of 5.76 GB was corrupt (`gzip: unexpected end of file`). The repo sat inside OneDrive, which can corrupt a large file mid-sync. We moved the repo out first.
2. **Resumed** the download from the exact byte offset (`curl -C -`) instead of restarting.
3. **Verified before trusting.** Right size proves nothing. SHA-256 matched EBI's `checksums.txt` exactly (`33c20374…290d281`). BindingDB's MD5 matched too.
4. **Checked the contents**, not just the file: `COUNT(*) FROM activities` = 24,527,044, identical to the release notes.
5. **Learned the schema by hand** before writing SQL: activities → assays → target_dictionary → target_components → component_sequences → component_class → protein_classification. A wrong join here would corrupt every number silently. (`docs/chembl_schema_notes.md`)
6. **Extracted** 8,299,186 rows, one million at a time, straight into Parquet (16 GB of RAM cannot hold everything). An explicit schema keeps column types consistent across chunks.
7. **Profiled before judging.** Counts, family breakdown, skew, missingness, sources, assay quality.
8. **Answered the BindingDB question honestly.** 872,761 shared pairs looks like a case to merge, but 52% of BindingDB's human rows are copied from ChEMBL and ChEMBL imports 2.2M BindingDB patent rows. On independent records only, the overlap is 66,145 (~13× smaller). Recommendation: ChEMBL only for Network 1 v1 (not yet approved).
9. **Wrote tests** so mistakes cannot return silently (censored rows survive extraction; no pChEMBL filter).
10. **Logged every decision** as it was made (`DECISIONS.md`).

## Result
| | |
|---|---|
| Activity rows in scope | 8,299,186 (of 24,527,044) |
| Human proteins | 5,738 |
| Compounds | 1,559,417 (2,685 approved drugs) |
| Drug–protein pairs | 5,064,882 |
| Censored measurements (kept) | 810,994 |
| Rows with no publication year | 39.8% |

## Handed to Week 2 (deliberately undecided)
Activity thresholds (and whether per family, controlling for data source); which endpoints count; the measured-inactive rule; minimum data per protein; the temporal cutoff.

## Code
`src/config.py` · `src/ingest/chembl_extract.py` · `bindingdb_extract.py` · `profile_chembl.py` · `profile_overlap.py` · `profile_source_confounding.py` · `families.py` · `relations.py` · `tests/`. Results: `reports/stage0/`, `docs/stage0_report.md`.

## Be able to explain
- Why a file's size is not proof it is intact.
- Why `pchembl_value IS NOT NULL` silently deletes the "inactive" evidence.
- Why a second database that "overlaps" may just be a copy.
- Why the data is profiled before any threshold is chosen.
