# DECISIONS.md

Every methodological or structural choice, dated, with the reason and the evidence behind it.
This file becomes the methods section. Newest entries at the bottom. Never rewrite an old entry —
if a decision is reversed, add a new entry that supersedes it and say which one.

Format: `## D-NNN · YYYY-MM-DD · short title` → Decision / Why / Evidence / Status.

---

## D-001 · 2026-09-27 · DTI universe scope: all human single-protein targets (universal), not kinome-only

**Decision.** The compound–protein universe is all ChEMBL targets with `target_type = 'SINGLE PROTEIN'`
and `organism = 'Homo sapiens'`, with every result reported stratified by target family. This supersedes
the Project Bible's framing (human kinome only, oncology case study, GNN as core drug encoder).
ChemBERTa remains the primary drug encoder; the molecular GNN is an optional ablation (Briefing Part 4).

**Why.** Deliberate team decision, explicitly confirmed by the project owner on 2026-09-27 (asked twice,
once with the trade-offs spelled out). It also matches the Submission document, the Master Plan and the
Claude Code Briefing, which all describe a large all-protein network stratified by family.

**Trade-offs knowingly accepted.**
- *Given up:* the kinome's data density, structural homology across the universe, a cleaner target-cold
  evaluation (proteins in one family are more comparable), and oncology-rich literature for sealed cases.
- *Taken on:* ~3–5k proteins to embed with ESM-2 (vs ~500), more compounds, and sparse/noisy families
  that will need an explicit minimum-data rule in Week 2.
- *Mitigation:* family-stratified evaluation (Week 6) and family-conditioned calibration (Week 7) are
  already planned; sparse-family handling is an open Week 2 question (see `docs/stage0_report.md`).

**Status.** LOCKED as intent. Week 2's inclusion rules (min interactions per protein, confidence floor,
endpoints) still decide *which* proteins survive inside this universe; that is not a change of scope.

## D-002 · 2026-09-27 · Authoritative schedule: Briefing / Master Plan (10 build + 2 buffer weeks)

**Decision.** `CLAUDE_CODE_BRIEFING.md` Part 5 and the Master Plan are the schedule of record.
The *12-Week Working Protocol* week mapping (router W10, experiment W11, write-up W12, no buffer) is superseded.
Week 1 started 2026-09-21.

**Why.** Protects Weeks 11–12 as a real buffer; the briefing was written specifically as the operating plan.

## D-003 · 2026-09-27 · Compute and LLM hosting

**Decision.** No local GPU (laptop: Intel i5-1145G7, 4 cores, 16 GB RAM, CPU-only torch). Heavy one-off jobs
(ESM-2 / ChemBERTa batch embedding, Week 4) run on Colab/Kaggle GPU or university HPC. The Week 9 LLM will be a
free, pinned open-weight instruction model hosted on Colab/HPC — exact model deferred to Week 9 and recorded then.
No paid LLM API.

**Why.** A local 7–8B model on this CPU runs at a few tokens/s — too slow for a fixed-vs-adaptive ablation
with many candidates. A pinned open-weight checkpoint is also more reproducible than a hosted API whose model changes.

## D-004 · 2026-09-27 · Working copy moved out of OneDrive

**Decision.** Working repo is `C:\Users\91701\code\Trust_DTI` (fresh clone). The OneDrive clone at
`Documents\Trust_DTI` is left untouched as a backup and is no longer worked in.

**Why.** The unpacked ChEMBL SQLite is ~25–30 GB; a synced folder risks partial-sync corruption of multi-GB files.
The OneDrive copy's unpushed commit `c3fa1f0` (a Jupyter-only `pip freeze` as `requirements.txt`) was deliberately
not carried over — it is superseded by a curated `requirements.in` + pinned `requirements.txt`.

## D-005 · 2026-09-27 · Source data releases

**Decision.** ChEMBL **37** (SQLite dump, prepared 2026-05-01 per release notes) and BindingDB **202609**
(`BindingDB_All_202609_tsv.zip`). Files, URLs, sizes and checksums are recorded in `data/MANIFEST.md`.
Versions are pinned as constants in `src/config.py`.

**Why.** Latest releases available on 2026-09-27. EBI publishes SHA-256 (not MD5) checksums; BindingDB publishes MD5.
Each file is verified against its publisher's own checksum.

## D-006 · 2026-09-27 · Target-family assignment method (Week 1 profiling)

**Decision.** Family = ChEMBL `protein_classification` walked from each component's class links up to level 1
(15 classes, e.g. Enzyme, Membrane receptor) and level 2 (e.g. Kinase, Family A GPCR). If a component's links
disagree at a level it is labelled `Multiple` (42 components at L1), never an arbitrary pick. A component with
an L1 but no L2 node gets `"<L1> (no L2)"`. Code: `src/ingest/families.py`, unit-tested.

**Why.** Deterministic and auditable. Stratified reporting (Weeks 6–7) needs one family per protein without hiding ambiguity.

## D-007 · 2026-09-27 · Censored relation operators

**Decision.** Censored = `standard_relation ∈ {>, <, >=, <=, >>, <<}`. `~` (approximate) and NULL are not censored.
No pipeline step filters on `pchembl_value IS NOT NULL`. Enforced by `tests/test_chembl_extract_data.py`.

**Evidence.** ChEMBL 37 human single-protein data has 810,994 censored rows, **all** with null pChEMBL.
`>>` (69 rows) and `<<` (1) exist and were initially missed. For imatinib the pChEMBL filter keeps 833 of 4,878 rows.

## D-008 · 2026-09-27 · Overlap methodology for ChEMBL ↔ BindingDB

**Decision.** Overlap is keyed on (InChIKey, UniProt accession), never SMILES, and reported three ways. The
decision-relevant figure is *independent vs independent*: ChEMBL minus src_id 37 (BindingDB patents) versus
BindingDB minus rows curated from ChEMBL.

**Evidence.** Naive shared pairs 872,761 vs independent 66,145 (≈13× inflation). 52% of BindingDB human
single-chain rows are ChEMBL-sourced.

**Status of the integration question itself:** *recommendation only* (ChEMBL-only for Network 1 v1; revisit
BindingDB's ~353k recent patent pairs for the temporal split). Pending owner review at the W1 gate; not locked.

## D-009 · 2026-09-27 · Working rule: "inconclusive" is not "inactive"

**Decision.** In all Week 1 estimates, `activity_comment` values "inconclusive" (1.73M rows), "not determined",
"nd" and "na" are **not** counted as measured-inactive. The final three-state label rules are a Week 2 decision; this
entry only prevents the most damaging conflation (Briefing §3.3) from creeping in beforehand.

## D-010 · 2026-09-27 · Slow full-database test excluded by default

**Decision.** `pytest` runs fast unit and data tests by default (~2 s). The full 24.5M-row count check is marked
`slow` (~1 h on the laptop) and runs with `pytest -m slow` before any data-release bump.

## D-011 · 2026-10-03 · Endpoints used for labelling (Week 2)

**Decision.** The ACTIVE/INACTIVE call is made only from **affinity dose-response** endpoints: IC50, Ki, Kd, EC50
(2.77M rows). qHTS endpoints (Potency, AC50; 2.90M rows) are used **only as inactive evidence** (a compound
screened at ≥10 µM with no activity), never to call ACTIVE. Kinetics (kon/koff, 1.37M) and single-point
%-inhibition (1.02M) are excluded from labelling.

**Why.** Dose-response affinities are the comparable, interpretable potencies. Restricting to them nearly
eliminates the PubChem confounding found in Week 1: median pChEMBL for dose-response exact values is 6.85 and
only moves to 6.91 when PubChem is excluded (vs. >1 log-unit shifts across all endpoints). qHTS "hits" are too
noisy to call active but a high-concentration no-activity screen is legitimate negative evidence. Kinetics and
%-inhibition are not affinities. Evidence: `reports/week2/A_endpoint_buckets.csv`, `week2_scope_summary.json`.

## D-012 · 2026-10-03 · Activity thresholds (Week 2)

**Decision.** From a pair's affinity dose-response measurements (exact `=`, nM), take the median pChEMBL.
- **ACTIVE** if median pChEMBL **≥ 6.5** (≈300 nM or stronger).
- **INACTIVE** if median pChEMBL **≤ 5.0** (≈10 µM or weaker), OR the pair has no exact value but has a censored
  `>`/`>=`/`>>` affinity ≥10 µM, or a "not active"-type comment, or a qHTS ≥10 µM no-activity screen.
- **GRAY** (median strictly between 5.0 and 6.5) is **excluded from training labels** but recorded with a flag.
- **UNTESTED** = everything else (not materialised).

**Why.** A 1.5-log gray buffer gives cleaner labels than a single cut, which matters for the Week 7 calibration
honesty, and we are not data-starved: this yields 754,401 ACTIVE and 1,163,256 INACTIVE pairs (1.92M labelled).
Sensitivity: a ≥6.0 cut would give 937,896 ACTIVE with a smaller gray zone; recorded as the alternative.
Evidence: `reports/week2/C_threshold_grid.csv`.

## D-013 · 2026-10-03 · Negatives are abundant; PU fallback not needed

**Decision.** The positive-unlabelled fallback (Briefing Week 2 risk) is **not** invoked. We have 1,163,256
measured-inactive pairs: 762k from "not active" comments, 273k censored-only, 141k exact-weak, 80k qHTS-only.
"inconclusive"/"not determined"/"nd"/"na" remain UNTESTED (D-009 stands). Evidence: `week2_scope_summary.json`.

## D-014 · 2026-10-03 · Compound identity and stereo/isotope variants

**Decision.** A compound is identified by its **salt-stripped parent InChIKey** (largest organic fragment,
neutralised; RDKit). Stereoisomers and isotope variants (e.g. imatinib vs deuterated imatinib) are **not merged**
— the InChIKey distinguishes them. Structural-analog leakage is prevented instead by the drug-cold split grouping
on the **Bemis–Murcko scaffold**, which such variants share, so they cannot land on opposite sides.

**Why.** Merging would conflate molecules that can have genuinely different activity. Scaffold grouping is the
correct, standard mechanism for leakage control. Supersedes open decision 6 in `STATUS.md`.

## D-015 · 2026-10-03 · Minimum data per protein

**Decision.** The modelling universe keeps proteins with **≥10 labelled (ACTIVE or INACTIVE) pairs**: 2,313
proteins (2,008 with both classes), 1,912,923 labelled pairs. Sparser proteins are dropped.

**Why.** Near-free (loses ~2k pairs of 1.91M) while removing proteins too sparse to evaluate or to support a
target-cold split. Evidence: `reports/week2/E_min_data_per_protein.csv`.

## D-016 · 2026-10-03 · Temporal split cutoff

**Decision.** Temporal split = train on pairs dated **before 2020**, test on **2020 onward** (by the minimum
doc_year of a pair's records): 860,525 train / 396,203 test (31.5% test). Pairs with no year (660,929) are
excluded from the temporal split only; they remain in the other three splits.

**Why.** A clean decade boundary leaving a healthy recent test set. Evidence: `reports/week2/F_temporal_cutoff.csv`.

## D-017 · 2026-10-03 · BindingDB: ChEMBL-only for Network 1 v1 (confirms D-008)

**Decision.** Network 1 v1 is built from **ChEMBL only**. BindingDB's independent patent pairs (~its newer
records) are reconsidered for the temporal test in a later iteration, not now. This confirms the recommendation
left pending in D-008.

## D-018 · 2026-10-03 · Measurement hygiene for aggregation

**Decision.** Keep confidence_score ≥ 8 (all in-scope rows are 8 or 9). When aggregating repeated measurements
per pair, use the **median** pChEMBL and retain the spread (IQR) and count; flag pairs whose IQR ≥ 1 log unit.
Drop rows flagged `data_validity_comment` = "Potential transcription error" or "Potential author error" from the
exact-value aggregation. Repeated-measurement disagreement is real: of pairs with >1 exact value, 23.1% differ
by ≥1 log unit (`reports/stage0/stage2_probe_output.txt`).

## D-019 · 2026-10-03 · Four splits + calibration carve-out

**Decision.** Build four splits with fixed seed 42: **random** (stratified by label), **drug-cold** (hold out
whole Murcko scaffolds), **target-cold** (hold out whole proteins — the primary generalisation test),
**temporal** (D-016). For each split a **calibration slice** is carved from its training partition only, provably
disjoint from that split's test set (needed by Week 7 conformal prediction). A leakage check must pass for all four.
