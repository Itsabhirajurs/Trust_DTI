# STATUS: where we are right now

*Last updated: 2026-11-18. History goes in `PROJECT_LOG.md`.*

## One-line state

**Stages 1–2 and the classical baseline pilots are complete; the 2,295-target Open Targets bridge is validated; both direct Network 2 tables have been extracted locally across all 14 shards.** The first joint validation run passed 16/17 checks; the sole issue was a stringified `None` in overall `aggregationValue`. The builder/validator correction and regression tests are merged into `main` through PR #3. The merged main-branch GitHub Actions run passed; the full test log on the fix branch reported 61 passed, 2 skipped and 1 deselected. Local data-backed revalidation is still pending. Week 11 is the final planned pilot sprint. Starting estimate: 70% of the weighted engineering-and-pilot workflow is complete; 30% remains. The Week 11 runner orchestrates the local gates but has not yet been executed against owner-local data in this environment.

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
- **Full Network 2 source-specific extraction:** on 2026-11-11, all 14 `association_by_datasource_direct` shards completed. The run processed 7,522,466 source rows and retained 1,739,224 target-matched datasource-level records for all 2,295 bridge targets and 21,268 distinct diseases. All 1,739,224 target–disease–source keys were unique; zero duplicate-key rows were retained. Source distribution and download manifest were written under `outputs/week09_network2/`; the filtered table is `data/processed/network2_direct_associations.parquet`.
- **Overall-direct Network 2 extraction:** on 2026-11-11, all 14 `association_overall_direct` shards completed. The run processed 7,225,847 input rows and retained 1,633,220 rows for all 2,295 bridge targets and 21,268 disease IDs. The disease metadata join reported zero unmatched rows; the joint audit found zero duplicate target–disease keys, zero mapping mismatches, no missing disease names, and all scores within [0, 1]. The output is `data/processed/network2_overall_direct.parquet`; audit: `outputs/week10/network2_overall_direct_audit.json`.
- **Joint Network 2 validation — first run:** all checks passed except `overall_aggregation_value_empty`. Inspecting the Parquet field showed the literal string `None` in all 1,633,220 rows; it is a serialized null sentinel, not an aggregation value. The follow-up code accepts common null sentinels and normalizes them to Arrow nulls on extraction. The fix is merged and the latest main-branch CI run passed; the data-backed local validator rerun remains pending.
- **Disease metadata inspection:** the Open Targets 26.09 disease table downloaded and inspected successfully: 45,896 records and 18 columns, including names, descriptions, ontology relationships and synonyms. Schema/sample JSON files were saved in `outputs/week09_network2/`.
- **Windows cleanup fix:** the Parquet lifecycle helper is isolated in `src/network/parquet_io.py`; the complete 14-shard rerun confirms temporary shard cleanup worked for newly downloaded shards. GitHub Actions on the merged Week 10 main commit `efa115a` passed the fast test suite.

## Baseline pilot metrics

All four runs used train/calibration/test sample caps of 5,000 / 1,000 / 2,000. Scores below come from the committed JSON metrics files.

| Split | ROC-AUC | Average precision | Balanced accuracy | Brier | 15-bin ECE | Empirical set coverage |
|---|---:|---:|---:|---:|---:|---:|
| Random | 0.8103 | 0.7296 | 0.7362 | 0.1883 | 0.1104 | 0.9005 |
| Drug-cold | 0.7785 | 0.6846 | 0.6969 | 0.2115 | 0.1421 | 0.8955 |
| Target-cold | 0.8009 | 0.6484 | 0.7230 | 0.1843 | 0.1163 | 0.9315 |
| Temporal | 0.6117 | 0.5887 | 0.5792 | 0.3293 | 0.2741 | 0.8335 |

**Interpretation limits:** this is a classical family-feature baseline, not the final ChemBERTa/ESM-2 fusion model. Metrics are based on row-capped samples. The prediction-set values are empirical diagnostics; no formal coverage guarantee is claimed under unverified exchangeability, pair dependence or distribution shift.

## Current workstream and next actions — Week 11 final sprint

1. Pull the work/week11-final-completion branch, activate the existing .venv, and run python -m pytest -q.
2. Execute python scripts/week11/run_week11_pipeline.py --phase prepare. It reruns the corrected Network 2 validator against the local Parquet data, then builds the fixed label-blind candidate set (up to nine), runs four Europe PMC strategies with a five-document cap per candidate, and prepares the blinded worksheet.
3. Inspect outputs/week11/week11_execution_status.json, the Network 2 audit, candidate audit, retrieval metadata/failures, and annotation worksheet.
4. Complete every unique candidate-publication annotation with SUPPORT / CONTRADICT / UNKNOWN, evidence category and rationale. Keep the strategy manifest/key private until annotations are frozen.
5. Run python scripts/week11/run_week11_pipeline.py --phase evaluate and inspect the matched-policy metrics.
6. Update the Week 11 report and form from actual evidence. Do not claim strategy improvement or exhaustive literature recall.

## Open decisions / limitations

| Topic | Current state |
|---|---|
| Full ChemBERTa / ESM-2 embedding cache | Pending; GPU-scale run not completed |
| Fusion model | Pending |
| Formal probability calibration | Not complete; existing conformal-style outputs are diagnostics |
| Direct-by-datasource Network 2 extraction | Completed locally: 1,739,224 rows across all 14 shards; joint QA pending |
| Overall-direct disease association table | Extraction and disease join completed locally: 1,633,220 rows across all 14 shards; joint QA pending after null-sentinel fix |
| Disease anchor thresholds | Quantile rule implemented; cutoffs must be frozen from the extracted overall-direct score distribution |
| Evidence direction annotation | Blinded sheet and evaluator implemented; human annotation pending |
| Literature retrieval and counter-evidence | Europe PMC retrieval code implemented; live candidate run pending |
| Matched-budget comparison | Four policies implemented; human adjudication and measured comparison pending |
| Sealed retrospective cases | Remain untouched until the documented Week 9 evaluation gate is ready |

## Research safeguards

- Network 1 compound–protein predictions and Network 2 curated protein–disease associations remain separate, with provenance.
- `UNKNOWN` is not `CONTRADICT`; no result is not negative evidence.
- Open Targets association scores are prioritization/association scores, not probabilities or proof of causality. Source-specific scores are not averaged together.
- Do not claim the adaptive retrieval policy improves precision or counter-evidence recall until a matched-budget experiment with reproducible annotations is run.
- Do not commit raw, interim or processed Parquet datasets, local model binaries, caches or `.venv`.

## Week 10 and Week 11 documentation packages

Week 10 technical and submission materials: reports/week10/README.md and docs/stages/week10.md. Week 11 final sprint instructions, progress baseline and report templates: reports/week11/README.md. The final local-run orchestrator is scripts/week11/run_week11_pipeline.py.

## Where things are

`README.md` → entry point. `docs/STATUS.md` → current state. `docs/PROJECT_LOG.md` → dated history. `DECISIONS.md` → methodological decisions. `docs/stages/` → teaching notes. `reports/` → reports and small derived artifacts.
