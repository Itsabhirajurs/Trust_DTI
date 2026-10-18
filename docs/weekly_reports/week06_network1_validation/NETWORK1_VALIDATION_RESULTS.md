# Week 6 — Network 1 Validation Results

**Date:** 18 October 2026
**Project:** TrustDTI
**Stage:** Stage 2 — Network 1 quality assurance

## Objective

Validate the local Network 1 dataset against its committed manifest and create a reusable validation script.

## Work Completed

1. Inspected the local Git status, recent commits and Python version.
2. Ran the default test suite: 9 tests passed and 1 test was deselected.
3. Created `src/network/validate_network1.py` to make dataset validation reproducible.
4. Ran the validator against `data/processed/network1_v1.parquet`.
5. Confirmed that all 13 validation checks passed.

## Results

| Check | Verified result |
|---|---|
| Dataset row count | 1,905,586; matches manifest |
| ACTIVE pairs | 748,430; matches manifest |
| INACTIVE pairs | 1,157,156; matches manifest |
| Four split distributions | All match manifest |
| Duplicate compound–protein pairs | 0 |
| Drug-cold scaffold overlaps | 0 across train, calibration and test |
| Target-cold protein overlaps | 0 across train, calibration and test |
| Temporal calibration years | Before 2020 |
| Temporal test years | 2020 onward |
| Rows without publication year | 659,861; unassigned to temporal split |
| Validator result | 13/13 checks passed |

## Interpretation and Limitations

The local dataset counts and split distributions match the committed manifest. The validation confirms separation by scaffold in the drug-cold split, separation by protein accession in the target-cold split, and the intended temporal cutoff.

The 659,861 rows without publication years are excluded from the temporal split. This reduces the data available for temporal evaluation.

These checks verify dataset consistency and selected leakage controls. They do not establish predictive accuracy, prove that every possible leakage mechanism has been eliminated, or demonstrate that a trained DTI model works.

The raw and processed datasets are excluded from Git tracking. Reproducing the checks therefore requires access to the local data files.

## Reproduction Commands

Run from the repository root:

`python -m src.network.validate_network1`

`python -m pytest -q`

The recorded validator run passed all 13 checks. The default test suite passed 9 tests, with 1 deselected.

## Next Steps

Prepare the Stage 3 GPU workflow for ChemBERTa compound embeddings and ESM-2 protein embeddings. Test suitable checkpoints and pooling strategies on a small pilot, define a reproducible embedding cache, and estimate GPU memory and runtime requirements before scaling up. Prepare classical fingerprint baselines for subsequent model evaluation.
