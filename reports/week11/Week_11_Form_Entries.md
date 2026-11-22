# Week 11 — form-ready progress entries

**Reporting date:** 22 November 2026  
**Reporting status:** Interim progress entry. Human annotation and final evaluation remain incomplete.

## Tasks & Work Completed During This Week

Synchronised the local TrustDTI repository with the latest merged main branch and backed up local Week 9/10 outputs. Verified the updated Python environment and ran the local test suite (70 passed, 1 deselected). Re-ran joint Network 2 validation against the original local association Parquet files and UniProt–Ensembl bridge; all 17 critical checks passed with zero warnings. Generated a fixed, label-blind nine-candidate set using seed 42, with three candidates per conformal prediction state and STRONG Network 2 anchors. Executed the first live Europe PMC retrieval run using fixed, uncertainty-only, disease-only and combined strategies with a five-document per-candidate cap. The run returned 15 candidate–strategy–publication records and logged two request timeouts. Audited publication metadata, router budget allocations and strategy coverage. Verified exact ChEMBL InChIKey matches for all nine candidate compounds and tested 12 Europe PMC query variants with synonym expansion on/off; all 12 returned zero hits. Preserved the initial retrieval run and documented its limitations.

## Roadblocks & Challenges Encountered

The initial live retrieval run had low coverage: 15 candidate-strategy records across the four policies, with no records returned by uncertainty-only and all returned records attached to disease-context intent. Two Europe PMC requests timed out. The current exact chemical-name and ChEMBL-ID title/abstract queries returned zero hits in a separate 12-query synonym diagnostic. ChEMBL structure records matched all nine candidate InChIKeys but did not provide preferred names or synonyms in the fields returned. The literature-query design therefore needs further refinement before human annotation and a meaningful matched-policy evaluation can proceed.

## Plan & Roadmap for Next Week

Improve and validate drug–target literature query construction using the verified compound identifiers and carefully controlled alias/target-term variants. Preserve the first 15-record retrieval experiment as the baseline and run improved retrieval into separate, versioned outputs. Review the retrieved evidence set, prepare the blinded annotation sheet, manually label each unique candidate–publication pair using SUPPORT / CONTRADICT / UNKNOWN and a short rationale, freeze annotations before unblinding, and run the matched-budget evaluator. Update the report and infographic with measured evaluation metrics only after the annotation and evaluator gates pass.

## Technologies / Tools Used

Python 3.12.6; pandas 3.0.6; PyArrow 25.0.1; scikit-learn 1.9.1; pytest; Parquet; Open Targets Platform 26.09; Europe PMC REST API; PubChem PUG REST; ChEMBL REST API; requests; deterministic retrieval router; PowerShell; Git; GitHub; GitHub Actions.

## Development Hours Invested

Enter the actual Week 11 hours from your own time record. This report does not infer or invent a duration from command timestamps.

## Key Learning Outcome

A working retrieval client does not guarantee useful literature coverage. Exact chemical/IUPAC names and database identifiers can be too restrictive when used as quoted title/abstract terms. The retrieval pipeline must preserve compound identity and provenance, report empty queries and technical failures, and distinguish the absence of a search result from biological counter-evidence. A valid evaluation still requires a fixed candidate set, matched policy budgets, blinded human evidence-direction labels and a clearly defined denominator.

## GitHub Repository / Commit URL

Repository: https://github.com/Itsabhirajurs/Trust_DTI

Week 11 reporting branch: https://github.com/Itsabhirajurs/Trust_DTI/tree/docs/week11-actual-progress

## Supporting Documents

Week 11 report pack: https://github.com/Itsabhirajurs/Trust_DTI/tree/docs/week11-actual-progress/reports/week11

Progress report: https://github.com/Itsabhirajurs/Trust_DTI/blob/docs/week11-actual-progress/reports/week11/Week_11_Progress_Report.md

SVG infographic: https://github.com/Itsabhirajurs/Trust_DTI/blob/docs/week11-actual-progress/reports/week11/WEEK11_INFOGRAPHIC.svg

Retrieval diagnostics: https://github.com/Itsabhirajurs/Trust_DTI/blob/docs/week11-actual-progress/reports/week11/WEEK11_RETRIEVAL_DIAGNOSTICS.md

## Submission note

This is an interim progress entry, not a final-project completion declaration. Human annotation, matched-policy evaluation and query-quality improvements remain outstanding.
