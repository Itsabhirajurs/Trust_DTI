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
