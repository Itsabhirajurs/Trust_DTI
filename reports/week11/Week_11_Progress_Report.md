# TrustDTI — Week 11 Progress Report

## Final end-to-end prototype completion sprint

**Milestone:** Course Week 11  
**Reporting date:** 18 November 2026  
**Execution window:** 16–22 November 2026  
**Starting progress estimate:** 70% complete; 30% remaining  
**Status at report creation:** Final sprint planned; local data-backed execution and human evaluation have not yet been evidenced in this environment.

> This is the Week 11 sprint baseline, not a claim that the final local experiment has already run. Replace the pending fields with actual run evidence after executing the local pipeline.

## 1. Executive summary

Week 10 completed the main engineering implementation: both separate Open Targets 26.09 direct-association products were extracted locally; the disease metadata join was completed; a stringified-null handling defect was corrected; the deterministic router, Europe PMC retrieval client, four matched-policy arms, blinded annotation preparation and evaluator were added and covered by automated tests. The Week 10 correction is merged into main.

The remaining work is empirical and owner-local. The first joint Network 2 validation audit passed 16 of 17 checks before the null-sentinel correction. The corrected validator must be rerun against the original local Parquet tables. Only after it passes can the candidate set and live literature experiment proceed.

Week 11 therefore focuses on four remaining gates:

1. Revalidate the two local Network 2 tables and bridge.
2. Build a fixed, label-blind pilot of up to nine drug–protein candidates and run four Europe PMC retrieval strategies at five documents per candidate.
3. Complete blinded human evidence annotations.
4. Evaluate the four policies on the same candidate set and report measured results and limitations.

## 2. Starting progress estimate

The 70% estimate uses the explicit workstream weights in WEEK11_PROGRESS_BASELINE.json:

| Workstream | Weight | Completed | Remaining |
|---|---:|---:|---:|
| Data foundation, Network 1 and classical baseline | 20 | 20 | 0 |
| Network 2 mapping and both 14-shard extractions | 25 | 25 | 0 |
| Joint Network 2 data-backed validation | 10 | 5 | 5 |
| Router, retrieval client, four strategies, annotation/evaluator implementation | 20 | 20 | 0 |
| Actual fixed-candidate and live retrieval run | 10 | 0 | 10 |
| Human evidence annotations | 10 | 0 | 10 |
| Matched-policy evaluation and final results | 5 | 0 | 5 |
| **Total** | **100** | **70** | **30** |

This estimate measures completion of the defined pilot workflow. It does not mean the broader research programme is scientifically finished: full ChemBERTa/ESM-2 embedding caches, a fusion model, formal calibration analysis, larger evaluation and sealed retrospective validation remain outside this final pilot sprint.

## 3. Week 11 objectives

### 3.1 Local Network 2 validation

Run scripts/week10/validate_network2.py against:
- outputs/week09_network2/uniprot_opentargets_primary_bridge.csv
- data/processed/network2_direct_associations.parquet
- data/processed/network2_overall_direct.parquet

Acceptance: all_critical_checks_passed is true, with checks covering bridge uniqueness, identifier consistency, aggregation types, release, provenance, key uniqueness, null sentinels, named disease coverage and score bounds.

### 3.2 Fixed candidate set

Use the saved random-split baseline prediction file and the validated Network 2 anchor table. Exclude observed DTI labels before candidate selection. Use seed 42, three candidates per prediction state and a maximum of nine candidates.

Acceptance: non-empty candidate CSV; candidate audit confirms label_blind_selection is true and true_label_column_used is false; count does not exceed nine.

### 3.3 Live Europe PMC retrieval

Run the fixed, uncertainty-only, disease-only and combined strategies on the same candidate set, with a maximum five retrieved documents per candidate per strategy. Keep the retrieval query, publication identifier, source URL and retrieval timestamp.

Acceptance: non-empty retrieval record file, run metadata confirms the same candidate count and five-document cap, and retrieval failures are recorded rather than silently discarded.

### 3.4 Blinded annotation

Prepare one worksheet row per unique candidate-publication pair. Keep retrieval_strategy_manifest.csv and retrieval_strategy_key.csv private until annotations are frozen.

Each row requires:
- Evidence category: MECHANISTIC, DISEASE_CONTEXT, COUNTER, SAFETY or OTHER.
- Direction: SUPPORT, CONTRADICT or UNKNOWN.
- A concise rationale grounded in the publication content.

UNKNOWN is not CONTRADICT; absence of evidence is not negative evidence. A query intent does not determine the evidence direction.

### 3.5 Matched-policy evaluation

After annotation is complete, evaluate all four strategies at the same per-candidate budget. Report retrieved records, candidate coverage, annotation coverage, relevant-evidence precision, SUPPORT / CONTRADICT / UNKNOWN counts, counter-evidence share and pooled candidate-set counter-evidence recall.

The pooled recall denominator is the union of CONTRADICT-labelled publications retrieved by the four arms for these fixed candidates. It is not exhaustive recall over all published literature.

## 4. Execution record

Fill this section only after running the local workflow.

| Gate | Required evidence | Result |
|---|---|---|
| Automated tests | pytest output | Pending |
| Network 2 validation | network2_validation_audit.json, all critical checks true | Pending |
| Candidate generation | Candidate CSV + candidate_build_audit.json | Pending |
| Europe PMC retrieval | Records JSONL + failures + run metadata | Pending |
| Blinded annotation | Completed annotation sheet; private key/manifest retained | Pending |
| Matched-policy evaluation | retrieval_policy_comparison.json | Pending |
| Final review | Metrics, caveats and reproducibility checked | Pending |

## 5. Tooling

Python 3.12.6, pandas, PyArrow, Requests, pytest, Open Targets Platform 26.09, Europe PMC REST API, PubChem PUG REST for compound-name resolution, Git, GitHub and GitHub Actions.

## 6. Risks and controls

- **Missing local files:** restore the original ignored Parquet and baseline prediction files; do not download/rebuild multi-gigabyte inputs unless necessary.
- **Network/API limits:** keep the pilot small, preserve retries/failure logs and rerun only failed queries where possible.
- **Candidate imbalance:** retain state counts in the candidate audit; report actual counts rather than implying every state has three valid candidates.
- **Blinding leakage:** do not expose the private strategy key or manifest before labels are frozen.
- **Annotation uncertainty:** retain UNKNOWN and record rationale; do not convert it to CONTRADICT.
- **Overclaiming:** do not claim strategy superiority from a small pilot or from pooled candidate-set recall as if it were exhaustive literature recall.

## 7. Week 11 final acceptance criteria

The engineering pilot is complete when the local validation passes, all four strategy runs are recorded against one fixed candidate set, the unique returned publications are annotated, and the evaluator emits metrics for all four arms with no missing annotations.

The scientific question remains open unless the measured results, sample size, uncertainty, annotation process and limitations support a defensible conclusion.

## 8. Next actions

1. Pull the latest main and activate the existing Python environment.
2. Run the Week 11 preparation runner and preserve its local execution status file.
3. Review the generated blinded worksheet and annotate every unique record.
4. Run the evaluation phase; inspect all four strategy metrics.
5. Update this report, the form entries and progress infographic with actual results only.
