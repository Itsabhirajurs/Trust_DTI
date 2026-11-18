# Week 11 final reproduction guide

## Environment

Repository: C:\Users\91701\code\Trust_DTI  
Python: 3.12.6  
Environment: .venv

Synchronise the Week 11 branch after it is merged into main, or switch to the feature branch while testing:

§§§powershell
git fetch origin
git switch work/week11-final-completion
git pull --ff-only
.venv\Scripts\Activate.ps1
python -m pytest -q
§§§

## Recommended one-command preparation

§§§powershell
python scripts/week11/run_week11_pipeline.py --phase prepare
§§§

Defaults: seed 42, three candidates per prediction state, maximum nine candidates, five documents per candidate per strategy.

The runner performs:
1. Fast pytest suite.
2. Local Network 2 validation; stops unless all critical checks pass.
3. Label-blind candidate generation and candidate-audit verification.
4. Four Europe PMC retrieval strategies at the same per-candidate cap.
5. Blinded annotation-sheet generation and verification.

Status is written locally to outputs/week11/week11_execution_status.json.

## Manual human annotation

Open outputs/week10/retrieval_annotation_sheet.csv. For every unique candidate-publication, complete:
- evidence_category: MECHANISTIC, DISEASE_CONTEXT, COUNTER, SAFETY or OTHER.
- direction_label: SUPPORT, CONTRADICT or UNKNOWN.
- annotation_rationale: short explanation based on article content.

Do not expose retrieval_strategy_manifest.csv or retrieval_strategy_key.csv until the annotation sheet is frozen. The strategy mapping is intentionally private to preserve blinding.

## Evaluate after annotation is complete

§§§powershell
python scripts/week11/run_week11_pipeline.py --phase evaluate
§§§

The runner checks that every row has a valid evidence direction, category and rationale before invoking the evaluator. The result is written to outputs/week11/retrieval_policy_comparison.json; a local execution status is also updated.

## Inspect progress

§§§powershell
python scripts/week11/run_week11_pipeline.py --phase status
§§§

This reads local run artifacts and does not rerun data processing or make network requests.

## Direct script alternative

Each existing Week 10 script remains independently executable. See scripts/week10/README.md.

## Data safety

Do not push raw/processed Parquet tables, PubChem caches, retrieved abstracts, annotation sheets or private strategy files to GitHub. Keep all local data and human annotations on the research workstation. Commit only source code, tests, documentation and appropriately redacted aggregate metrics.
