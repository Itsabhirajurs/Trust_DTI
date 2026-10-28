# STATUS: where we are right now

*Last updated: 2026-10-28. Rewrite this file at the end of every session. History goes in `PROJECT_LOG.md`.*

## One-line state

**Stages 1 and 2 are built and verified; Stage 3 has a successful small embedding pilot; a test-covered classical DTI baseline runner has been added but has not yet been run on the local dataset.** No full-dataset embeddings, DTI performance metrics, formal calibrated predictions, Network 2, router, or evidence-policy comparison are complete yet.

Network 1 contains 1,905,586 labelled drug–protein pairs (748,430 ACTIVE / 1,157,156 INACTIVE), 2,312 proteins, and 1,006,840 compounds. Four precomputed split definitions are available.

## Current progress

- **Stage 1 — Data:** ChEMBL 37 and BindingDB were verified, extracted, and profiled; see `docs/stage0_report.md` and `reports/stage0/`.
- **Stage 2 — Network 1:** `src/network/build_network1.py` and `src/network/validate_network1.py` build/validate the labelled table. Earlier local validation passed all 13 checks.
- **Stage 3 — embedding pilot:** 2,312 UniProt human protein sequences were retrieved and passed the implemented sequence/length checks. On Colab/Tesla T4, ChemBERTa produced 100 × 384 compound embeddings and ESM-2 produced 20 × 320 protein embeddings. This is only a smoke test; the full cache is not created.
- **Week 7 result artifacts:** The seven NPZ/CSV/JSON result files were verified locally and reside under `reports/week07_embedding_pilot/pilot_results/`.
- **Classical DTI baseline:** `src/model/evaluate_dti_baseline.py` now implements a capped Morgan-fingerprint + `family_l1` one-hot logistic-regression baseline using the existing split assignments. It saves metrics and test predictions under `reports/model_baseline/`; the estimator artifact is written under ignored `data/processed/`. It must first be run against local data.
- **CI:** GitHub Actions passed the fast suite on commit `d7e0db4`: **17 passed, 2 skipped, 1 deselected**. Two tests need local ChEMBL files; the full-database test is deliberately deselected. The first CI attempt failed because the Windows-frozen requirements tried to compile `pywinpty` on Linux; CI now uses `requirements-ci.txt`.
- **Week 8 plan:** `docs/plans/week08_core_pipeline_sprint.md`.

## Next actions — strictly in order

1. Keep the seven Week 7 result files in `reports/week07_embedding_pilot/pilot_results/`.
2. Run `python -m pytest -q` locally. Commit/push only the seven audited Week 7 result files; never add raw, interim, processed Parquet data, the virtual environment, or caches.
3. Run the default resource-capped random baseline: `python -m src.model.evaluate_dti_baseline --split random`. Inspect runtime, actual sampled counts, split checks, ROC-AUC/average precision, balanced accuracy, Brier/ECE, and the empirical prediction-set diagnostic. Do not claim baseline performance until this output exists.
4. If the random baseline completes acceptably, run separate `drugcold`, `targetcold`, and `temporal` invocations. Compare results only with each cap and split integrity recorded.
5. Decide whether to add a separately fitted probability calibrator after inspecting the baseline. Keep probability calibration distinct from conformal prediction sets; do not claim guaranteed coverage without justified assumptions.
6. Build curated protein–disease Network 2 with source/version, stable identifiers, confidence/evidence, and explicit curated provenance. Never mix disease links with predicted drug–protein edges.
7. Implement and unit-test the deterministic router; the UNKNOWN evidence state must never be converted to CONTRADICT.
8. Build a small literature retrieval prototype with source URLs, retrieval dates, queries/policies, evidence direction, and an empty-result/error path.
9. Run the fixed-vs-adaptive policy comparison only when a reproducible candidate set, labels, retrieval budget, and outcome definitions are in place.

## Sprint completion definition

A “90% prototype” means a runnable core path with passing tests, recorded baseline metrics, explicit uncertainty/disease/router contracts, and a small traceable evidence demo. It does **not** mean the scientific research question is proven. Full-scale embeddings and matched-budget retrieval experiments must have actual runs and saved results before being reported as completed.

## Open decisions

| Topic | State |
|---|---|
| Final ChemBERTa checkpoint/pooling | Pilot choice only; benchmark before locking |
| Final ESM-2 checkpoint/pooling | 8M + mean pooling used for pilot only |
| Full-scale embedding hardware/storage | Not benchmarked |
| Classical baseline metrics | Runner and tests added; local data run pending |
| Fusion head | Not started |
| Probability calibration and conformal analysis | Conformal-style diagnostic in baseline; full calibration assessment pending |
| Curated protein–disease network | Not started |
| Router, evidence retrieval, matched-budget experiment | Not started |

## Key numbers

- Network 1: 1,905,586 labelled pairs; 748,430 ACTIVE; 1,157,156 INACTIVE.
- Unique Network 1 compounds: 1,006,840.
- Unique Network 1 proteins: 2,312.
- Week 7 retrieval: 2,312 / 2,312 protein sequences returned and passed the implemented checks.
- Week 7 pilot: ChemBERTa 100 × 384; ESM-2 20 × 320; both had zero truncated inputs and finite outputs.
- Latest successful CI: 17 passed, 2 skipped, 1 deselected.

## Where things are
`README.md` → front door. `docs/STATUS.md` → present state. `docs/PROJECT_LOG.md` → history. `DECISIONS.md` → methodological choices. `docs/stages/` → teaching notes. `reports/` → experimental outputs & weekly reports. `reports/week07_embedding_pilot/` → course Week 7 evidence.
