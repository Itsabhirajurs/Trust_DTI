# STATUS: where we are right now

*Last updated: 2026-11-11. History goes in `PROJECT_LOG.md`.*

## One-line state

**Stages 1–2 are built and validated; a small Stage 3 embedding pilot is complete; the classical DTI baseline has been run on all four predefined split types; Open Targets target mapping is prepared for Network 2; full Network 2 association extraction is the current local execution gate.** The deterministic router, literature evidence pipeline, matched-budget comparison and integrated demo are not yet complete.

This status is about the engineering prototype. It is not a claim that the research question has been proven.

## Core dataset

Network 1 contains 1,905,586 labelled drug–protein pairs (748,430 ACTIVE / 1,157,156 INACTIVE), 2,312 proteins and 1,006,840 compounds. Four split definitions are available: random, drug-cold, target-cold and temporal.

## Completed and verified

- **Stage 1 — Data:** ChEMBL 37 and BindingDB 202609 were verified, extracted and profiled. See `docs/stage0_report.md`, `data/MANIFEST.md` and `reports/stage0/`.
- **Stage 2 — Network 1:** versioned labelled interaction table built; prior validation passed all 13 checks. One row per compound–protein pair; split assignments retained.
- **Stage 3 — embedding pilot:** 2,312 human protein sequences retrieved and checked. Small Colab/T4 pilot: 100 ChemBERTa compound vectors (384 dimensions) and 20 ESM-2 protein vectors (320 dimensions). Full cache remains pending.
- **Classical DTI baseline:** Morgan radius-2 / 2,048-bit fingerprints + `family_l1` one-hot logistic regression. Each split used the reproducible pilot caps: 5,000 train / 1,000 calibration / 2,000 test rows (seed 42). All saved split-integrity checks passed.
- **Baseline metrics:** see `reports/model_baseline/baseline_metrics_*_morgan_family.json` and prediction CSVs. ROC-AUC: random 0.8103; drug-cold 0.7785; target-cold 0.8009; temporal 0.6117. Temporal performance and calibration diagnostics deteriorate substantially; this is a limitation, not something to hide. These are row-capped pilot metrics, not full-partition estimates.
- **Compound representation sensitivity:** Standard InChI round-trip was assessed on random and drug-cold pilot samples. The original branch reproduced the baseline; normalization produced small, inconsistent metric changes, so the original representation remains the reference.
- **Network 2 identifier bridge:** 2,295 high-confidence unique UniProt-to-Ensembl/Open Targets target mappings prepared from 2,312 Network 1 accessions. 2,170 are one-to-one and 125 one-to-many cases were resolved using a unique direct UniProt cross-reference. Seventeen accessions remain in a review queue. The bridge includes 2,294 protein-coding rows and one IG_V_gene row (retained with an explicit biotype flag).
- **Open Targets target validation:** release 26.09 target index contains 78,733 unique target IDs. 2,301 / 2,312 Network 1 accessions had at least one Open Targets target (99.52%).
- **Association dataset reconnaissance:** the 26.09 `association_by_datasource_direct` directory lists 14 shards (~821.33 MB compressed); `disease` lists one file (~6.05 MB). The first association shard schema was inspected. A two-shard extraction test matched 248,834 datasource-level rows (114,855 + 133,979), then stopped on a Windows file lock during cleanup. No complete Network 2 association output is claimed yet.
- **Windows cleanup fix:** Parquet reader cleanup was isolated in `src/network/parquet_io.py`; regression tests cover closing/deleting and closing/retaining reused files. GitHub Actions on commit `36d4161` passed **19 tests, 2 skipped, 1 deselected**. The full association build still needs a rerun on the Windows workstation.

## Baseline pilot metrics

All four runs used train/calibration/test sample caps of 5,000 / 1,000 / 2,000. Scores below come from the committed JSON metrics files.

| Split | ROC-AUC | Average precision | Balanced accuracy | Brier | 15-bin ECE | Empirical set coverage |
|---|---:|---:|---:|---:|---:|---:|
| Random | 0.8103 | 0.7296 | 0.7362 | 0.1883 | 0.1104 | 0.9005 |
| Drug-cold | 0.7785 | 0.6846 | 0.6969 | 0.2115 | 0.1421 | 0.8955 |
| Target-cold | 0.8009 | 0.6484 | 0.7230 | 0.1843 | 0.1163 | 0.9315 |
| Temporal | 0.6117 | 0.5887 | 0.5792 | 0.3293 | 0.2741 | 0.8335 |

**Interpretation limits:** this is a classical family-feature baseline, not the final ChemBERTa/ESM-2 fusion model. Metrics are based on row-capped samples. The prediction-set values are empirical diagnostics; no formal coverage guarantee is claimed under unverified exchangeability, pair dependence or distribution shift.

## Current workstream and next actions

1. Pull the latest `main` on the Windows workstation and rerun `python scripts/week09/build_network2_direct_associations.py`. Confirm all 14 shards finish and disease metadata schema is printed.
2. Validate the filtered association Parquet: schema, row counts, target/disease coverage, source distribution, duplicate keys, nulls and score ranges. Keep source-specific scores separate.
3. Confirm whether release 26.09 exposes `association_by_overall_direct`; use the official overall direct association score as the main anchor if present, while retaining source-level associations for provenance. Do not average source-specific scores ourselves.
4. Join disease metadata; preserve `curated` provenance, Open Targets release, target identifiers and source identifiers. Keep the 17 unresolved protein mappings separate.
5. Implement the deterministic uncertainty × disease-relevance router with unit tests for all seven policies. UNKNOWN evidence must never become CONTRADICT.
6. Build a small literature retrieval prototype with stable record identifiers, source URL, retrieval timestamp, query, retrieval intent, publication metadata, text provenance and explicit empty/error handling.
7. Prepare a small, reproducible candidate set and an annotation protocol before evaluating fixed, uncertainty-only, disease-only and combined retrieval under identical budgets.
8. Integrate a reproducible CLI/demo path and document setup, outputs and limitations.

## Open decisions / limitations

| Topic | Current state |
|---|---|
| Full ChemBERTa / ESM-2 embedding cache | Pending; GPU-scale run not completed |
| Fusion model | Pending |
| Formal probability calibration | Not complete; existing conformal-style outputs are diagnostics |
| Full Network 2 association extraction | Pending local rerun after Windows cleanup fix |
| Overall direct disease association score availability | Must verify for Open Targets 26.09 |
| Disease anchor thresholds | Must define and document before evaluation |
| Evidence direction annotation | Must be explicit; retrieved query intent is not a ground-truth label |
| Literature retrieval and counter-evidence | Not implemented end-to-end yet |
| Matched-budget comparison | Pending candidate set and adjudicated outcome labels |
| Sealed retrospective cases | Remain untouched until the documented Week 9 evaluation gate is ready |

## Research safeguards

- Network 1 compound–protein predictions and Network 2 curated protein–disease associations remain separate, with provenance.
- `UNKNOWN` is not `CONTRADICT`; no result is not negative evidence.
- Open Targets association scores are prioritization/association scores, not probabilities or proof of causality. Source-specific scores are not averaged together.
- Do not claim the adaptive retrieval policy improves precision or counter-evidence recall until a matched-budget experiment with reproducible annotations is run.
- Do not commit raw, interim or processed Parquet datasets, local model binaries, caches or `.venv`.

## Where things are

`README.md` → entry point. `docs/STATUS.md` → current state. `docs/PROJECT_LOG.md` → dated history. `DECISIONS.md` → methodological decisions. `docs/stages/` → teaching notes. `reports/` → reports and small derived artifacts.
