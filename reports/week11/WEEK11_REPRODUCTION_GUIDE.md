# Week 11 reproduction guide — actual interim checkpoint

## Environment

- Repository: `C:\Users\91701\code\Trust_DTI`
- Branch at last local verification: `main`
- Main commit verified locally: `712f4a2`
- Python: 3.12.6
- Environment: `.venv`
- OS shell: Windows PowerShell

## 1. Synchronise and test

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
.venv\Scripts\Activate.ps1
python --version
python -m pytest -q
```

Recorded result: **70 passed, 1 deselected**.

## 2. Network 2 validation

```powershell
python scripts/week10/validate_network2.py `
    --bridge outputs/week09_network2/uniprot_opentargets_primary_bridge.csv `
    --source data/processed/network2_direct_associations.parquet `
    --overall data/processed/network2_overall_direct.parquet `
    --output outputs/week10/network2_validation_audit_rerun.json
```

Inspect the JSON and require `all_critical_checks_passed: true`. The recorded rerun passed 17/17 checks with zero warnings. The previous failed audit was preserved as `network2_validation_audit_pre_rerun.json`; the passing rerun was copied to `network2_validation_audit.json` because the candidate builder reads that canonical filename.

## 3. Candidate generation

```powershell
python scripts/week10/build_candidate_set.py `
    --per-state 3 `
    --seed 42 `
    --max-candidates 9
```

Inspect:

```powershell
Get-Content outputs/week10/candidate_build_audit.json
Import-Csv data/processed/week10_candidates.csv | Format-Table
```

Recorded result: 9 candidates, 3 per conformal state, seed 42, label-blind true, observed label column not used, all 9 anchors STRONG.

## 4. Preserve the initial retrieval run

Before rerunning the retrieval runner, preserve current outputs. The runner writes to fixed filenames and will overwrite them.

```powershell
Copy-Item outputs/week10/retrieval_records.jsonl outputs/week10/retrieval_records_initial.jsonl -Force
Copy-Item outputs/week10/retrieval_failures.json outputs/week10/retrieval_failures_initial.json -Force
Copy-Item outputs/week10/retrieval_run_metadata.json outputs/week10/retrieval_run_metadata_initial.json -Force
```

These initial copies were created for the recorded experiment. Do not replace them when testing new query formulations.

## 5. Initial four-arm retrieval command

```powershell
python scripts/week10/run_retrieval_demo.py --budget-per-candidate 5
```

Recorded initial result:
- 9 fixed candidates.
- 4 strategies.
- 150 allocated retrieval slots after intentional STOP allocations.
- 15 candidate–strategy–publication records.
- 2 ReadTimeout failures.
- Strategy counts: fixed 3, uncertainty-only 0, disease-only 8, combined 4.
- All returned records remained UNANNOTATED.

This first run is a baseline. The query-quality diagnostic found only disease-context records, so do not treat it as an accepted final evidence set yet.

## 6. Compound identity and query diagnostics

Local diagnostic outputs used:
- `outputs/week10/pubchem_synonym_lookup.json`
- `outputs/week10/chembl_synonym_enrichment_corrected.json`
- `outputs/week10/retrieval_synonym_probe.json`

All 9 candidate InChIKeys matched ChEMBL molecule records exactly. No preferred compound names or synonyms were returned in the queried ChEMBL fields. The 12 Europe PMC diagnostic queries across DRD2, PTH1R and IRAK4 returned zero hits.

## 7. Remaining retrieval work

Do not alter the frozen candidate set or overwrite the initial run. Test broader but controlled query formulations on a diagnostic subset, preserve the query and result provenance, and then run all four policies with the same cap against the same candidate set. Write improved outputs to a distinct run directory or versioned filenames. Record query-level hit counts, returned records and exceptions.

## 8. Annotation and evaluation

After accepting the improved retrieval set:

```powershell
python scripts/week10/prepare_annotation_sheet.py
```

Complete the annotation worksheet manually. Each unique candidate–publication pair needs:
- `evidence_category`: MECHANISTIC, DISEASE_CONTEXT, COUNTER, SAFETY or OTHER.
- `direction_label`: SUPPORT, CONTRADICT or UNKNOWN.
- `annotation_rationale`: concise explanation based on the article content.

Keep `retrieval_strategy_manifest.csv` and `retrieval_strategy_key.csv` private until the annotation sheet is frozen. Never label records from search intent alone.

Then run:

```powershell
python scripts/week11/run_week11_pipeline.py --phase evaluate
```

Inspect `outputs/week11/retrieval_policy_comparison.json`. Report actual candidate and annotation denominators. Pooled counter-evidence recall is relative to the union of CONTRADICT-labelled records retrieved for these fixed pilot candidates, not exhaustive literature recall.

## Data safety

Keep raw/processed Parquet, candidate tables, PubChem/ChEMBL lookup files, retrieved abstracts, local failures, annotation worksheets and private strategy files on the workstation. Commit only documentation, code, tests and appropriately redacted aggregate summaries.
