# TrustDTI — Week 11 activity log

**Reporting date:** 22 November 2026  
**Evidence period:** 21–22 November 2026  
**Source:** terminal outputs provided during the guided local execution session.

## 21 November 2026 — repository and environment

- Created a local backup of `outputs/week09_network2` and `outputs/week10` at `C:\Users\91701\code\Trust_DTI_local_outputs_backup_20261121_205036`.
- Fast-forwarded local `main` from commit `0450518` to `712f4a2`.
- Verified Python 3.12.6, pandas 3.0.6, PyArrow 25.0.1 and scikit-learn 1.9.1.
- Ran the updated test suite: 70 passed, 1 deselected.

## 21 November 2026 — Network 2 validation

- Executed the corrected joint validator against the local bridge, source-specific association table and overall-direct association table.
- Saved a fresh audit as `outputs/week10/network2_validation_audit_rerun.json`.
- Verified all 17 critical checks true, zero warnings, zero mapping mismatches, zero duplicate keys and zero missing disease metadata.
- Preserved the earlier failed audit as `network2_validation_audit_pre_rerun.json` and installed the passing rerun as the canonical `network2_validation_audit.json` candidate-builder gate.

## 21 November 2026 — candidate generation

- Built the fixed candidate pool using seed 42, three per conformal state and maximum nine.
- Produced nine candidates: three ACTIVE_ONLY, three INACTIVE_ONLY and three UNCERTAIN.
- Confirmed label-blind selection and no use of the observed DTI label column.
- All nine candidates were assigned STRONG anchor tier.

## 21 November 2026 — initial live retrieval

- Ran the fixed, uncertainty-only, disease-only and combined Europe PMC policies at a five-document per-candidate cap.
- The router allocated 150 policy slots after intended STOP allocations.
- Retrieved 15 candidate–strategy–publication records: fixed 3, uncertainty-only 0, disease-only 8 and combined 4.
- Recorded two ReadTimeout failures after 45 seconds.
- Inspected all returned records: titles, abstracts and identifiers were present; all remained UNANNOTATED.
- Preserved the initial JSONL, failures and metadata before continuing diagnostics.

## 21–22 November 2026 — retrieval and compound diagnostics

- Audited candidate-specific router allocations and strategy coverage.
- Retrieved PubChem synonyms: eight HTTP 200 responses and one HTTP 404.
- Corrected the ChEMBL response parser after identifying that the molecule fields are returned at the top level, not necessarily under a nested `molecule` field.
- Verified exact ChEMBL InChIKey matches for all nine candidates. No preferred names or molecule synonyms were returned in the queried fields.
- Tested 12 Europe PMC diagnostic queries (three representative targets, chemical name/ChEMBL ID query forms, synonym expansion off/on). All 12 returned zero hits.
- Decision: retain the first retrieval experiment as the baseline, do not interpret zero results as counter-evidence, and improve query construction before annotation.

## Current open tasks

- Query refinement and a new versioned four-arm retrieval experiment.
- Blinded manual annotation of each unique candidate–publication pair.
- Matched-budget evaluation and final interpretation.
- Enter actual Week 11 development hours in the course form; no hours are inferred from terminal timestamps.
