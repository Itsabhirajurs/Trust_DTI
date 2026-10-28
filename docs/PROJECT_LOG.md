## 2026-10-28 · Week 8 sprint kickoff and classical DTI baseline scaffolding
**Where:** GitHub repository + GitHub Actions · **Stage / project week:** Stage 3/4 bridge; Week 8 core-pipeline sprint
**Done:**
- Read the project instructions, current status, recent log, guide, and decision policy before changing code. The sealed-case rule remains untouched.
- Added `docs/plans/week08_core_pipeline_sprint.md` with ordered work packages and measurable acceptance gates for the requested high-intensity sprint.
- Added `src/model/evaluate_dti_baseline.py`: resource-capped logistic regression over RDKit Morgan fingerprints plus `family_l1` one-hot features, using existing random, drug-cold, target-cold, or temporal split assignments; reports standard classification metrics, Brier/ECE diagnostics, and split-conformal-style set statistics.
- Added unit tests for deterministic stratified sampling, fingerprint output, split integrity guards, ECE, and prediction-set calculation. Added scikit-learn/scipy/joblib/threadpoolctl pins and a minimal cross-platform CI dependency file.
- Added the baseline explanation note and GitHub Actions test workflow.
**Found:** first CI attempt failed before tests because the full Windows-frozen dependency list tried compiling `pywinpty` on Linux. CI was changed to install `requirements-ci.txt`; run `40689615417` passed **17 tests**, with 2 data-dependent tests skipped and 1 slow test deselected.
**Changed vs plan:** the implementation is a conventional reference baseline, not the final ChemBERTa/ESM-2 fusion head. The runner has not yet been run against the user's local Network 1 data, so no predictive metrics are claimed.
**Decisions:** D-021 records the classical baseline as a provisional reference only.
**Commits:** baseline runner `ce8d2ed`; baseline tests `504e254`; passing CI setup `d7e0db4`; sprint plan `b20f182`. Additional dependency/workflow updates followed.
**Open / next:** sync the latest main branch to the local workstation; commit the seven previously validated Week 7 artifact files; run the random baseline locally; then proceed through the other split evaluations before Network 2 and the router.
**For the owner to understand:** an embedding vector is not a binding prediction. The baseline is a reference measurement; its output scores and diagnostics still need to be generated from the actual dataset before they can support a scientific claim.

---

## 2026-10-25 · Stage 3 smoke test: sequence retrieval and embeddings
**Where:** Windows working copy + Google Colab + GitHub · **Stage / project week:** preliminary Stage 3 pilot / course report Week 7
**Done:**
- Audited 2,312 unique Network 1 protein accessions; all mapped to human target metadata and passed the preliminary UniProt-format check.
- Retrieved 2,312 UniProt human protein sequences. The local summary showed zero unmatched accessions, all sequences passing the implemented amino-acid check, and all reported/actual lengths matching.
- Tested pretrained embedding generation on Google Colab / NVIDIA Tesla T4: 100 compound SMILES with ChemBERTa-77M-MLM (100 × 384) and 20 protein sequences with ESM-2 8M UR50D (20 × 320). No pilot inputs were truncated; all embedding values were finite.
- Verified local output shapes, identifier alignment, sequence alignment, and safe NumPy loading. Local tests: 9 passed, 1 deselected.
- Added the Week 7 progress documentation, form entries, references, infographic, reproduction notebook, and sequence retrieval scripts.
**Found:** Model load/inference times in the recorded pilot were 10.88 s / 1.39 s for ChemBERTa and 2.66 s / 0.54 s for ESM-2. These are small-sample pilot measurements, not full-dataset throughput estimates.
**Changed vs plan:** the laptop GPU environment was not established; the small pilot therefore ran on Colab. The result does not complete full-scale embedding generation.
**Decisions:** D-020 records the encoders/pooling as a provisional smoke-test configuration only.
**Commits:** see the Week 7 repository update.
**Open / next:** sync local NPZ and sample CSV artifacts into the repository; rerun the notebook after a clean runtime; then design and evaluate a labelled DTI baseline.
**For the owner to understand:** an embedding is a numerical representation, not a binding prediction. Passing shape and finite-value checks proves that the encoding pipeline ran, not that the vectors improve DTI accuracy.

---

# PROJECT LOG (the diary)

Newest entry at the **top**. One entry per working session. Facts only: what was done, what was found, what changed versus the plan, what is open. Never rewrite an old entry; if something turns out wrong, correct it in a new entry and say which one.

The older running log in `CLAUDE_CODE_BRIEFING.md` Part 8 stays as history. New entries go here.

### Entry template (copy to the top)
```
## YYYY-MM-DD · short title
**Where:** which tool/IDE · **Stage / project week:** …
**Done:** …
**Found:** … (numbers must come from a file or a query; name it)
**Changed vs plan:** …
**Decisions:** D-NNN … (or "none")
**Commits:** `abc1234` message …
**Open / next:** …
**For the owner to understand:** one or two lines of the key idea learned today
```

---

## 2026-10-04 · Week 2 scope locked; Network 1 (Stage 2) built
**Where:** Claude Code (desktop) · **Stage / project week:** Stage 2 / project Weeks 2–3
**Done:**
- Locked the Week 2 scope from evidence: `src/ingest/analyze_scope_week2.py` over all 8.3M rows → `reports/week2/`. Decisions D-011–D-019 in `DECISIONS.md` (endpoints, thresholds, inactive rule, compound identity, min-data, temporal cutoff, BindingDB, hygiene, splits).
- Standardised 1,559,417 compounds with RDKit (`src/network/standardize_compounds.py`): 1 unparseable, 50,339 salts/mixtures stripped, 478,250 distinct scaffolds.
- Built Network 1 (`src/network/build_network1.py` → `data/processed/network1_v1.parquet`): 1,905,586 labelled pairs (748,430 ACTIVE / 1,157,156 INACTIVE), 2,312 proteins, 1,006,840 compounds, 333,583 scaffold groups. Four splits (random, drug-cold, target-cold, temporal 2020) each with a calibration slice.
- **Leakage check PASSED** (all train/test/calib overlaps 0; temporal calib ≤2019, test ≥2020). Manifest: `reports/week2/network1_v1_manifest.json`.
- Prepared course report 4 (`docs/weekly_reports/week04_network1/`): PDF, 6 figures, form entries, references.
**Found:**
- Restricting labels to dose-response affinities (2.77M rows) nearly removes the PubChem distortion (median pChEMBL 6.85 → 6.91 without PubChem), so no per-family threshold correction was needed.
- Abundant real negatives (1.16M measured-inactive pairs, 762k from "not active" comments) → PU fallback not needed (D-013).
- 18,078 pairs have repeated measurements disagreeing by ≥1 log unit (flagged, not averaged away).
**Changed vs plan:** none in substance. Chose Kaggle over Colab for the Stage 3 GPU batch (more generous free quota, persistent datasets).
**Roadblocks (engineering):** first Network 1 build was OS-killed (OOM) — fixed by dropping the free-text column early, category dtypes, and vectorised joins instead of Python sets (2.3 GB → 1.6 GB). Also fixed a read-only-array shuffle and a non-serialisable NA manifest key.
**Decisions:** D-011 to D-019.
**Commits:** see this session's commit.
**Open / next:** owner sign-off on D-011–D-019; Stage 3 embeddings on Kaggle; classical baselines.
**For the owner to understand:** Network 1 is one clean row per drug–protein pair with a label and a leakage-safe split assignment. The labelling rule and the splits are what make every later result trustworthy.

## 2026-10-03 · Memory system for AI assistants; Stage 2 groundwork
**Where:** Claude Code (desktop) · **Stage / project week:** teaching Stage 2; calendar project Week 2
**Done:**
- Built the "resume from anywhere" system because the owner's IDE (Antigravity) sometimes loses conversation history: `AGENTS.md` (loaded automatically by Antigravity from the project root), `docs/STATUS.md`, this log, `docs/PROJECT_GUIDE.md`, `docs/stages/` teaching notes, copies of the two interactive pages in `docs/interactive/`, and a `README.md`.
- Explained Stage 1 (Data) and Stage 2 (Network 1) in detail; saved as `docs/stages/stage01_data.md` and `stage02_network1.md`.
- Ran a read-only probe of the real data to find what Network 1 construction must handle. Script `src/ingest/probe_stage2_issues.py`, output `reports/stage0/stage2_probe_output.txt`.
**Found:** (full numbers in the probe output)
- 28.0% of the 5,064,882 pairs have more than one record (max 1,934).
- Of 1,347,583 pairs with an exact potency, 22.9% have repeats; among those, 23.1% disagree by at least 1 log unit and 8.2% by at least 2.
- 53,559 InChIKey skeletons are shared by more than one ChEMBL compound ID (example: imatinib and a deuterated imatinib). If both land on different sides of a split, that is leakage.
- In a fixed 40,000-compound sample, 3.2% of SMILES are multi-component (salts or mixtures) and none failed to parse in RDKit. Sample-based, not full-universe.
**Changed vs plan:** none. Added open decision 6 (merge isotope/stereo variants) to `STATUS.md`.
**Decisions:** none recorded yet. Decision 6 is pending Week 2.
**Open / next:** Stage 3 explanation; owner review of Stage 0; teammate runs the pipeline; Week 2 decisions.
**For the owner to understand:** Network 1 is just a clean table with one row per drug–protein pair. The hard part is deciding, before splitting, which records describe "the same thing".

## 2026-09-28 → 2026-10-02 · Learning sessions (approximate dates)
**Where:** Claude Code (desktop) · **Stage / project week:** between project Weeks 1 and 2
**Done:**
- The owner asked to understand the whole project before continuing. Explained, in chat: the idea and research question, the two networks, the offline/online architecture, the router, the evidence categories, the 12-week roadmap, the data acquisition story, the three-state label and censoring rules, and a file-by-file walkthrough of every script and test in `src/ingest/` and `tests/`.
- Built and published two private interactive pages (claude.ai artifacts): **TrustDTI Explained** (concept and architecture, light theme) and **TrustDTI Pipeline** (all 13 stages with real numbers, dark theme). Sources now saved in `docs/interactive/`.
- Fixed an error found while verifying the Pipeline page: the "all other families" bar was wrong (should be 9 classes, 297,110 pairs, 521 proteins).
**Found:** nothing new in the data. Process lesson: the editor's file tool stores text literally, so JavaScript apostrophes were double-escaped; caught with a syntax check before publishing.
**Changed vs plan:** project Week 2 has not started; the owner is learning first (see `STATUS.md`).
**Commits:** none in this period.
**Open / next:** continue stage by stage (Stage 1 and 2 done, Stage 3 next).
**For the owner to understand:** the project's contribution is what happens after the prediction (calibrated confidence steering the evidence search), not the predictor itself.

## 2026-09-27 · Week 1 completed to the gate; weekly reports prepared
**Where:** Claude Code (desktop) · **Stage / project week:** Stage 1 (Data) / project Week 1, Days 1–5
**Done:**
- Resolved contradictions between the owner's documents (scope: kinome-only vs all human proteins → all; schedule: Briefing/Master Plan over the Working Protocol). Decisions D-001 to D-005.
- Moved the working repo out of OneDrive to `C:\Users\91701\code\Trust_DTI`; wrote a curated, pinned environment.
- Resumed the corrupt 265 MB ChEMBL download to the full 5,764,252,857 bytes; SHA-256 matched EBI's `checksums.txt`. Row count 24,527,044 matched the release notes. BindingDB 202609 MD5 matched.
- Wrote and ran `chembl_extract.py`, `bindingdb_extract.py`, `profile_chembl.py`, `profile_overlap.py`, `profile_source_confounding.py`, `families.py`, `relations.py`; 10 tests.
- Closed Day 1: imatinib check reproduced in the web client and in SQL (4,878 rows; 833 with pChEMBL; 1,335 censored, all without pChEMBL; example activity 884645, IC50 > 30,000 nM vs FLT3).
- Wrote the Stage 0 report and prepared the course Week 2 and Week 3 reports.
**Found:** (all in `docs/stage0_report.md` and `reports/stage0/`)
- 8,299,186 rows, 5,738 proteins, 1,559,417 compounds, 5,064,882 pairs; the busiest 10% of proteins hold 88% of pairs.
- ChEMBL and BindingDB copy each other: naive overlap 872,761 pairs vs 66,145 on independent records (~13×).
- PubChem screening data shifts median pChEMBL by more than 1 log unit in 5 families.
- `>>` and `<<` operators exist (70 rows); 40% of rows lack a year; ~1.04M pairs look measured-inactive.
**Changed vs plan:** EBI publishes SHA-256, not MD5. Kinetic and %-inhibition endpoints need an explicit policy. A count in the report was corrected from 7 to 5 families.
**Decisions:** D-001 to D-010.
**Commits:** `2430958` setup + decision log · `c7b1483` BindingDB extract + relation parser · `6918de8` imatinib notebook close-out · `c6fd155` verified ChEMBL, schema notes, manifest · `215d7ed` extraction/profiling scripts + tests · `9df4a36` Stage 0 report + decision/running logs · `8ee1855` weekly reports · `16fe9b5` count correction.
**Open / next:** owner review; teammate run; Week 2 decisions.
**For the owner to understand:** profile the data before deciding any threshold, so decisions rest on evidence. Verify downloads with the publisher's checksum, never by file size.

## 2026-09-22 · First ChEMBL download attempt (reconstructed from the Briefing log)
**Where:** earlier setup, outside this log system · **Stage / project week:** Week 1 Day 1
**Done:** direct FTP/HTTPS download failed repeatedly with `ConnectionRefusedError`; a `chembl_downloader` attempt left a 265 MB partial file. The ChEMBL web client was confirmed working (imatinib CHEMBL941, ABL1 CHEMBL1862).
**Found:** `pchembl_value__isnull=False` silently drops censored rows (see 2026-09-27).
**Open / next:** finish the download (done 2026-09-27).

## 2026-09-21 · Project skeleton
**Where:** GitHub · **Stage / project week:** Week 1 start
**Done:** folder structure committed (`84c2b23`). A local-only commit `c3fa1f0` (a Jupyter-only `pip freeze`) was never pushed and was deliberately not carried over (D-004).
