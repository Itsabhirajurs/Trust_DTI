# TrustDTI — Week 11 progress and evidence pack

**Reporting snapshot:** 22 November 2026  
**Status:** Interim evidence-backed progress report; literature retrieval quality, human annotation and matched-policy evaluation remain open.

Week 11 moved the project from a planned local pilot to actual data-backed execution. The corrected Network 2 validation passed all 17 checks; a fixed, label-blind nine-candidate set was generated; and the first live four-strategy Europe PMC run produced 15 candidate–strategy–publication records. Follow-up compound-identity and synonym-query diagnostics were completed. The first retrieval run has low coverage and only disease-context records, so it is not yet suitable for claiming a retrieval-policy benefit.

## Contents

- [Week 11 progress report](Week_11_Progress_Report.md) — detailed measured results, interpretation and limitations
- [Week 11 form entries](Week_11_Form_Entries.md) — copy-ready course progress form responses
- [Week 11 activity log](Week_11_Activity_Log.md) — dated sequence of work and decisions
- [Retrieval diagnostics](WEEK11_RETRIEVAL_DIAGNOSTICS.md) — query coverage, failures, compound identity and synonym probe
- [Execution evidence JSON](WEEK11_EXECUTION_EVIDENCE.json) — sanitised machine-readable aggregate results
- [Final checklist](WEEK11_FINAL_CHECKLIST.md) — verified gates and remaining owner actions
- [Reproduction guide](WEEK11_REPRODUCTION_GUIDE.md) — Windows PowerShell commands and data-safety rules
- [Progress baseline JSON](WEEK11_PROGRESS_BASELINE.json) — preserves the original 70% starting estimate from 18 November
- [Current progress snapshot](WEEK11_PROGRESS_SNAPSHOT.json) — current 80% evidence-backed estimate and interim metrics
- [SVG infographic](WEEK11_INFOGRAPHIC.svg) — editable, scalable progress visual

## Current measured position

| Gate | Current evidence | Status |
|---|---|---|
| Local tests | 70 passed, 1 deselected | Passed |
| Network 2 validation | 17/17 critical checks true; zero warnings | Passed |
| Candidate set | 9 label-blind candidates; 3 in each prediction state | Passed |
| Initial live retrieval | 15 records across the four arms; 2 timeouts | Executed; quality diagnosis open |
| Compound identity | 9/9 exact ChEMBL InChIKey matches | Passed |
| Europe PMC synonym probe | 12/12 diagnostic queries returned zero hits | Query approach unresolved |
| Human annotation | No records manually labelled yet | Pending |
| Matched-policy evaluation | Not run | Pending |

The weighted project-management estimate is **80% complete** (20% remains). This is a planning estimate for the defined engineering-plus-pilot workflow, not a model-performance score or a claim that the scientific question has been answered.

## Local-only artefacts

The following are expected to remain on the research workstation and are not committed here: Parquet tables, candidate CSV, raw retrieval JSONL and abstracts, retrieval failures, PubChem/ChEMBL lookup outputs, annotation worksheet, private strategy manifest/key and any local execution status file. The committed JSON evidence snapshot contains only aggregate counts and validation summaries.

## Next steps

1. Diagnose and improve drug/target query construction without changing the frozen candidate set or the recorded initial experiment.
2. Re-run the retrieval policies with a preserved, versioned run output; inspect whether mechanistic and counter-evidence queries return records.
3. Prepare the blinded annotation sheet only after the retrieval set is accepted; keep the strategy manifest/key private.
4. Manually annotate every unique candidate–publication pair using SUPPORT, CONTRADICT or UNKNOWN, an evidence category and a rationale.
5. Run the matched-budget evaluator and update the report with actual metrics and denominators.

## Scientific safeguards

- An empty query result is not negative biological evidence.
- A retrieval intent does not determine an article's evidence direction.
- UNKNOWN is not CONTRADICT.
- Open Targets association scores are prioritisation/association signals, not probabilities or causal proof.
- Candidate–strategy records can repeat the same publication across policy arms; do not count those as independent publications.
- Counter-evidence recall is restricted to the pooled publications retrieved for this fixed pilot candidate set, not the full literature corpus.
