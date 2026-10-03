# STATUS: where we are right now

*Last updated: 2026-10-03. Rewrite this file at the end of every session. It must always describe the present, not the history (history goes in `PROJECT_LOG.md`).*

## One-line state
Project Week 1 (data profiling) is **finished and waiting for the owner's review**. Stage 1 of the pipeline (Data) is built and verified; Stage 2 (Network 1) is explained but **not coded**. The owner is currently learning the pipeline one stage at a time, with Stage 3 (Embeddings) explained next.

## Calendar check
- Project Week 1 started 2026-09-21. Today (2026-10-03) falls in calendar project Week 2 (28 Sep – 4 Oct).
- Week 1 work was completed in one long session on 2026-09-27. **Project Week 2 work (locking scope) has not started**, because the owner chose to learn first. This is a small slip against the plan. The two buffer weeks absorb it, but the owner should decide whether to adjust dates.
- Do not confuse **course report weeks** with **project weeks**. Course Week 2 and Week 3 reports (`docs/weekly_reports/`) both describe project Week 1.

## Done
- Scope decided (all human single-protein targets, per-family reporting), schedule fixed, compute plan fixed: `DECISIONS.md` D-001 to D-005.
- ChEMBL 37 and BindingDB 202609 downloaded and checksum-verified; ChEMBL extracted (30.5 GB): `data/MANIFEST.md`.
- Extraction, profiling, overlap and source-confounding scripts in `src/ingest/`; results in `reports/stage0/`; report in `docs/stage0_report.md`.
- 10 tests (9 fast, 1 slow). A from-scratch re-run reproduced all 16 result files byte-for-byte.
- Weekly reports for course Weeks 2 and 3 prepared (`docs/weekly_reports/`).
- Teaching material: two interactive pages (`docs/interactive/`) and stage notes for Stages 1 and 2 (`docs/stages/`).
- This memory system (`AGENTS.md`, `STATUS.md`, `PROJECT_LOG.md`, `PROJECT_GUIDE.md`).

## Next actions (in order)
1. **Teaching:** explain Stage 3 (Embeddings) when the owner says "next". Save it as `docs/stages/stage03_embeddings.md`.
2. **Owner review of the Stage 0 report** (`docs/stage0_report.md`). Approve or reject the recommendation to build Network 1 from ChEMBL only (`DECISIONS.md` D-008).
3. **Teammate runs the pipeline on their own machine.** This is the one unchecked item on the Week 1 gate.
4. **Project Week 2:** settle the open decisions below and freeze them in `DECISIONS.md`.
5. **Project Week 3:** build Network 1 (Stage 2) from those decisions.

## Open decisions (Week 2 must settle these; do not guess them)
| # | Decision | Why it is open |
|---|---|---|
| 1 | Activity thresholds, and whether per family | PubChem screening data shifts median potency by more than 1 log unit in 5 families, so thresholds must control for data source |
| 2 | Which endpoints count (IC50/Ki/Kd/EC50 only, or also "Potency")? | "Potency" (2.69M rows) is mostly single-series screening data; kinetics and %-inhibition are not affinities |
| 3 | Precise measured-inactive rule | ~1.04M candidate inactive pairs; "inconclusive" (1.73M rows) stays UNTESTED |
| 4 | Minimum data per protein | 2,883 of 5,738 proteins have fewer than 10 partners; a protein-cold split needs enough usable proteins |
| 5 | Temporal-split cutoff | 40% of rows have no publication year (all PubChem, PKIS, DrugMatrix) |
| 6 | Merge stereoisomer/isotope variants into parent compounds? | 53,559 InChIKey skeletons are shared by more than one compound ID; leakage risk (`reports/stage0/stage2_probe_output.txt`) |
| 7 | BindingDB: ChEMBL-only for v1? | Recommended, not yet approved (D-008) |
| 8 | Confidence floor (8 vs 9), `potential_duplicate` rows, validity-flagged rows | Minor, but must be written down before aggregation |

## Gotchas
- **Python 3.12 only** in `.venv`. If the IDE picks another interpreter, point it at `.venv\Scripts\python.exe`.
- Scripts import `src.*`, so run them from the repo root with `python -m ...`. A script outside the repo needs `PYTHONPATH=.`.
- The full-database test takes about 1 hour. It is excluded by default.
- Do not edit or commit anything under `data/raw/` or `data/interim/`.
- Git line endings are normalised to LF (`.gitattributes`), so Windows may show harmless CRLF warnings.

## Key numbers (ChEMBL 37, human single-protein)
8,299,186 activity rows · 5,738 proteins · 1,559,417 compounds · 5,064,882 drug–protein pairs · 810,994 censored rows (all without pChEMBL) · 28% of pairs have more than one record · 40% of rows lack a year. Source: `reports/stage0/`.

## Where things are
Start with `README.md`. Full project detail: `docs/PROJECT_GUIDE.md`. History: `docs/PROJECT_LOG.md`. Decisions: `DECISIONS.md`. Stage-by-stage teaching notes: `docs/stages/`.
