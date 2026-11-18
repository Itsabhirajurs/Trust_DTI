# TrustDTI — Week 11 final completion sprint

Week 11 is the final planned sprint to turn the Week 10 Network 2 and adaptive-retrieval implementation into a data-backed, reproducible pilot. This folder records the starting position, execution gates, reproducibility steps and final reporting templates.

## Starting point (18 November 2026)

The weighted end-to-end prototype estimate is **70% complete; 30% remains**. This is a project-management estimate, not a model-performance or scientific-validity score.

| Workstream | Weight | Starting completion |
|---|---:|---:|
| Data foundation, Network 1 and classical baseline | 20 | 20 |
| Network 2 bridge and both 14-shard extractions | 25 | 25 |
| Joint Network 2 data-backed validation | 10 | 5 |
| Router, Europe PMC client, four strategies, annotation/evaluator code | 20 | 20 |
| Actual fixed-candidate and live retrieval run | 10 | 0 |
| Human evidence annotations | 10 | 0 |
| Matched-policy evaluation and final results | 5 | 0 |
| **Total** | **100** | **70** |

## Contents

- *Week_11_Progress_Report.md* — Week 11 baseline and final-report structure
- *Week_11_Form_Entries.md* — form-ready milestone entries
- *WEEK11_FINAL_CHECKLIST.md* — acceptance gates and owner actions
- *WEEK11_REPRODUCTION_GUIDE.md* — final local run commands
- *WEEK11_PROGRESS_BASELINE.json* — explicit weighting behind the 70% estimate
- *WEEK11_INFOGRAPHIC.svg* — sprint progress infographic

## One-command preparation runner

After synchronising main and activating the project environment:

```powershell
python scripts/week11/run_week11_pipeline.py --phase prepare
```

The runner executes the test suite, data-backed Network 2 validation, fixed label-blind candidate generation (up to nine candidates), four matched-budget Europe PMC retrieval strategies (five documents per candidate) and blinded annotation-sheet creation. It stops at the first failed gate and writes a local status file to outputs/week11/week11_execution_status.json.

After a human has completed every annotation row:

```powershell
python scripts/week11/run_week11_pipeline.py --phase evaluate
```

The evaluator gate requires a valid SUPPORT / CONTRADICT / UNKNOWN label, evidence category and rationale on every row. It does not manufacture annotations.

To inspect local progress without rerunning the pipeline:

```powershell
python scripts/week11/run_week11_pipeline.py --phase status
```

## Important boundaries

The Parquet datasets, candidate table, retrieved abstracts, annotation worksheet and private strategy manifest/key remain on the workstation and are not committed. Never share the private strategy manifest/key before the blind annotations are frozen.

A green CI test suite is not a substitute for local Parquet validation. A completed retrieval run is not a completed human evaluation. Counter-evidence recall is only relative to the pooled publications retrieved for the fixed pilot candidates, not the whole literature.

## Related implementation

- [Week 10 code](../../scripts/week10/README.md)
- [Week 10 results and methods](../week10/README.md)
- [Week 11 execution runner](../../scripts/week11/README.md)
- [Week 11 final sprint plan](../../docs/plans/week11_final_completion.md)
