# Week 10 reproduction guide

## Environment
Repository: `C:\\Users\\91701\\code\\Trust_DTI`; Python 3.12.6; virtual environment: `.venv`.

```bash
source .venv/Scripts/activate
git fetch origin
git switch fix/network2-aggregation-null
git pull --ff-only
python -m pytest -q
```

GitHub Actions reported 61 passed, 2 skipped and 1 deselected.

## Revalidate existing local files
```bash
python scripts/week10/validate_network2.py
```
Inputs: bridge CSV, `network2_direct_associations.parquet` and `network2_overall_direct.parquet`. Output: `outputs/week10/network2_validation_audit.json`. The validator reads existing Parquet files; it does not require a re-download. Candidate generation requires `all_critical_checks_passed: true`.

## Rebuild only if missing or corrupt
```bash
python scripts/week09/build_network2_direct_associations.py
python scripts/week10/build_network2_overall_direct.py
```
These are full-data operations, not ordinary validation steps.

## Candidate, retrieval and annotation pilot
After the local validator passes:
```bash
python scripts/week10/build_candidate_set.py --per-state 3 --max-candidates 9
python scripts/week10/run_retrieval_demo.py --budget-per-candidate 5
python scripts/week10/prepare_annotation_sheet.py
```
Keep `retrieval_strategy_manifest.csv` and `retrieval_strategy_key.csv` private until blind labels are final.

Annotate each unique candidate-publication once as SUPPORT, CONTRADICT or UNKNOWN, with evidence category and rationale. Query intent is not evidence direction. UNKNOWN/missing evidence is not CONTRADICT.

Then run:
```bash
python scripts/week10/evaluate_retrieval.py --budget-per-candidate 5
```
Pooled counter-evidence recall is limited to the union of four retrieved sets for the fixed candidates, not exhaustive literature recall.
