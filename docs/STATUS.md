# STATUS: where we are right now

*Last updated: 2026-11-22. History goes in `PROJECT_LOG.md`.*

## One-line state

**Network 1 and the classical baseline are complete; both Open Targets 26.09 Network 2 association tables are extracted and the corrected local joint validator now passes 17/17 checks; a fixed label-blind nine-candidate set and the first live four-policy literature run have been executed.** The initial Europe PMC run returned 15 candidate–strategy–publication records and two timeouts, but all returned records were disease-context only. A 12-query synonym diagnostic returned zero hits. Query refinement, human evidence annotation and matched-policy evaluation remain open. Current weighted engineering-plus-pilot progress estimate: **80%**; this is not scientific validation or model performance.

## Current Week 11 evidence checkpoint

- Local repository switched to `main` and fast-forwarded to commit `712f4a2`; local Week 9/10 output folders were backed up outside the repository.
- Environment: Python 3.12.6, pandas 3.0.6, PyArrow 25.0.1, scikit-learn 1.9.1.
- Local tests: 70 passed, 1 deselected.
- Network 2 validation: 17/17 critical checks true; zero warnings; bridge 2,295 rows; source-specific associations 1,739,224 rows; overall-direct associations 1,633,220 rows; 21,268 diseases; zero mapping mismatches/duplicate keys; zero missing disease names; 100% disease-name coverage; no out-of-range scores; no non-empty overall aggregationValue.
- Candidate set: 9 candidates, seed 42, three ACTIVE_ONLY, three INACTIVE_ONLY and three UNCERTAIN; label-blind true; observed DTI label column not used; all 9 anchor tiers STRONG.
- Initial live retrieval: fixed 3, uncertainty-only 0, disease-only 8, combined 4; 15 candidate–strategy–publication records in total; two 45-second ReadTimeout errors; all records include title, abstract and ID and remain UNANNOTATED.
- Actual router slot allocations: fixed 45, uncertainty-only 30, disease-only 45, combined 30 (150 total). The difference from the theoretical 180 slots is the intended STOP policy for INACTIVE_ONLY candidates in uncertainty-only and combined arms.
- Initial retrieval record set contains eight distinct candidate–publication pairs across strategies; records are policy exposures and may repeat the same candidate/publication across arms.
- PubChem candidate title resolution: 8/9 in the candidate-builder run. ChEMBL exact InChIKey matches: 9/9. The queried ChEMBL records returned no preferred names or synonyms.
- Europe PMC synonym diagnostic: 12 queries across DRD2, PTH1R and IRAK4 (chemical name/ChEMBL ID, synonym option false/true); all returned zero hits.
- Human annotations: none yet. Matched-policy evaluation: not run.

## Core dataset

Network 1 contains 1,905,586 labelled drug–protein pairs (748,430 ACTIVE / 1,157,156 INACTIVE), 2,312 proteins and 1,006,840 compounds. Four split definitions are available: random, drug-cold, target-cold and temporal.

## Completed and verified

- **Stage 1 — Data:** ChEMBL 37 and BindingDB 202609 were verified, extracted and profiled. See `docs/stage0_report.md`, `data/MANIFEST.md` and `reports/stage0/`.
- **Stage 2 — Network 1:** versioned labelled interaction table built; prior validation passed all 13 checks. One row per compound–protein pair; split assignments retained.
- **Stage 3 — embedding pilot:** 2,312 human protein sequences retrieved and checked. Small Colab/T4 pilot: 100 ChemBERTa compound vectors (384 dimensions) and 20 ESM-2 protein vectors (320 dimensions). Full cache remains pending.
- **Classical DTI baseline:** Morgan radius-2 / 2,048-bit fingerprints + `family_l1` one-hot logistic regression. Each split used reproducible pilot caps: 5,000 train / 1,000 calibration / 2,000 test rows (seed 42). ROC-AUC: random 0.8103; drug-cold 0.7785; target-cold 0.8009; temporal 0.6117. These are row-capped pilot metrics, not full-partition estimates.
- **Network 2 identifier bridge:** 2,295 high-confidence unique UniProt-to-Ensembl/Open Targets mappings prepared from 2,312 Network 1 accessions. Seventeen accessions remain in a review queue.
- **Full Network 2 source-specific extraction:** all 14 `association_by_datasource_direct` shards completed. 7,522,466 input rows were processed and 1,739,224 target-matched datasource-level records retained for 2,295 bridge targets and 21,268 diseases. No duplicate target–disease–source keys were retained.
- **Overall-direct Network 2 extraction:** all 14 `association_overall_direct` shards completed. 7,225,847 input rows were processed and 1,633,220 rows retained for 2,295 targets and 21,268 diseases. Disease metadata unmatched rows: zero.
- **Joint Network 2 validation — corrected local rerun:** on 2026-11-21, all 17 critical checks passed. The earlier failure was the stringified `None` in every overall `aggregationValue`; the corrected builder/validator null-sentinel handling now passes against the actual local Parquet data.
- **Week 11 candidate set:** nine label-blind candidates generated with seed 42, three per conformal state. All nine had STRONG overall-direct anchors. The observed DTI label column was not used for selection.

## Baseline pilot metrics

All four runs used train/calibration/test sample caps of 5,000 / 1,000 / 2,000. These are classical row-capped pilot results, not the final ChemBERTa/ESM-2 fusion model.

| Split | ROC-AUC | Average precision | Balanced accuracy | Brier | 15-bin ECE | Empirical set coverage |
|---|---:|---:|---:|---:|---:|---:|
| Random | 0.8103 | 0.7296 | 0.7362 | 0.1883 | 0.1104 | 0.9005 |
| Drug-cold | 0.7785 | 0.6846 | 0.6969 | 0.2115 | 0.1421 | 0.8955 |
| Target-cold | 0.8009 | 0.6484 | 0.7230 | 0.1843 | 0.1163 | 0.9315 |
| Temporal | 0.6117 | 0.5887 | 0.5792 | 0.3293 | 0.2741 | 0.8335 |

## Current workstream and next actions — Week 11

1. Preserve the initial retrieval run; it is the baseline for query refinement.
2. Improve and test query formulations without changing the nine-candidate pool or silently changing the policy weights.
3. Re-run all four arms with the same per-candidate cap and write outputs to separate versioned files/directories.
4. Inspect query-level coverage, records, provenance and technical failures. Do not equate empty results with CONTRADICT evidence.
5. Prepare the blinded annotation worksheet from the accepted retrieval run. Keep the strategy manifest/key private until labels are frozen.
6. Complete every unique candidate–publication row with evidence category, SUPPORT / CONTRADICT / UNKNOWN and rationale.
7. Run the Week 11 evaluation phase; inspect metrics and exact denominators.
8. Update the Week 11 final report and form entries with actual outcomes. Record actual development hours rather than estimating them.

## Open decisions / limitations

| Topic | Current state |
|---|---|
| Full ChemBERTa / ESM-2 embedding cache | Pending |
| Fusion model | Pending |
| Formal probability calibration | Not complete |
| Network 2 direct association tables | Extracted locally and joint validation passed 17/17 |
| Candidate set | Fixed nine-candidate label-blind pilot generated |
| Literature retrieval query quality | Open; initial 15-record run is disease-context-only; 12 synonym probes returned zero hits |
| Human evidence-direction annotation | Pending |
| Matched-budget comparison | Pending |
| Sealed retrospective cases | Remain untouched until the documented evaluation gate is ready |

## Research safeguards

- Network 1 compound–protein predictions and Network 2 curated protein–disease associations remain separate, with provenance.
- `UNKNOWN` is not `CONTRADICT`; no result is not negative evidence.
- Open Targets association scores are prioritisation/association signals, not probabilities or proof of causality.
- Do not claim the adaptive retrieval policy improves precision or counter-evidence recall until a matched-budget experiment with reproducible human annotations is run.
- Do not commit raw or processed Parquet tables, downloaded shards, retrieved abstracts, candidate files, caches, local model binaries, annotation worksheets or private strategy mappings.
