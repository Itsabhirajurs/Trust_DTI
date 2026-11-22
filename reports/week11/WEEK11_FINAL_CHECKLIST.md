# Week 11 completion checklist — evidence checkpoint 22 November 2026

Use this checklist on the Windows research workstation. A gate is complete only when its specified output exists and has been checked. This checklist intentionally distinguishes passed gates from partial or pending research work.

## Gate 0 — repository, environment and tests

- [x] Back up local Week 9 and Week 10 outputs outside the repository.
- [x] Switch to main and fast-forward from origin/main.
- [x] Verify Python 3.12.6 and the principal data-science packages.
- [x] Run `python -m pytest -q`: 70 passed, 1 deselected.

**Status: PASSED**

## Gate 1 — Network 2 data validation

- [x] Run `scripts/week10/validate_network2.py` on the actual local bridge and Parquet tables.
- [x] Preserve the earlier failed audit separately.
- [x] Copy the passing rerun to the canonical candidate-builder audit path.
- [x] Confirm all 17 critical checks are true.
- [x] Confirm zero mapping mismatches, duplicate keys, missing disease names, missing source IDs, out-of-range scores and non-empty overall aggregation values.
- [x] Confirm zero warnings.

**Status: PASSED — 17/17 checks**

## Gate 2 — fixed candidate set

- [x] Run candidate builder with `--per-state 3 --seed 42 --max-candidates 9`.
- [x] Confirm 9 candidates: 3 ACTIVE_ONLY, 3 INACTIVE_ONLY and 3 UNCERTAIN.
- [x] Confirm label-blind selection true and observed DTI label column not used.
- [x] Confirm candidate IDs are unique.
- [x] Record that all 9 candidates received STRONG anchor tier.
- [x] Perform PubChem/ChEMBL identity follow-up; exact ChEMBL InChIKey matches found for 9/9.

**Status: PASSED**

## Gate 3 — initial live literature retrieval

- [x] Run all four strategies on the same nine-candidate set, cap 5 per candidate.
- [x] Preserve the initial JSONL, failures and metadata before further experiments.
- [x] Record router allocations: fixed 45, uncertainty-only 30, disease-only 45, combined 30 (150 total policy slots).
- [x] Record initial retrieval: 15 candidate–strategy–publication records.
- [x] Record two 45-second ReadTimeout failures.
- [x] Verify titles, abstracts and record identifiers present for all 15 records.
- [x] Verify all 15 records remain UNANNOTATED.
- [ ] Improve query construction and rerun the four arms into separate/versioned outputs.
- [ ] Demonstrate useful coverage beyond disease-context-only results.
- [ ] Inspect and resolve technical failures where possible.

**Status: PARTIAL — retrieval-quality work remains**

## Gate 4 — blinded human annotation

- [ ] Prepare the annotation sheet from the accepted retrieval run.
- [ ] Keep `retrieval_strategy_manifest.csv` and `retrieval_strategy_key.csv` private.
- [ ] For each unique candidate–publication pair, assign an allowed evidence category.
- [ ] For each unique pair, choose SUPPORT, CONTRADICT or UNKNOWN from article content.
- [ ] Enter a short publication-grounded rationale for every row.
- [ ] Resolve ambiguity as UNKNOWN rather than guessing.
- [ ] Freeze the worksheet before unblinding the strategy key.

**Status: PENDING**

## Gate 5 — matched-policy evaluation

- [ ] Ensure annotation completeness and validity.
- [ ] Run `python scripts/week11/run_week11_pipeline.py --phase evaluate` or the documented evaluator command.
- [ ] Inspect `outputs/week11/retrieval_policy_comparison.json`.
- [ ] Compare actual records, candidate coverage, annotation completeness, evidence counts and relevant-evidence precision.
- [ ] Verify denominators for pooled candidate-set counter-evidence recall.
- [ ] Do not describe candidate-set pooled recall as exhaustive literature recall.

**Status: PENDING**

## Gate 6 — final report and submission

- [x] Create an interim Week 11 report, form entries, SVG infographic, activity log, diagnostic note, aggregate evidence JSON and updated status snapshot.
- [ ] Update the interim report with improved retrieval and final human-evaluation results.
- [ ] Enter actual development hours in the form.
- [ ] Update progress percentage only from the agreed weighted workstream evidence.
- [ ] Confirm final documentation and repository links.
- [ ] Clearly disclose incomplete scientific work and limitations.

**Status: INTERIM DOCUMENTATION PREPARED; FINAL CLOSE-OUT PENDING**

## Completion rule

The current project-management estimate is **80%**. The pilot is not 100% complete. It reaches final pilot completion only after retrieval-quality work is accepted, every unique candidate–publication record is human-annotated, the four-arm evaluator runs successfully and the final denominators/limitations are reviewed. A passing CI run, a passing data validator or a prepared worksheet alone does not close those later gates.
