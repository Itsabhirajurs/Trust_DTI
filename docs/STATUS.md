# STATUS: where we are right now

*Last updated: 2026-10-04. Rewrite this file at the end of every session. It must describe the present (history goes in `PROJECT_LOG.md`).*

## One-line state
**Stages 1 (Data) and 2 (Network 1) are built and verified.** Network 1 = 1,905,586 labelled drug–protein pairs (748,430 ACTIVE / 1,157,156 INACTIVE) over 2,312 proteins and 1,006,840 compounds, with four leakage-checked splits. Next is **Stage 3 (Embeddings)**, which needs a Kaggle GPU. The owner is learning the project one stage at a time (Stages 1–4 explained).

## Calendar
- Project Week 1 started 2026-09-21. Course reports submitted so far: 2, 3, and now 4.
- This session (2026-10-03/04) completed **project Week 2** (lock scope, D-011–D-019) and **project Week 3** (build Network 1). We are roughly on-plan now; the earlier learning time was absorbed.
- Course report 4 is prepared in `docs/weekly_reports/week04_network1/`.

## Done
- **Stage 1 (Data):** ChEMBL 37 + BindingDB verified, extracted, profiled; `docs/stage0_report.md`, `reports/stage0/`.
- **Week 2 scope lock:** `src/ingest/analyze_scope_week2.py` → `reports/week2/`; decisions D-011–D-019.
- **Stage 2 (Network 1):** `src/network/standardize_compounds.py` (1.56M compounds, RDKit) + `build_network1.py`
  → `data/processed/network1_v1.parquet`, manifest `reports/week2/network1_v1_manifest.json`. Leakage check PASSED.
- Teaching: Stages 1–4 explained; notes in `docs/stages/` (Stages 1–2 written). Two interactive pages in `docs/interactive/`.
- Memory system: `AGENTS.md`, this file, `PROJECT_LOG.md`, `PROJECT_GUIDE.md`.
- Course reports for Weeks 2, 3, 4 in `docs/weekly_reports/`.

## Next actions (in order)
1. **Teaching:** explain Stage 3 details when asked (ChemBERTa/ESM-2 mechanics); save `docs/stages/stage03_embeddings.md`.
2. **Stage 3 build (project Week 4):** write the Kaggle embedding notebook — ChemBERTa for the 1,006,840 compounds, ESM-2 for the 2,312 proteins (frozen); cache vectors keyed by InChIKey / accession; truncate giant proteins (max 34,350 residues).
3. Build classical baselines (logistic regression, XGBoost on fingerprints) as the floor for Stage 4.
4. **Owner tasks:** review DECISIONS.md D-011–D-019 (reversible if you disagree); teammate runs the pipeline; set up Kaggle.
5. **Stage 4 (project Week 5):** train the fusion head over the cached embeddings using the splits in `network1_v1.parquet`.

## Open decisions (most of Week 2 now locked)
Resolved this session: endpoints (D-011), thresholds (D-012), negatives/PU (D-013), compound identity (D-014),
min-data (D-015), temporal cutoff (D-016), BindingDB (D-017), hygiene (D-018), splits (D-019).
Remaining / pending:
| # | Decision | State |
|---|---|---|
| — | Owner sign-off on D-011–D-019 | Pending review (defaults chosen from evidence; reversible) |
| — | ESM-2 checkpoint size (35M vs 150M vs 650M) | Decide at Stage 3 from Kaggle GPU memory/time |
| — | ChemBERTa variant + pooling (CLS vs mean) | Decide at Stage 3 |
| — | Gene-symbol mapping for proteins (needed by Week 8) | Deferred to Network 2 |

## Gotchas
- **Python 3.12 only** in `.venv`. Scripts import `src.*`; run from repo root with `python -m ...`.
- **Memory:** building over the 8.3M-row extract needs care — drop the free-text comment column early and use category dtypes (see `build_network1.py`). The naive version was OOM-killed on 16 GB.
- `data/raw`, `data/interim`, `data/processed` are gitignored. `network1_v1.parquet` and `compounds_standardized.parquet` regenerate from the scripts.
- The ~1 h full-database test is excluded by default (`pytest -m slow`).

## Key numbers
ChEMBL 37 scope: 8.3M rows, 5,738 proteins, 1.56M compounds. Network 1: 1,905,586 pairs, 748,430 ACTIVE /
1,157,156 INACTIVE, 2,312 proteins, 1,006,840 compounds, 333,583 scaffold groups. Sources: `reports/stage0/`, `reports/week2/`.

## Where things are
`README.md` → front door. `docs/PROJECT_GUIDE.md` → full detail. `docs/PROJECT_LOG.md` → history. `DECISIONS.md` → decisions. `docs/stages/` → per-stage teaching.
