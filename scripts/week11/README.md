# Week 11 execution utilities

The run_week11_pipeline.py script coordinates the final local run without duplicating Week 10 processing code.

## Prepare the pilot

```powershell
python scripts/week11/run_week11_pipeline.py --phase prepare
```

Defaults: seed 42, 3 candidates per state, maximum 9 candidates, 5 documents per candidate per strategy. It runs pytest, the joint Network 2 validator, candidate generation, four-arm Europe PMC retrieval and blinded annotation-sheet preparation. It stops at the first failed gate.

## Evaluate after manual annotation

Complete all rows of outputs/week10/retrieval_annotation_sheet.csv with a valid direction_label, evidence_category and annotation_rationale, then run:

```powershell
python scripts/week11/run_week11_pipeline.py --phase evaluate
```

This phase refuses to run when any annotation is incomplete or invalid.

## Inspect status

```powershell
python scripts/week11/run_week11_pipeline.py --phase status
```

The runner writes its local status to outputs/week11/week11_execution_status.json. It must not be committed with raw/processed data, retrieval abstracts or private strategy files.
