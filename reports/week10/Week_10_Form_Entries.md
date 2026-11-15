# Week 10 form-ready entries

Development hours are not available in the repository or terminal logs. Enter the actual hours from your personal record.

## Objective
Complete both separate Open Targets 26.09 direct protein-disease association tables for the 2,295 high-confidence mapped targets, join disease metadata, validate the outputs and connect the deterministic uncertainty-by-disease-context router to a reproducible literature-retrieval and human-evaluation workflow.

## Work completed
1. Ran all 14 `association_by_datasource_direct` shards: 7,522,466 inputs; 1,739,224 retained datasource-level records; 2,295 mapped targets; 21,268 disease IDs.
2. Ran all 14 `association_overall_direct` shards: 7,225,847 inputs; 1,633,220 retained overall-direct records; all 2,295 targets and 21,268 disease IDs represented.
3. Joined 45,896 disease metadata records; the build audit reported zero unmatched association rows.
4. Diagnosed the joint-validator failure: overall `aggregationValue` stored the string `None`; fixed builder and validator handling.
5. Added regression tests for `None`, `null`, blank and `<NULL>`. CI reported 61 passed, 2 skipped, 1 deselected.
6. Implemented/tested the deterministic seven-policy router, Europe PMC retrieval with provenance and failure handling, four matched-budget arms, blinded annotation preparation and evaluator.
7. Prepared Week 10 documentation and reorganized the root-level Week 9 audit scripts under `scripts/week09/`.

## Results
- Source-specific output: 1,739,224 rows; zero duplicate target-disease-source keys.
- Overall-direct output: 1,633,220 rows; zero duplicate target-disease keys; zero unmatched disease metadata.
- Overall association score range: 0.0-0.9138468742.
- Largest source groups: Europe PMC 752,854; IMPC 680,209; GWAS Credible Sets 165,102; Clinical Precedence 56,902; Cancer Gene Census 33,961.
- CI: 61 passed, 2 skipped, 1 deselected.

## Challenge and resolution
The first joint validator run passed 16 of 17 checks. The failed check was caused by a stringified null sentinel in `aggregationValue`. Code and regression tests now pass CI. Local data-backed validation still needs to be rerun.

## Learning outcome
Source-specific and overall-direct association datasets serve different purposes and must remain separate. Neither association score is causal proof. Search intent does not determine evidence direction; human annotations must use SUPPORT, CONTRADICT or UNKNOWN.

## Pending
Rerun local Network 2 validation, build the candidate set, run four Europe PMC strategies at matched budget, annotate the blinded publication set and evaluate the four arms. Do not claim retrieval improvement before that evaluation.
