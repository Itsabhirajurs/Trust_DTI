# TrustDTI

TrustDTI is an uncertainty-aware drug–protein interaction research prototype. It investigates whether calibrated DTI prediction uncertainty and curated protein–disease context can guide literature retrieval to improve evidence precision and counter-evidence recall compared with fixed retrieval under the same candidate set and budget.

## Current state (11 Nov 2026)

- **Network 1:** 1,905,586 labelled drug–protein pairs, 1,006,840 compounds and 2,312 proteins; four split definitions and prior data validation.
- **Embedding pilot:** ChemBERTa 100 × 384 and ESM-2 20 × 320 sample outputs passed integrity checks. Full embeddings remain pending.
- **Classical baseline:** Morgan fingerprints + protein-family one-hot logistic regression evaluated on random, drug-cold, target-cold and temporal pilot samples. See [baseline metrics](reports/model_baseline/). ROC-AUC: 0.8103 / 0.7785 / 0.8009 / 0.6117 respectively. Each run used 5k/1k/2k train/calibration/test caps; see JSON files for full details and caveats.
- **Network 2 target bridge:** 2,295 high-confidence UniProt–Ensembl/Open Targets mappings; 17 accessions remain in the review queue. Open Targets 26.09 target-index coverage is 2,301/2,312 (99.52%).
- **Network 2 associations:** direct-by-datasource extraction was tested on two shards (248,834 matched records) but the complete 14-shard output still needs a local rerun. A separate Open Targets overall-direct score dataset is identified for the disease anchor; neither full association table has yet passed the combined local validation gate.
- **Prototype implementation branch:** `work/90-percent-prototype` adds the overall-direct builder, Network 2 validator, deterministic seven-policy uncertainty × disease router, Europe PMC retrieval with provenance, four matched-budget retrieval strategies, a human annotation worksheet and an evaluator. Pull-request CI and local data-backed execution are still required.
- **Still pending:** full Network 2 extraction/join validation, end-to-end retrieval run, human evidence annotation, policy comparison and integrated demo results.

**Do not interpret row-capped pilot metrics as full-partition estimates or empirical prediction-set coverage as a formal guarantee.** The project’s scientific research question has not yet been answered.

Read [`docs/STATUS.md`](docs/STATUS.md) for the current ordered work plan.

## Pick up where you left off

Working folder: `C:\Users\91701\code\Trust_DTI` (not the old OneDrive copy).

```bash
git fetch origin
git checkout work/90-percent-prototype
git pull origin work/90-percent-prototype
.venv/Scripts/activate
python -m pytest -q
```

Then follow the next action in [`docs/STATUS.md`](docs/STATUS.md).

## Where to read what

| I want… | Read |
|---|---|
| Current state and ordered next steps | [docs/STATUS.md](docs/STATUS.md) |
| Session history | [docs/PROJECT_LOG.md](docs/PROJECT_LOG.md) |
| Project design and research question | [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) |
| Methodological decisions | [DECISIONS.md](DECISIONS.md) |
| Stage-by-stage explanations | [docs/stages/](docs/stages/README.md) |
| Network 2 mapping and association concepts | [docs/stages/network2.md](docs/stages/network2.md) |
| Baseline implementation and limitations | [docs/stages/baseline_before_fusion.md](docs/stages/baseline_before_fusion.md) |
| Weekly reports and derived results | [reports/](reports/README.md) |
| Week 9 milestone report | [reports/week09/](reports/week09/README.md) |

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
python -m pytest -q
```

## Run the classical baseline

```bash
python -m src.model.evaluate_dti_baseline --split random
python -m src.model.evaluate_dti_baseline --split drugcold
python -m src.model.evaluate_dti_baseline --split targetcold
python -m src.model.evaluate_dti_baseline --split temporal
```

Default row caps are 50,000 / 10,000 / 20,000. The committed Week 9 pilot metrics were generated with lower caps (5,000 / 1,000 / 2,000); consult their JSON files for the exact settings.

Raw ChEMBL/BindingDB data, interim and processed data, local environments, caches and trained model binaries must not be committed.
