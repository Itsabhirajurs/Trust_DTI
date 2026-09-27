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
