# TrustDTI - Week 10 Progress Report
## Network 2 direct-association completion and adaptive literature retrieval

**Milestone:** Course Week 10  
**Reporting period:** 11-15 November 2026  
**Prepared:** 15 November 2026  
**Status:** Both Network 2 direct-association products extracted locally; null-sentinel code correction passes CI; local data-backed revalidation and live retrieval experiment remain open.

> This report separates local execution results, code/CI results and work not yet executed. The Week 10 engineering prototype is not a claim that the scientific research question has been answered.

## 1. Executive summary

Week 10 moved Network 2 from an identifier bridge and a partial extraction attempt to two full, separate Open Targets Platform 26.09 direct-association tables. It also connected the deterministic uncertainty-by-disease-context router to a reproducible literature-retrieval and human-evaluation scaffold.

The complete `association_by_datasource_direct` build processed all 14 shards and retained **1,739,224 datasource-level rows**, covering all **2,295 high-confidence mapped targets** and **21,268 disease identifiers**. All target-disease-source keys were unique.

The separate `association_overall_direct` build processed all 14 shards and retained **1,633,220 target-disease rows**, again covering all 2,295 targets and 21,268 disease identifiers. The disease-metadata join reported zero unmatched rows. The official overall score remains separate; no average of datasource scores was manufactured.

The first joint Network 2 validation run passed 16 of 17 checks. The only failure concerned `aggregationValue`: all overall rows carried the literal string `None`. Inspection established that this is a serialized null sentinel, not a datasource value. The builder and validator were corrected to normalize or recognize null-like values. The follow-up branch was merged into `main` through PR #3. GitHub Actions on the fix branch reported **61 passed, 2 skipped, 1 deselected**, and the merged main-branch workflow completed successfully. The local data-backed validator must still be rerun after pulling the correction.

The deterministic router, Europe PMC retrieval client, four strategy arms, blinded annotation preparation and evaluator are implemented and unit-tested. The live candidate-generation/retrieval run, human annotations and matched-budget comparison have not yet been completed. No claim is made that adaptive retrieval improves evidence precision or counter-evidence recall.

### Milestone scorecard

| Workstream | Status | Evidence |
|---|---|---|
| Source-specific Network 2 extraction | Completed locally | 14/14 shards; 1,739,224 rows |
| Overall-direct Network 2 extraction | Completed locally | 14/14 shards; 1,633,220 rows |
| Disease metadata join | Completed locally | 0 unmatched rows |
| Joint Network 2 validation | Code fix passes CI; local rerun pending | Initial audit had one null-sentinel failure |
| Deterministic seven-policy router | Implemented and unit-tested | Prediction set x disease tier |
| Europe PMC backend | Implemented and unit-tested | Stable IDs, provenance, retries, failures |
| Four retrieval arms | Implemented | Fixed, uncertainty-only, disease-only, combined |
| Blinded annotation/evaluator | Implemented | SUPPORT / CONTRADICT / UNKNOWN |
| Measured retrieval experiment | Not yet run | Candidate generation and human annotation pending |

## 2. Week 9 foundation carried forward

Week 9 prepared the identifier bridge required to join TrustDTI proteins to Open Targets targets:

- Network 1 contained 2,312 human protein accessions.
- 2,303 accessions had at least one UniProt-to-Ensembl candidate mapping.
- The Open Targets 26.09 target index contained 78,733 unique targets.
- 2,301 Network 1 accessions had at least one Open Targets target.
- The high-confidence bridge retained **2,295 unique UniProt-to-Ensembl/Open Targets mappings**: 2,170 one-to-one mappings plus 125 one-to-many cases resolved through a unique direct UniProt cross-reference.
- Seventeen accessions remained in a review queue.
- The bridge retained 2,294 protein-coding targets and one IG_V_gene target with an explicit biotype flag.

Week 9 also exposed a Windows file-handle issue during Parquet cleanup. The close-before-delete helper was isolated in `src/network/parquet_io.py` and regression-tested. Week 10's successful 14-shard execution confirmed temporary-shard cleanup for the new downloads.

The bridge is an identifier-mapping layer; it is not itself a disease network. Week 10 therefore treated the source-specific and overall-direct association products as separate data products.

## 3. Source-specific Network 2 extraction

**Dataset:** Open Targets Platform 26.09 `association_by_datasource_direct`.

The extractor discovers the 14 Parquet shards, loads the validated primary target bridge, reads files in batches, filters to supported Ensembl target IDs and preserves datasource-level aggregation values and evidence fields. It adds UniProt accession, gene symbol, target biotype, release and curated-edge provenance.

The execution reused the first two local schema-check shards and processed/downloaded the remaining 12.

**Command:**

```bash
python scripts/week09/build_network2_direct_associations.py
```

The script remains at its original Week 9 path because it originated during Week 9 mapping/extraction preparation; the full production run is documented here as Week 10 work.

### 3.1 Results from the local execution log

| Measure | Result |
|---|---:|
| Parquet shards processed | 14 / 14 |
| Total input rows | 7,522,466 |
| Rows matched to high-confidence bridge | 1,739,224 |
| Datasource-level rows written | 1,739,224 |
| Unique mapped targets | 2,295 / 2,295 |
| Unique disease identifiers | 21,268 |
| Unique target-disease-source keys | 1,739,224 |
| Duplicate key rows | 0 |

### 3.2 Datasource distribution

| Datasource | Rows |
|---|---:|
| Europe PMC | 752,854 |
| IMPC | 680,209 |
| GWAS Credible Sets | 165,102 |
| Clinical Precedence | 56,902 |
| Cancer Gene Census | 33,961 |
| Expression Atlas | 25,246 |
| EVA | 8,366 |
| Gene Burden | 2,780 |
| Genomics England | 2,589 |
| CRISPR Screen | 2,389 |
| UniProt Literature | 1,451 |
| Orphanet | 1,359 |
| UniProt Variants | 1,161 |
| IntOGen | 1,139 |
| Gene2Phenotype | 911 |
| ClinGen | 825 |
| EVA Somatic | 781 |
| Reactome | 648 |
| Cancer Biomarkers | 331 |
| CRISPR | 220 |
| **Total** | **1,739,224** |

The largest contributors were Europe PMC and IMPC. These counts describe retained evidence records for the mapped targets; they are not a ranking of biological truth or source quality.

### 3.3 Local outputs

The local execution log reported:
- `data/processed/network2_direct_associations.parquet`
- `outputs/week09_network2/network2_association_source_counts.csv`
- `outputs/week09_network2/network2_download_manifest.csv`
- `outputs/week09_network2/network2_direct_association_audit.json`
- `outputs/week09_network2/opentargets_disease_schema.json`
- `outputs/week09_network2/opentargets_disease_sample.json`

These Parquet files, shard downloads, manifests and audits remain local and are not committed.

## 4. Separate overall-direct Network 2 extraction

Open Targets publishes `association_overall_direct` as a separate overall score product. TrustDTI must not manufacture an overall score by averaging or summing unrelated datasource-level rows.

The two outputs remain separate:
1. `association_by_datasource_direct`: source-specific records with source identifiers and provenance.
2. `association_overall_direct`: one official overall direct-association score per target-disease pair, used as a disease-context prioritisation signal.

The scores are not calibrated probabilities and do not prove causality.

### 4.1 Results from the local execution log

| Measure | Result |
|---|---:|
| Parquet shards processed | 14 / 14 |
| Total input rows | 7,225,847 |
| Rows matched to target bridge | 1,633,220 |
| Output rows | 1,633,220 |
| Unique mapped targets | 2,295 / 2,295 |
| Unique disease identifiers | 21,268 |
| Targets without edges | 0 |
| Duplicate target-disease keys | 0 |
| Disease metadata unmatched rows | 0 |
| Overall association score minimum | 0.0 |
| Overall association score maximum | 0.9138468742 |

The disease metadata table contained 45,896 unique records and 18 inspected columns, including names, descriptions, codes, cross-references, ontology relationships, synonyms and therapeutic-area metadata. The build audit reported zero unmatched disease rows.

**Command:**

```bash
python scripts/week10/build_network2_overall_direct.py
```

**Local outputs:**
- `data/processed/network2_overall_direct.parquet`
- `outputs/week10/network2_overall_direct_audit.json`

## 5. Network 2 validation and null-sentinel correction

The first joint run of `python scripts/week10/validate_network2.py` passed **16 of 17 checks**. It confirmed bridge uniqueness, mapping consistency, aggregation types, release labels, datasource identifiers, provenance, key uniqueness, score ranges and disease-name coverage. The only failed check was `overall_aggregation_value_empty`.

Inspection showed:
- `aggregationType=overall` on all 1,633,220 overall rows.
- The literal string `None` in `aggregationValue` on all 1,633,220 rows.

This is a serialized missing value, not another source label.

The follow-up branch `fix/network2-aggregation-null` (merged into `main` through PR #3):
- converts `None`, `null`, blank and `<NULL>` sentinels to Arrow nulls when rebuilding;
- treats those values as missing when validating an already-built local Parquet file;
- includes parameterized regression tests for the sentinel forms.

GitHub Actions for PR #3 completed with **61 passed, 2 skipped, 1 deselected**. This confirms code and tests in CI, not the workstation's local Parquet data. Rerun the local validator after pulling the correction; the data-backed validation gate stays open until `all_critical_checks_passed: true`.

## 6. Adaptive retrieval prototype

### 6.1 End-to-end design

`Network 1 prediction -> Network 2 disease context -> deterministic routing -> Europe PMC -> blinded annotation -> matched-budget evaluation`

Network 1 supplies the saved drug-protein prediction set. Network 2 supplies curated protein-disease associations and an overall-direct anchor. The deterministic router selects a search policy. Europe PMC returns records with provenance. Human annotators judge each publication. The evaluator compares four strategies on the same fixed candidates and per-candidate document budget.

An LLM does not choose a routing policy or assign evidence direction.

### 6.2 Seven routing policies

| Prediction set | Disease anchor | Policy | Retrieval priority |
|---|---|---|---|
| ACTIVE | STRONG | CONFIRM | Mechanistic evidence, then disease context |
| ACTIVE | MODERATE | CONTEXTUALISE | Disease linkage; mechanism secondary |
| ACTIVE | WEAK / NONE | INVESTIGATE | General background and target mechanism |
| ACTIVE + INACTIVE | STRONG | CHALLENGE | Counter-evidence and safety first |
| ACTIVE + INACTIVE | MODERATE | CHALLENGE_CONTEXT | Counter-evidence, then disease linkage |
| ACTIVE + INACTIVE | WEAK / NONE | LOW_PRIORITY | Small, low-priority search |
| INACTIVE | Any | STOP | No adaptive retrieval |

The quantile-based disease-anchor tiers are an engineering prioritisation convention, not biological truths. Thresholds must be frozen before evaluation.

### 6.3 Europe PMC retrieval

The client preserves stable PMID/PMCID/DOI identifiers when available, title/abstract metadata, source URL, exact query, retrieval timestamp and strategy provenance. It includes retry and explicit failure handling. Retrieved records start as `UNANNOTATED`.

Query intents:
- `MECHANISTIC`: drug + gene + interaction terms.
- `COUNTER`: drug + gene + resistance, failure or no-effect terms.
- `DISEASE_CONTEXT`: gene + disease.
- `GENERAL`: drug + gene.

Query intent is not an evidence direction.

### 6.4 Matched-policy comparison

The same fixed candidate set is evaluated under `fixed`, `uncertainty_only`, `disease_only` and `combined`.

The planned pilot is capped at nine candidates and five retrieved documents per candidate:

```bash
python scripts/week10/build_candidate_set.py --per-state 3 --max-candidates 9
python scripts/week10/run_retrieval_demo.py --budget-per-candidate 5
python scripts/week10/prepare_annotation_sheet.py
```

The candidate builder is label-blind. For this prototype it selects the highest overall-direct named disease association per UniProt accession for query generation. This is an engineering simplification, not a claim that each protein has only one relevant disease.

**Execution status:** the commands are implemented, but no actual candidate-set build or live Europe PMC run appears in the supplied terminal logs. No candidate count, publication count or retrieval metric is claimed.

## 7. Blinded annotation and evaluation

The preparation script deduplicates each candidate-publication pair so a publication retrieved by multiple policies is annotated once. The visible worksheet hides strategy, query and retrieval intent. A private strategy manifest and key restore policy exposures only after labels are finalized.

Direction labels:
- **SUPPORT:** relevant article content supports the stated hypothesis.
- **CONTRADICT:** relevant article content directly weakens or challenges the stated hypothesis.
- **UNKNOWN:** the available title/abstract does not justify a directional decision, or the item is not relevant.

Evidence categories include MECHANISTIC, DISEASE_CONTEXT, COUNTER, SAFETY and OTHER. A rationale is required. UNKNOWN must never be converted to CONTRADICT; missing results are not negative evidence.

The evaluator reports relevant-evidence precision, annotation coverage, counter-evidence share and pooled candidate-set counter-evidence recall. That recall denominator is the union of contradiction-labelled publications found within the four retrieved pools for these candidates. It is **not** exhaustive recall over all published literature.

**Execution status:** worksheet generator and evaluator are implemented and unit-tested. Human annotations and the measured four-arm comparison remain pending.

## 8. Repository implementation map

| Area | File |
|---|---|
| Parquet reader lifecycle | `src/network/parquet_io.py` |
| Deterministic router | `src/network/router.py` |
| Europe PMC client | `src/retrieval/europe_pmc.py` |
| Retrieval query/policy pipeline | `src/retrieval/pipeline.py` |
| Source-specific association builder | `scripts/week09/build_network2_direct_associations.py` |
| Overall-direct builder | `scripts/week10/build_network2_overall_direct.py` |
| Joint Network 2 validator | `scripts/week10/validate_network2.py` |
| Label-blind candidate builder | `scripts/week10/build_candidate_set.py` |
| Europe PMC demo runner | `scripts/week10/run_retrieval_demo.py` |
| Blinded annotation preparation | `scripts/week10/prepare_annotation_sheet.py` |
| Four-arm evaluator | `scripts/week10/evaluate_retrieval.py` |

## 9. Tools and data sources

Python 3.12.6; pandas; PyArrow; Requests; Open Targets Platform 26.09; Europe PMC REST API; Git/GitHub; GitHub Actions; pytest. Official endpoints are in [references.md](references.md).

## 10. Limitations and research safeguards

1. Local joint Network 2 validation remains pending after the null-sentinel code fix.
2. Candidate sampling has not yet been executed in the submitted logs.
3. Live literature retrieval has not yet been executed; no query counts or failure rates are reported.
4. Human evidence annotations are pending.
5. No adaptive-retrieval improvement claim is justified yet.
6. Open Targets association scores are prioritisation scores, not causal probabilities.
7. Query intent never becomes SUPPORT or CONTRADICT automatically.
8. UNKNOWN remains UNKNOWN; missing evidence is not negative evidence.
9. Source-specific scores are not averaged into the overall score.
10. Raw/processed Parquet, shard downloads, retrieved abstracts, annotation sheets and private strategy files are not committed.

## 11. Next actions

1. Pull the Week 10 branch and rerun `python scripts/week10/validate_network2.py` on the existing local Parquet outputs.
2. Confirm `all_critical_checks_passed: true`.
3. Build the nine-candidate set.
4. Run the four Europe PMC strategies at the same per-candidate budget.
5. Prepare the blinded annotation sheet; keep the strategy manifest/key private.
6. Annotate unique candidate-publication pairs as SUPPORT, CONTRADICT or UNKNOWN, with evidence category and rationale.
7. Evaluate the four arms and report actual denominators, annotation coverage, failures and metrics.
8. Update the report only with observed outputs.

## 12. Key learning outcome

The identifier bridge answers **which external target record belongs to a protein**. Network 2 association tables describe **which curated disease evidence is linked to that target**, separately at datasource and overall level. The router uses disease context to decide what to search for; the publication itself still requires evidence-direction annotation.

## References

- Open Targets 26.09 `association_by_datasource_direct`: https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.09/output/association_by_datasource_direct/
- Open Targets 26.09 `association_overall_direct`: https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.09/output/association_overall_direct/
- Open Targets 26.09 disease metadata: https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.09/output/disease/
- Open Targets association-score documentation: https://platform-docs.opentargets.org/associations
- Europe PMC REST search API: https://www.ebi.ac.uk/europepmc/webservices/rest/search
- Repository: https://github.com/Itsabhirajurs/Trust_DTI
