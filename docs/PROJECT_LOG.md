## 2026-11-22 · Week 11 local Network 2 validation, candidate build and retrieval diagnostics

**Where:** Windows research workstation `C:\Users\91701\code\Trust_DTI`; documentation checkpoint captured to GitHub branch `docs/week11-actual-progress` · **Stage / project week:** Week 11 / final Network 2 + adaptive literature retrieval pilot

**Done:**
- Updated local `main` to merged repository commit `712f4a2`; backed up local Week 9 and Week 10 outputs outside the repository.
- Verified Python 3.12.6, pandas 3.0.6, PyArrow 25.0.1 and scikit-learn 1.9.1. Local pytest: 70 passed, 1 deselected.
- Reran the corrected Network 2 validator against the local bridge and both association Parquet tables. All 17 critical checks passed; warnings 0.
- Preserved the earlier failed audit and installed the passing rerun at the candidate builder's canonical audit path.
- Generated nine label-blind candidates (seed 42; 3 ACTIVE_ONLY, 3 INACTIVE_ONLY, 3 UNCERTAIN); the observed DTI label column was not used; all nine anchors were STRONG.
- Ran the first live four-policy Europe PMC retrieval with a five-document per-candidate cap. It returned 15 candidate–strategy–publication records across the four arms and recorded two 45-second ReadTimeout failures.
- Audited routing allocations (150 policy slots after intentional STOP allocations), record metadata, candidate coverage and returned intents. All 15 records were disease-context-only and remained UNANNOTATED.
- Performed PubChem/ChEMBL identity follow-up. Exact ChEMBL InChIKey matches were found for all nine candidates; queried ChEMBL preferred-name and synonym fields were empty.
- Tested 12 Europe PMC chemical-name/ChEMBL-ID queries across DRD2, PTH1R and IRAK4 with synonym expansion off/on. All 12 returned zero hits.
- Updated the Week 11 interim report, infographic, activity log, form entries, checklist, reproduction guide, aggregate evidence JSON and status snapshot.

**Found:**
- Network 2 local QA: 2,295 bridge rows; 1,739,224 source-specific rows; 1,633,220 overall-direct rows; 21,268 disease IDs; zero mapping mismatches, duplicate keys, missing source IDs or missing disease names; 100% disease-name coverage; all scores within [0, 1]; no non-empty overall `aggregationValue`; 17/17 critical checks true.
- Initial strategy counts: fixed 3; uncertainty-only 0; disease-only 8; combined 4. Candidate coverage: 3, 0, 3 and 2 respectively. The 15 strategy records represent eight distinct candidate–publication pairs across the arms.
- Two request failures were network read timeouts, not negative biological evidence.
- No retrieved record was mechanistic, counter-evidence or general-intent. Query quality remains the main blocker before annotation.

**Changed vs plan:** the live retrieval stage has been executed but is only partially complete because its coverage is low and returned evidence is restricted to disease context. The pilot remains at an interim 80% weighted project-management estimate (20% remains), with 5/10 points credited to candidate/live-retrieval execution, 0/10 to human annotation and 0/5 to final evaluation.

**Decisions:** preserve the initial retrieval JSONL, failures and metadata as the baseline. Do not change candidate selection or policy weights to inflate results. ChEMBL ID match verifies chemical identity, not a drug–target interaction. Zero query hits do not imply no literature or inactive biology. Keep UNKNOWN distinct from CONTRADICT and keep strategy key/manifest private until annotation is frozen.

**Open / next:** improve controlled query formulations; rerun the four arms into versioned outputs; prepare and manually complete blinded annotations; run the matched-budget evaluator; report measured metrics and denominators. Enter actual Week 11 development hours in the course form.

**For the owner to understand:** the Network 2 foundation and fixed candidate set are now supported by local evidence. The first retrieval run shows that API connectivity alone is not enough—the search terms must reliably find compound–target evidence before human review and policy comparison can answer the research question.

---

## 2026-11-18 · Week 11 final completion sprint established
**Where:** GitHub feature branch `work/week11-final-completion` · **Stage / project week:** Week 11 / final Network 2 + adaptive literature retrieval pilot

**Done:**
- Audited the merged Week 10 repository, local-data dependencies and outstanding empirical acceptance gates.
- Established a weighted baseline of 70% complete and 30% remaining across Network 2 validation, live candidate/retrieval execution, human annotation and matched-policy evaluation. The weighting is a transparent project-management estimate, not a scientific-performance metric.
- Added a Week 11 local execution runner that orchestrates pytest, corrected Network 2 validation, label-blind candidate generation, four matched-budget Europe PMC strategies, blinded annotation preparation and a separate evaluation gate.
- Added tests for candidate-audit guards, retrieval metadata, matched candidate pool, duplicate and over-budget retrieval records, annotation status and complete human evidence labels.
- Added Week 11 progress report, form entries, reproduction guide, final checklist, progress baseline JSON, SVG infographic and repository index updates.
- Kept raw Parquet, retrieved abstracts, candidate outputs, annotation worksheets and private strategy mappings local/ignored.

**Found:** the prior Week 10 extraction logs support 1,739,224 source-specific association rows and 1,633,220 overall-direct rows, both from 14 shards across 2,295 mapped targets. The corrected validator has not yet been rerun against the owner-local Parquet files. Candidate generation, live literature retrieval, manual annotation and measured policy comparison remain pending.

**Changed vs plan:** this sprint narrows the final deliverable to a small, reproducible nine-candidate pilot rather than adding new modelling scope. The broader fusion-model and formal-calibration research remains outside the immediate pilot completion gate.

**Decisions:** no fabricated scientific results. UNKNOWN remains separate from CONTRADICT; the strategy key stays private until blinded labels are frozen; pooled counter-evidence recall is limited to the retrieved candidate set.

**Open / next:** execute python scripts/week11/run_week11_pipeline.py --phase prepare on the Windows research workstation, complete the generated annotation worksheet, then run the evaluation phase and update final reports with observed counts/metrics.

**For the owner to understand:** code and CI establish that the workflow can be run; only the workstation's actual data validation, live retrieval and human evidence review can establish whether the pilot experiment was completed.

---
