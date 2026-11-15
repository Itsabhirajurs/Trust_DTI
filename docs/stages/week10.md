# Week 10: Network 2 completion and adaptive literature retrieval

## Purpose
Week 10 connects curated protein-disease context to TrustDTI's evidence-retrieval prototype. The objective is a reproducible workflow to compare retrieval policies fairly, not to claim one policy already wins.

`Network 1 prediction -> Network 2 disease context -> deterministic routing -> Europe PMC -> blinded annotation -> matched-budget evaluation`

## 1. Separate Network 2 products
Open Targets 26.09 provides `association_by_datasource_direct` and the separate `association_overall_direct` product. The source-specific build processed 7,522,466 inputs across 14 shards and retained 1,739,224 rows for 2,295 targets and 21,268 diseases. The overall-direct build processed 7,225,847 inputs and retained 1,633,220 rows for the same 2,295 targets and 21,268 disease IDs. The disease metadata join covered 45,896 metadata records with zero unmatched association rows.

Do not average source-specific scores into an overall score. Open Targets association scores are evidence-prioritisation scores, not probabilities or causal proof.

## 2. Validation edge case
The first joint validator passed 16/17 checks. Every overall row had `aggregationType=overall` and the literal string `None` in `aggregationValue`; this is a serialized null. The builder now normalizes common sentinels to Arrow nulls; the validator treats them as missing. Regression tests cover `None`, `null`, blank and `<NULL>`. CI: 61 passed, 2 skipped, 1 deselected. Local data-backed validation must still be rerun.

## 3. Seven deterministic policies
| Prediction set | Disease tier | Policy |
|---|---|---|
| ACTIVE | STRONG | CONFIRM |
| ACTIVE | MODERATE | CONTEXTUALISE |
| ACTIVE | WEAK / NONE | INVESTIGATE |
| ACTIVE + INACTIVE | STRONG | CHALLENGE |
| ACTIVE + INACTIVE | MODERATE | CHALLENGE_CONTEXT |
| ACTIVE + INACTIVE | WEAK / NONE | LOW_PRIORITY |
| INACTIVE | Any | STOP |

The router is deterministic code in `src/network/router.py`; an LLM does not choose the route.

## 4. Literature and annotation
Europe PMC records preserve stable identifiers, URL, query and retrieval time. Retrieved records start UNANNOTATED. Human labels are SUPPORT, CONTRADICT or UNKNOWN. UNKNOWN is not CONTRADICT, and query intent does not determine direction.

## 5. Matched-policy comparison
The same candidates are evaluated under `fixed`, `uncertainty_only`, `disease_only` and `combined`:
```bash
python scripts/week10/validate_network2.py
python scripts/week10/build_candidate_set.py --per-state 3 --max-candidates 9
python scripts/week10/run_retrieval_demo.py --budget-per-candidate 5
python scripts/week10/prepare_annotation_sheet.py
```
After annotation:
```bash
python scripts/week10/evaluate_retrieval.py --budget-per-candidate 5
```
Pooled counter-evidence recall is limited to the four retrieved pools, not all literature.

## 6. Current status
Completed locally: both 14-shard association extractions and disease metadata join. Completed in code/CI: null-sentinel correction, router, Europe PMC client, four strategy arms, blinded worksheet and evaluator. Still open: local joint validation, actual candidate set, live retrieval, human annotations and matched-budget evaluation.

See [the Week 10 progress report](../../reports/week10/Week_10_Progress_Report.md).
