# TrustDTI - Week 10 submission pack

This folder records work completed after Week 9: complete Network 2 direct-association extraction, overall-direct disease anchoring, the null-sentinel QA correction and the adaptive literature-retrieval prototype.

Contents: `Week_10_Progress_Report.md`, `WEEK10_INFOGRAPHIC.svg`, `Week_10_Form_Entries.md`, `WEEK10_REPRODUCTION_GUIDE.md`, `Network2_Extraction_Summary.json`, `Network2_Source_Distribution.csv`, `references.md`, `LOCAL_ARTIFACTS.md`.

The committed report is Markdown and the infographic is a scalable SVG master. DOCX, PDF and PNG exports are not stored in this folder; export the report/infographic only when a submission portal requires those formats. Large Parquet tables, downloaded shards, retrieved abstracts and private annotation files remain local.

Code references: [scripts/week10](../../scripts/week10/README.md), [Week 10 technical note](../../docs/stages/week10.md), [Network 2 stage note](../../docs/stages/network2.md), [Week 10 sprint plan](../../docs/plans/week10_90_percent_prototype.md).

The two association products and disease join completed locally. The null-sentinel correction is merged into `main` (PR #3); the merge commit's main-branch CI passed, and the preceding full test log reports 61 passed, 2 skipped and 1 deselected. Local data-backed validation must still be rerun. Candidate/retrieval execution and human evaluation remain pending. No retrieval improvement claim is made.
