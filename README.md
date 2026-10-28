# TrustDTI

An uncertainty-aware drug–protein interaction (DTI) research project exploring whether calibrated prediction uncertainty and curated disease context can improve evidence retrieval for drug repurposing.

TrustDTI's research question is whether literature retrieval conditioned on calibrated DTI prediction uncertainty plus a disease-relevance signal improves evidence precision and counter-evidence recall compared with fixed retrieval under the same candidate set and budget.

**Current state (28 Oct 2026):**
- **Stage 1 — Data:** ChEMBL 37 and BindingDB were verified, extracted, and profiled.
- **Stage 2 — Network 1:** built and validated; 1,905,586 labelled drug–protein pairs, 1,006,840 compounds, and 2,312 proteins.
- **Stage 3 — Embeddings:** a small pilot passed. 100 compounds produced ChemBERTa vectors of dimension 384; 20 proteins produced ESM-2 vectors of dimension 320. The full embedding cache is not built.
- **Stage 4 baseline:** a resource-capped Morgan-fingerprint + protein-family logistic-regression runner and tests are in the repository. GitHub Actions reports 17 passed, 2 skipped, 1 slow test deselected. The runner has **not yet been run against the local Network 1 dataset**, so no DTI baseline metrics are claimed yet.
- **Still pending:** full-scale embeddings, the neural fusion model, robust split-by-split evaluation, formal calibration assessment, curated protein–disease Network 2, deterministic routing, evidence retrieval, and matched-budget experiments.

Read [`docs/STATUS.md`](docs/STATUS.md) for exact state and the ordered next steps.

## Pick up where you left off
Open the working folder `C:\Users\91701\code\Trust_DTI` (not the old OneDrive copy), then ask your assistant:

> Read `AGENTS.md`, then `docs/STATUS.md` and the top 3 entries of `docs/PROJECT_LOG.md`. Tell me in 5 lines where we are and what you suggest next, then wait for me. I am still learning this project, so explain simply and one pipeline stage at a time.

## Where to read what

| I want… | Read |
|---|---|
| Current state and next actions | [`docs/STATUS.md`](docs/STATUS.md) |
| Session history | [`docs/PROJECT_LOG.md`](docs/PROJECT_LOG.md) |
| Project overview and research question | [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md) |
| Methodological decisions | [`DECISIONS.md`](DECISIONS.md) |
| Stage teaching notes | [`docs/stages/`](docs/stages/README.md) |
| Consolidated reports and experimental outputs | [`reports/`](reports/README.md) |
| Week 7 report and infographic | [`reports/week07_embedding_pilot/`](reports/week07_embedding_pilot/) |
| Week 8 sprint plan | [`docs/plans/week08_core_pipeline_sprint.md`](docs/plans/week08_core_pipeline_sprint.md) |
| Baseline instructions | [`docs/stages/baseline_before_fusion.md`](docs/stages/baseline_before_fusion.md) |
| Raw data sources and checksums | [`data/MANIFEST.md`](data/MANIFEST.md) |

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
python -m pytest -q
```

For CI-style dependencies, use `pip install -r requirements-ci.txt`.

## Run the classical baseline

After the local ignored data files are available and the repository is up to date:

```bash
python -m src.model.evaluate_dti_baseline --split random
```

Then run `--split drugcold`, `--split targetcold`, and `--split temporal` separately. The first-run defaults cap the train/calibration/test samples to 50,000 / 10,000 / 20,000 rows; the report records actual partition sizes. The model is a baseline only and does not use the pilot ChemBERTa/ESM-2 embeddings.

Raw ChEMBL and BindingDB data, local environments, caches, and trained model artifacts are not to be committed.
