# TrustDTI - Week 9 Progress Report
## Open Targets Platform 26.09 Integration and Network 2 Preparation

**Milestone:** Week 9  
**Reporting date:** 8 November 2026  
**Development hours recorded:** 10  
**Status:** Network 2 target bridge completed; full direct-association extraction in progress

> **Scope note:** This report distinguishes validated results from unfinished work. The full 14-shard association extraction did not complete during the recorded run.

## 1. Executive Summary
Week 9 focused on validating the mapping between TrustDTI's Network 1 human protein accessions and Open Targets Platform 26.09 target identifiers, and preparing the inputs required for a curated protein-disease association network (Network 2).

The UniProt-to-Ensembl mapping and Open Targets target-index validation are complete. A high-confidence bridge containing 2,295 unique UniProt-to-Ensembl target mappings was prepared from 2,312 Network 1 protein accessions. The direct-association dataset was inspected and a batch-processing pipeline was exercised on the first two of 14 Parquet shards. Those two shards produced 248,834 target-matched datasource-level rows, but the full extraction did not finish because Windows prevented deletion of an open Parquet file. Therefore, a completed Network 2 association dataset is not claimed in this report.

## 2. Tasks and Work Completed
2.1 Compound representation sensitivity analysis. Completed the Standard InChI round-trip sensitivity experiment on the random and drug-cold pilot splits. The original representation branch reproduced the saved baseline results. On the random pilot, the normalized branch changed five of nine sampled conflict-compound fingerprints (93 fingerprint bits), changed 11 of 2,000 test labels, and shifted predicted probabilities by a mean absolute 0.00247; ROC-AUC moved from 0.81033 to 0.81021. On the drug-cold pilot, two of four sampled fingerprints changed (55 bits), 18 of 2,000 test labels changed, and mean absolute probability shift was 0.00687; ROC-AUC moved from 0.77853 to 0.77759. The results showed no consistent improvement, so the original baseline representation was retained and the normalization experiment recorded as sensitivity analysis.

2.2 UniProt-to-Ensembl identifier mapping. Mapped 2,312 Network 1 UniProt accessions using the UniProt ID Mapping service. The mapping returned 2,542 candidate Ensembl gene records; 2,303 accessions had at least one Ensembl mapping (99.61%), while nine had no mapping. One-to-many mappings were preserved for review rather than arbitrarily collapsed.

2.3 Open Targets target-index validation. Downloaded and inspected the three Open Targets 26.09 target-index Parquet shards (78,733 unique target IDs). The target index exposed UniProt protein cross-references. Of 2,312 Network 1 accessions, 2,301 had at least one Open Targets target record (99.52%). Across 2,542 Ensembl candidate mapping rows, 2,336 candidate target records were found in the Open Targets target index and 206 were not found. The validation reported 2,170 one-to-one target cross-reference confirmations, 131 one-to-many accessions requiring review at the initial validation stage, nine without an Ensembl mapping, and two without an Open Targets target record.

2.4 High-confidence Network 2 target bridge. Used direct UniProt cross-references in the Open Targets target index to uniquely resolve 125 of the initially ambiguous one-to-many accessions. Combined with the 2,170 one-to-one confirmed mappings, this produced 2,295 high-confidence unique mappings. Seventeen accessions remain in the review queue. The bridge contains 2,294 protein-coding targets and one IG_V_gene target; the latter was retained with its biotype flag rather than silently discarded.

2.5 Direct association data reconnaissance. Confirmed the Open Targets 26.09 association_by_datasource_direct dataset is available as 14 Parquet shards with an estimated combined compressed size of 821.33 MB. Confirmed the disease metadata dataset is available as one Parquet file of approximately 6.05 MB. Inspected the first direct-association shard: 497,136 rows and eight columns, including diseaseId, targetId, aggregationType, aggregationValue, associationScore, evidenceCount, timeseries and currentNovelty. Sample records showed datasource-level rows such as aggregationType=datasourceId and aggregationValue=europepmc.

2.6 Initial batch-processing test. The extraction script processed shard 1 and shard 2, matching 114,855 and 133,979 rows respectively to the high-confidence target bridge (248,834 rows total). These are partial-processing counts only; the complete 14-shard filtered Parquet output was not produced.

## 3. Key Validation Results
Network 1 protein accessions: 2,312.

UniProt-to-Ensembl mapped accessions: 2,303 / 2,312 (99.61%); unmapped: 9.

Open Targets target-index size: 78,733 unique target IDs.

Accessions with at least one Open Targets target: 2,301 / 2,312 (99.52%).

High-confidence unique Network 2 target bridge: 2,295 / 2,312 accessions (99.26%); review queue: 17.

High-confidence bridge biotypes: 2,294 protein_coding and 1 IG_V_gene.

Direct association extraction test: 248,834 matching datasource-level rows across the first two of 14 shards; final extraction remains pending.

## 4. Roadblocks and Challenges
The first two association shards were downloaded/read and filtered successfully. During cleanup, Windows raised PermissionError [WinError 32] because the downloaded Parquet file was still held by the PyArrow reader when the script attempted to delete it. The exception stopped the run and the script removed its partial output, so no completed association Parquet dataset should be used yet. The planned correction is to explicitly close the ParquetFile reader before deleting each temporary shard, then rerun the extraction; already downloaded shards can be reused.

A request to list the parent Open Targets evidence directory returned HTTP 404. This only establishes that the parent listing URL was unavailable; source-specific evidence partitions have not yet been individually checked. The evidence dataset should therefore be described as not yet located/verified, not as absent from the release.

## 5. Plan and Roadmap for Week 10
Fix the Windows file-handle cleanup and rerun all 14 association shards, reusing valid local downloads where possible.

Validate the final filtered association output: schema preservation, row counts, target coverage, disease coverage, datasource distribution, duplicate target-disease-source keys, nulls and score ranges.

Download and inspect the disease metadata Parquet file, then join disease identifiers to readable disease names and relevant ontology metadata.

Investigate source-specific evidence partitions and identify suitable literature/curated evidence sources. Do not treat a missing parent directory listing as proof that evidence data is unavailable.

Build the Network 2 protein-disease association table with source provenance preserved. Keep association scores source-specific and do not interpret them as calibrated probabilities or proof of causality.

Proceed to the deterministic uncertainty-by-disease-relevance routing and evidence retrieval components after Network 2 is validated.

## 6. Technologies and Tools Used
Python 3.12.6; pandas; PyArrow; Parquet with Zstandard compression; Requests; UniProt ID Mapping REST service; Open Targets Platform 26.09 datasets; RDKit for compound representation sensitivity analysis; Git/GitHub; Windows with Git Bash (MINGW64).

## 7. Development Hours and Key Learning Outcome
Development hours recorded for the milestone: 10 hours.

Key learning outcome: gained practical experience with cross-database biological identifier mapping and evidence-aware resolution of one-to-many mappings; learned to preserve ambiguous mappings for review, validate protein targets against an external target index, inspect nested Parquet schemas, and process large datasets in batches while retaining provenance. A source-specific association score must not be mistaken for a probability or causal claim.

## 8. Reproducibility and Current Deliverables
Scripts prepared during this work include scripts/week09/map_uniprot_to_ensembl.py, scripts/week09/validate_opentargets_targets.py, scripts/week09/prepare_network2_association_inputs.py, scripts/week09/inspect_network2_association_schema.py and scripts/week09/build_network2_direct_associations.py. The compound sensitivity experiment is recorded in experiments/week09/evaluate_inchi_normalization.py.

Key local outputs include outputs/week09_network2/uniprot_opentargets_primary_bridge.csv, outputs/week09_network2/uniprot_opentargets_mapping_review.csv, outputs/week09_network2/opentargets_target_validation_audit.json, the association schema/sample inspection files, and the partial extraction run logs. These outputs are local working artifacts; the Week 9 report and infographic are being packaged for milestone submission.

Repository: https://github.com/Itsabhirajurs/Trust_DTI. A Week 9 commit URL is not yet available because the report package is being prepared before the planned commit/push. The final filtered Network 2 association dataset is also not yet available.

## 9. Research and Data-Interpretation Notes
The Network 2 target bridge is an identifier-mapping layer; it is not itself a protein-disease association network. Open Targets direct association rows will provide the disease association layer once the complete extraction and validation succeed.

The association_by_datasource_direct records retain datasource-specific aggregation values. Scores from different sources should remain distinguishable with their provenance. No source score should be described as a calibrated probability, causal effect, or proof of a biological mechanism.

Unknown or unverified evidence must remain unknown. The fact that the parent evidence directory returned 404 is not evidence that no literature records exist, and absence of a retrieved association is not automatically negative evidence.

## Appendix A - Milestone form links
- **GitHub repository (optional):** https://github.com/Itsabhirajurs/Trust_DTI
- **GitHub Week 9 commit:** to be added after the report and supporting files are committed.
- **Supporting document / demo link:** add the shareable Google Drive link after uploading the PDF and infographic.

## Appendix B - Suggested repository location
Place this report package under `reports/week09/` in the TrustDTI repository. The archive supplied with this report preserves that directory structure.