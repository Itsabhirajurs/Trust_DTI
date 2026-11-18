# Week 11 final completion checklist

Use this checklist on the Windows research workstation. A box is complete only after the output exists and has been checked.

## Gate 0 — synchronise and test

- [ ] git fetch origin
- [ ] git switch main
- [ ] git pull --ff-only origin main
- [ ] git switch main
- [ ] git pull --ff-only origin main
- [ ] Activate .venv and run python -m pytest -q
- [ ] Confirm all required local inputs exist; do not commit them

## Gate 1 — Network 2 data validation (5% remaining)

- [ ] Run python scripts/week10/validate_network2.py
- [ ] Inspect outputs/week10/network2_validation_audit.json
- [ ] Confirm all_critical_checks_passed: true
- [ ] Confirm no mapping mismatches, duplicate keys, wrong release/provenance, nonempty overall aggregationValue or out-of-range scores

## Gate 2 — candidate set (part of 10% live-execution work)

- [ ] Run python scripts/week10/build_candidate_set.py --per-state 3 --seed 42 --max-candidates 9
- [ ] Inspect outputs/week10/candidate_build_audit.json
- [ ] Confirm candidate count is non-zero and at most nine
- [ ] Confirm label_blind_selection: true and true_label_column_used: false
- [ ] Review unresolved PubChem name lookups; compound IDs remain preserved if a title is not found

## Gate 3 — live retrieval (part of 10% live-execution work)

- [ ] Run python scripts/week10/run_retrieval_demo.py --budget-per-candidate 5
- [ ] Inspect outputs/week10/retrieval_run_metadata.json
- [ ] Inspect outputs/week10/retrieval_failures.json
- [ ] Confirm records are non-empty and all four strategies used the same candidate set and budget
- [ ] Preserve the raw JSONL locally; do not commit abstracts

## Gate 4 — blinded human annotation (10%)

- [ ] Run python scripts/week10/prepare_annotation_sheet.py
- [ ] Keep retrieval_strategy_manifest.csv and retrieval_strategy_key.csv private
- [ ] For every unique candidate-publication, set an allowed evidence category
- [ ] For every unique candidate-publication, choose SUPPORT, CONTRADICT or UNKNOWN based on article content
- [ ] Enter a short rationale for every label
- [ ] Resolve ambiguous records as UNKNOWN rather than guessing
- [ ] Freeze the worksheet before unblinding the strategy key

## Gate 5 — matched-policy evaluation (5%)

- [ ] Run python scripts/week10/evaluate_retrieval.py --budget-per-candidate 5 after all annotations are complete, or use python scripts/week11/run_week11_pipeline.py --phase evaluate
- [ ] Inspect outputs/week11/retrieval_policy_comparison.json
- [ ] Compare relevant-evidence precision, annotation coverage, counter-evidence share and pooled candidate-set counter-evidence recall
- [ ] Verify actual candidate and annotation denominators
- [ ] Do not describe pooled candidate-set counter-evidence recall as exhaustive literature recall

## Gate 6 — final report and submission

- [ ] Update Week_11_Progress_Report.md with observed counts and dates
- [ ] Update the Week 11 form entries; enter actual development hours
- [ ] Update infographic and progress percentage from the evidence
- [ ] Add links to the final report and exact merge commit
- [ ] Clearly state any incomplete scientific work and limitations

## Completion rule

The final pilot is **100% complete only when Gates 1–6 are evidenced**. A CI green check alone does not close Gate 1. A prepared worksheet does not close Gate 4. A report written in advance does not close any execution gate.
