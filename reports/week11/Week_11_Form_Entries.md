# Week 11 — form-ready progress entries

**Notice:** These are Week 11 starting-sprint entries. Do not submit the planned/live-execution statements as completed work until the corresponding local run evidence exists.

## Tasks & Work Completed During This Week

Started the final TrustDTI prototype-completion sprint by auditing the merged Week 10 repository, defining measurable acceptance gates for local Network 2 validation, fixed-candidate generation, live Europe PMC retrieval, blinded annotation and matched-policy evaluation. Added a Week 11 execution runner that orchestrates the tests and local data pipeline in sequence, records gate outcomes and stops on failed prerequisites. The runner requires all annotations to be completed manually with a direction label, evidence category and rationale before evaluation.

**After execution, add:** actual Network 2 validation result, number of candidates created, number of publications retrieved, number of retrieval failures, number of unique annotation rows and final evaluation result.

## Roadblocks & Challenges Encountered

The primary blocker is that the Network 2 Parquet datasets, baseline prediction files and retrieval outputs are local-only and are not stored in GitHub. The merged Week 10 CI run validates code/tests but cannot substitute for executing the corrected validator against the local datasets. The live retrieval and human annotation stages also require API access and evidence review on the research workstation.

## Plan & Roadmap for Next Week

This is the final planned sprint. Complete the local Network 2 validation, build a reproducible fixed candidate set of up to nine candidates, run all four Europe PMC retrieval strategies with a matched cap of five documents per candidate, complete blinded human annotation and generate the four-arm comparison. Update the final report and progress dashboard from actual execution outputs. If a gate fails, document the failure and do not report downstream stages as complete.

## Technologies / Tools Used

Python 3.12.6; pandas; PyArrow; Parquet; pytest; Open Targets Platform 26.09; Europe PMC REST API; PubChem PUG REST; deterministic retrieval routing; Git; GitHub; GitHub Actions; Windows PowerShell.

## Development Hours Invested

Enter actual Week 11 development hours from the workstation/time record. Do not estimate or copy Week 10 hours.

## Key Learning Outcome

A reproducible evidence-retrieval experiment requires more than a working API client and routing code. It requires validated biological identifier joins, one fixed label-blind candidate pool, an identical document budget across retrieval policies, publication-level blinded annotation and a clearly defined evaluation denominator. Automated tests verify implementation behaviour; local data validation and human evidence adjudication are separate scientific gates.

## GitHub Repository / Commit URL

Repository: https://github.com/Itsabhirajurs/Trust_DTI

Week 11 sprint branch: https://github.com/Itsabhirajurs/Trust_DTI/tree/work/week11-final-completion

## Supporting Document / Demo Link

Week 11 sprint pack: https://github.com/Itsabhirajurs/Trust_DTI/tree/work/week11-final-completion/reports/week11

Week 11 execution guide: https://github.com/Itsabhirajurs/Trust_DTI/blob/work/week11-final-completion/reports/week11/WEEK11_REPRODUCTION_GUIDE.md

Week 11 technical runner: https://github.com/Itsabhirajurs/Trust_DTI/blob/work/week11-final-completion/scripts/week11/run_week11_pipeline.py

Week 10 technical baseline: https://github.com/Itsabhirajurs/Trust_DTI/blob/main/reports/week10/Week_10_Progress_Report.md
