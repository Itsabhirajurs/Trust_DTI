# TrustDTI - Week 10 submission pack

This folder records work completed after Week 9: complete Network 2 direct-association extraction, overall-direct disease anchoring, the null-sentinel QA correction and the adaptive literature-retrieval prototype.

Contents: `Week_10_Progress_Report.md`, `WEEK10_INFOGRAPHIC.svg`, `Week_10_Form_Entries.md`, `WEEK10_REPRODUCTION_GUIDE.md`, `Network2_Extraction_Summary.json`, `Network2_Source_Distribution.csv`, `references.md`, `LOCAL_ARTIFACTS.md`.

The editable DOCX, PDF and PNG infographic are included in the Week 10 downloadable submission pack. Large Parquet tables, downloaded shards, retrieved abstracts and private annotation files remain local.

Code references: [scripts/week10](../../scripts/week10/README.md), [Week 10 technical note](../../docs/stages/week10.md), [Network 2 stage note](../../docs/stages/network2.md), [Week 10 sprint plan](../../docs/plans/week10_90_percent_prototype.md).

The two association products and disease join completed locally. The first joint validator found a stringified `None` null sentinel; code/tests pass CI (61 passed, 2 skipped, 1 deselected), but local data-backed validation must be rerun. Candidate/retrieval execution and human evaluation remain pending. No retrieval improvement claim is made.
