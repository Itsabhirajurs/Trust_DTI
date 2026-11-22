# TrustDTI — Week 11 Progress Report

## Interim final-sprint checkpoint: Network 2 validation and adaptive literature retrieval

**Reporting date:** 22 November 2026  
**Execution evidence window:** 21–22 November 2026  
**Repository:** https://github.com/Itsabhirajurs/Trust_DTI  
**Local workspace:** `C:\Users\91701\code\Trust_DTI`  
**Python:** 3.12.6 in `.venv`  
**Current weighted progress estimate:** **80% complete; 20% remaining**

> **Report status:** This is an interim Week 11 progress report based on the terminal outputs supplied from the research workstation. The data validation and candidate-generation gates are complete. An initial live retrieval experiment has run, but query coverage is weak. Human evidence annotation and matched-policy evaluation have not been completed. This report does not claim that the research hypothesis has been validated.

## 1. Executive summary

Week 11 converted the Week 10 implementation into a locally executed, data-backed pilot. The local repository was fast-forwarded to the merged main branch, the local research outputs were backed up, and the updated test suite completed with **70 passed and 1 deselected**. The corrected Network 2 validator was run against the actual bridge and two local Parquet tables. All **17 of 17 critical checks passed**, with no warnings.

A reproducible candidate builder then produced **nine label-blind candidates**, balanced across ACTIVE_ONLY, INACTIVE_ONLY and UNCERTAIN prediction states (three per state), using seed 42. All nine candidates were assigned a STRONG Network 2 disease-anchor tier. The first live Europe PMC run executed all four retrieval policies with a five-document per-candidate cap. It returned **15 candidate–strategy–publication records** and recorded two request timeouts.

The retrieval audit exposed a major quality limitation: the 15 returned records were all disease-context records. No mechanistic, counter-evidence or general-intent records were retrieved. The uncertainty-only policy returned zero records. A follow-up compound-identity audit established exact ChEMBL InChIKey matches for all nine compounds, but ChEMBL returned no preferred names or synonyms for these molecule records. A 12-query Europe PMC diagnostic—chemical-name and ChEMBL-ID searches, each with synonym expansion on and off, across DRD2, PTH1R and IRAK4—returned zero hits in every condition.

The current scientific interpretation is therefore limited: the Network 2 and candidate-selection foundations are validated, and the live retrieval code executes, but the literature query design is not yet producing a sufficiently broad or balanced evidence set. The next work should improve and test query construction while preserving the original retrieval experiment as a baseline. Only then should the blinded annotation and matched-policy evaluation be completed.

## 2. Weighted progress estimate

The original Week 11 baseline was 70%. The current 80% estimate gives full credit to the now-passed Network 2 validation and partial credit to the candidate/live-retrieval workstream because the candidate set and first live run exist, but retrieval quality remains unresolved.

| Workstream | Weight | Completed | Remaining |
|---|---:|---:|---:|
| Data foundation, Network 1 and classical baseline | 20 | 20 | 0 |
| Network 2 mapping and both 14-shard extractions | 25 | 25 | 0 |
| Joint Network 2 data-backed validation | 10 | 10 | 0 |
| Router, Europe PMC client, four strategies, annotation/evaluator implementation | 20 | 20 | 0 |
| Actual fixed-candidate and live retrieval run | 10 | 5 | 5 |
| Human evidence annotations | 10 | 0 | 10 |
| Matched-policy evaluation and final results | 5 | 0 | 5 |
| **Total** | **100** | **80** | **20** |

This is a project-management estimate of the defined engineering-plus-pilot workflow. It is not a model-performance measurement, a probability of success or a statement that the broader research programme is complete. Full ChemBERTa/ESM-2 caches, a fusion model, formal calibration and larger external validation remain outside this pilot checkpoint.

## 3. Work completed and verified

### 3.1 Repository and environment

- Switched the local workspace to `main` and fast-forwarded from `0450518` to `712f4a2`.
- Backed up local Week 9 and Week 10 output folders to `C:\Users\91701\code\Trust_DTI_local_outputs_backup_20261121_205036`.
- Verified Python 3.12.6, pandas 3.0.6, PyArrow 25.0.1 and scikit-learn 1.9.1.
- Ran `python -m pytest -q`: **70 passed, 1 deselected**.

### 3.2 Network 2 validation

The fresh validation audit was written to `outputs/week10/network2_validation_audit_rerun.json`. After inspecting it, the earlier failed audit was preserved as `network2_validation_audit_pre_rerun.json`, and the passing rerun was copied to the canonical candidate-builder input `network2_validation_audit.json`.

| Measure | Validated result |
|---|---:|
| Open Targets release | 26.09 |
| UniProt–Ensembl bridge rows | 2,295 |
| Unique UniProt accessions | 2,295 |
| Unique Ensembl IDs | 2,295 |
| Source-specific association rows | 1,739,224 |
| Overall-direct association rows | 1,633,220 |
| Distinct disease IDs | 21,268 |
| Source-specific duplicate keys | 0 |
| Overall target–disease duplicate keys | 0 |
| UniProt-to-target mismatches | 0 |
| Missing source IDs | 0 |
| Missing disease names | 0 |
| Disease-name coverage | 100% |
| Non-curated provenance rows | 0 in both tables |
| Score values outside [0, 1] | 0 in both tables |
| Overall rows with non-empty aggregationValue | 0 |
| Critical checks | **17/17 true** |
| Warnings | **0** |

The previous failure was `overall_aggregation_value_empty`: the first audit interpreted the literal string `None` in `aggregationValue` as populated data. The corrected local rerun now passes this check. The actual local table contains 1,633,220 overall-direct records with zero non-empty aggregation values under the validator's null-sentinel handling.

The validator's interpretation remains important: source-specific and overall-direct Open Targets scores are separate prioritisation products, not probabilities or causal proof.

### 3.3 Fixed label-blind candidate set

Command used:

```powershell
python scripts/week10/build_candidate_set.py --per-state 3 --seed 42 --max-candidates 9
```

The candidate builder passed the refreshed validation gate and produced:

| Conformal state | Candidates |
|---|---:|
| ACTIVE_ONLY | 3 |
| INACTIVE_ONLY | 3 |
| UNCERTAIN | 3 |
| **Total** | **9** |

Candidate audit results:

- `candidate_selection_seed`: 42
- `label_blind_selection`: true
- `true_label_column_used`: false
- `anchor_tier_counts`: STRONG = 9
- Moderate anchor threshold: 0.007400497920106558
- Strong anchor threshold: 0.0484621606298178
- Threshold population: 1,633,220 overall-direct scores
- Drug title resolved during the builder's PubChem lookup: 8
- Drug title unresolved during the builder's PubChem lookup: 1

The one PubChem title miss was candidate `0830087a069c8cad` (IRAK4), which retained an InChIKey-based fallback name. Subsequent structure matching identified a corresponding ChEMBL record for this candidate.

### 3.4 Compound identity and name-enrichment diagnostics

A PubChem PUG REST synonym lookup returned HTTP 200 for eight compounds and HTTP 404 for the IRAK4 candidate's PubChem InChIKey route. PubChem supplied ChEMBL IDs for the other eight.

A follow-up ChEMBL lookup was corrected after the first script incorrectly expected a nested `molecule` object. The corrected extraction read the returned molecule fields and compared the returned standard InChIKey with each candidate's original key.

**Result: all 9 of 9 candidates had an exact ChEMBL InChIKey match.** The ChEMBL IDs were:

| Candidate | Target | ChEMBL molecule ID | Exact InChIKey match |
|---|---|---|---|
| f71aaf13cf08391a | DRD2 | CHEMBL1258535 | Yes |
| e6f9b83ea1b7fbb3 | CYP3A4 | CHEMBL1489708 | Yes |
| 608d2caeeebbe5bc | HTR1A | CHEMBL3949638 | Yes |
| 0723f1d688724366 | PTH1R | CHEMBL1385247 | Yes |
| 3f239e3699ee2f01 | POLI | CHEMBL1899453 | Yes |
| 954788b9023842da | PKM | CHEMBL1494871 | Yes |
| f894b1679dbcb915 | PTH1R | CHEMBL2134040 | Yes |
| 0830087a069c8cad | IRAK4 | CHEMBL4105582 | Yes |
| 4306d2a57fcfbff4 | BTK | CHEMBL316264 | Yes |

The returned ChEMBL records had no preferred names and no molecule synonyms in the fields inspected. This verifies chemical-structure identity against ChEMBL, but it does not provide a more useful literature-search name. The original chemical names and InChIKeys must therefore remain available; a ChEMBL ID must not be assumed to be a human-readable synonym.

## 4. Initial live Europe PMC retrieval experiment

Command used:

```powershell
python scripts/week10/run_retrieval_demo.py --budget-per-candidate 5
```

The four strategies used the same nine-candidate pool:

- `fixed`
- `uncertainty_only`
- `disease_only`
- `combined`

The nominal maximum is 9 candidates × 4 strategies × 5 documents = 180 candidate-strategy slots. The router intentionally allocates zero slots for INACTIVE_ONLY candidates in the uncertainty-only and combined policies. The actual allocations totalled **150 slots**, not 180:

| Strategy | Allocated slots | Candidate–strategy records returned | Candidates represented |
|---|---:|---:|---:|
| fixed | 45 | 3 | 3 |
| uncertainty_only | 30 | 0 | 0 |
| disease_only | 45 | 8 | 3 |
| combined | 30 | 4 | 2 |
| **Total** | **150** | **15** | — |

These records are candidate–strategy–publication exposures. The same publication can be retrieved by more than one policy arm; the 15 records should not be described as 15 independent publications. The inspected output contained eight distinct candidate–publication pairs across the four arms.

### 4.1 Publication-record quality

For the 15 retrieved exposure records:

- Missing titles: 0
- Missing abstracts: 0
- Missing publication IDs: 0
- Records not in `UNANNOTATED` status: 0
- All direction labels remained unset / null.

All returned records were attached to the `DISEASE_CONTEXT` intent. No returned records were attached to `MECHANISTIC`, `COUNTER` or `GENERAL` intents. The uncertainty-only strategy returned zero records despite having 30 allocated slots across eligible uncertain candidates.

### 4.2 Retrieval failures

Two Europe PMC requests failed with `ReadTimeout` after the configured 45-second read timeout:

1. Candidate `f894b1679dbcb915` / PTH1R, combined strategy, `DISEASE_CONTEXT` query.
2. Candidate `0830087a069c8cad` / IRAK4, uncertainty-only strategy, `COUNTER` query.

These are technical request failures, not evidence against the candidate–target interaction. Other zero-result searches were completed requests with no returned publications and are not counted as exceptions.

### 4.3 Interpretation

The first run demonstrates that the four-arm pipeline executes and writes provenance-preserving, unannotated records. It does not yet demonstrate that the policies retrieve useful or balanced drug–target evidence. The returned records are predominantly disease/gene context, and there is no retrieved mechanistic or counter-evidence record in this run.

## 5. Europe PMC synonym diagnostic

A separate diagnostic was run on representative DRD2, PTH1R and IRAK4 candidates. It compared two query term types:

- Exact chemical name + gene symbol
- ChEMBL molecule ID + gene symbol

Each was tested with Europe PMC's `synonym` option set to both `false` and `true`. This produced 3 candidates × 2 query types × 2 synonym settings = **12 diagnostic queries**.

**All 12 returned a hit count of zero.** Enabling the synonym option did not increase the hit count for these exact query constructions.

This finding is limited to the particular `TITLE_ABS` query expressions tested. It does not show that the compounds have no publications or that Europe PMC contains no relevant literature. It suggests that exact compound-term matching in the title/abstract field is too restrictive for this pilot, or that the current aliases/target terms are not adequate. The original candidate set and 15-record experiment must remain unchanged as the baseline while query design is improved.

## 6. Main roadblocks and decisions

| Issue | Evidence | Decision / control |
|---|---|---|
| Earlier Network 2 audit failure | Stringified `None` aggregation values | Corrected local rerun passed 17/17; preserve the old failed audit for traceability |
| One PubChem title not resolved | IRAK4 candidate returned PubChem 404 | Retain its InChIKey; ChEMBL exact structure match found |
| ChEMBL returned no preferred names/synonyms | Empty fields across 9 exact structure matches | Do not invent aliases; preserve chemical identity and search identifiers |
| Initial retrieval coverage low | 15 exposures; no uncertainty-only records | Diagnose and improve query construction before annotation |
| Europe PMC timeouts | Two 45-second `ReadTimeout` failures | Preserve failures and retry only in a separate, versioned run |
| Synonym expansion did not help | 12/12 diagnostic queries had zero hits | Test broader but controlled query formulations; do not treat zero hits as negative evidence |
| Human annotation outstanding | All retrieved records remain UNANNOTATED | No evaluator run until human labels, evidence categories and rationales are complete |

## 7. Remaining Week 11 work

1. Improve the literature-query design using validated compound identifiers, carefully selected aliases and target terms; test query variants on a small diagnostic subset first.
2. Preserve the initial retrieval outputs and run the improved four-arm experiment into a distinct output directory or clearly versioned filenames.
3. Review whether the new retrieval set contains mechanistic, disease-context, counter and safety-relevant publications; record empty searches and technical failures.
4. Generate and inspect the blinded annotation worksheet for the accepted retrieval run.
5. Manually annotate every unique candidate–publication pair with evidence category, SUPPORT / CONTRADICT / UNKNOWN, and a publication-grounded rationale.
6. Freeze the annotation worksheet before exposing the strategy manifest/key.
7. Run the matched-budget evaluator and report actual precision, coverage, annotation completeness, evidence counts and the pooled candidate-set counter-evidence recall denominator.
8. Revisit the completion estimate only after these gates have evidence.

## 8. Scientific limitations and reporting safeguards

- The candidate set contains only nine compounds from the random-split baseline test predictions. It is a small prototype sample, not a representative evaluation population.
- All nine candidates had STRONG overall-direct disease anchors under the implemented quantile thresholds; this pilot therefore does not compare all anchor-strength categories.
- The nine ChEMBL records matched the candidate InChIKeys, but preferred names and synonyms were absent in the returned fields.
- Zero Europe PMC hits do not mean a compound has no literature or that an interaction is inactive.
- The 15 candidate-strategy records include repeat exposures of the same candidate–publication pair across policy arms.
- Human evidence direction has not been assigned. Search intent, query wording and article title are not evidence labels.
- UNKNOWN is not CONTRADICT. Lack of retrieved evidence is not counter-evidence.
- Pooled counter-evidence recall is restricted to the union of CONTRADICT-labelled records retrieved for these fixed candidates across the tested strategies. It is not recall over the complete literature.
- No claim that adaptive routing improves precision, evidence diversity or counter-evidence recall is justified at this checkpoint.

## 9. Local evidence locations

The following paths refer to local, ignored research outputs on the Windows workstation:

- `outputs/week10/network2_validation_audit_rerun.json`
- `outputs/week10/network2_validation_audit.json` (canonical passing copy used by candidate builder)
- `outputs/week10/network2_validation_audit_pre_rerun.json` (preserved earlier failed audit)
- `data/processed/week10_candidates.csv`
- `outputs/week10/candidate_build_audit.json`
- `outputs/week10/retrieval_records_initial.jsonl`
- `outputs/week10/retrieval_failures_initial.json`
- `outputs/week10/retrieval_run_metadata_initial.json`
- `outputs/week10/pubchem_synonym_lookup.json`
- `outputs/week10/chembl_synonym_enrichment_corrected.json`
- `outputs/week10/retrieval_synonym_probe.json`

The committed [execution evidence JSON](WEEK11_EXECUTION_EVIDENCE.json) contains aggregate counts only. Raw abstracts, local CSV/Parquet research data, annotation sheets and private strategy keys are not included in this documentation pack.
