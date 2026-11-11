# Network 2: identifier bridge and protein–disease evidence

## Why this stage exists

Network 1 contains compound–protein interaction labels and predictions. TrustDTI also needs disease context for each protein so the evidence router can distinguish a model prediction about a protein that is highly relevant to a disease from one with little curated disease support.

This is a lookup/curation task, not a second disease-prediction model. Network 2 must remain separate from Network 1's drug–protein edges.

## Identifier path

Network 1 stores protein identifiers as UniProt accessions. Open Targets associations use Ensembl target IDs and disease IDs from the EFO ontology. The bridge therefore follows:

`Network 1 UniProt accession → Ensembl gene ID → Open Targets target index`

A successful string match is not sufficient when one UniProt accession maps to several Ensembl IDs. TrustDTI preserves all candidates and uses the Open Targets target record's direct UniProt cross-reference to identify a unique supported candidate. Ambiguous cases stay in a review queue; they are not arbitrarily collapsed.

## Current release 26.09 mapping results

- Network 1 proteins: 2,312.
- UniProt-to-Ensembl candidate mapping rows: 2,542.
- Accessions with at least one Ensembl mapping: 2,303 (99.61%); nine are unmapped.
- Open Targets target index: 78,733 unique target IDs.
- Accessions with at least one Open Targets target: 2,301 (99.52%).
- High-confidence unique bridge: 2,295 accessions (2,170 one-to-one plus 125 one-to-many cases with exactly one direct UniProt cross-reference).
- Seventeen accessions remain for review.
- Bridge biotypes: 2,294 protein-coding and one IG_V_gene. Retain the latter with an explicit biotype flag so the inclusion is visible and can be tested in sensitivity analysis.

Artifacts and reproducible scripts live in `outputs/week09_network2/` and `scripts/week09/`.

## Association records

The Open Targets 26.09 `association_by_datasource_direct` dataset was discovered as 14 Parquet shards. Its inspected schema contains:

- `targetId`: Ensembl target identifier
- `diseaseId`: disease identifier
- `aggregationType`: grouping field (the inspected records use `datasourceId`)
- `aggregationValue`: specific source identifier (sample: `europepmc`)
- `associationScore`: source-specific association ranking score
- `evidenceCount`: supporting evidence-record count
- `timeseries` and `currentNovelty`: longitudinal/novelty summaries

Keep source-specific rows and source identifiers. Do not average or sum unrelated datasource scores and do not call them probabilities or causal effects. Open Targets explains that the direct-by-datasource scores are independently source-normalised and designed for prioritisation; the overall score is a separately aggregated product. See the [official association-score documentation](https://platform-docs.opentargets.org/associations).

Use **direct** associations for the primary network. Indirect associations propagate evidence through disease ontology relationships and should not silently be mixed into the direct edge table.

## Current extraction state — 11 November 2026

The complete local run processed all 14 of 14 `association_by_datasource_direct` shards:

- Input rows across the 14 shards: 7,522,466.
- Rows linked to the high-confidence target bridge: 1,739,224.
- Datasource-level rows retained: 1,739,224.
- Unique targets represented: 2,295 (all targets in the primary bridge).
- Unique disease IDs: 21,268.
- Unique target–disease–source keys: 1,739,224.
- Duplicate key rows retained for audit: 0.

Largest source groups were Europe PMC (752,854), IMPC (680,209), GWAS Credible Sets (165,102), Clinical Precedence (56,902), and Cancer Gene Census (33,961). The full source distribution and checksums are recorded in `outputs/week09_network2/network2_association_source_counts.csv` and `network2_download_manifest.csv`.

The filtered table is `data/processed/network2_direct_associations.parquet`; its audit is `outputs/week09_network2/network2_direct_association_audit.json`. Newly downloaded temporary shards were closed and removed successfully, so the prior Windows file-lock blocker is resolved.

The separate disease metadata table was downloaded and inspected: 45,896 rows and 18 columns. It includes `id`, `code`, `name`, `description`, database cross-references, parent/child/ancestor/descendant ontology relations, exact and related synonyms, therapeutic areas, and ontology metadata. The inspected schema and sample are saved as `opentargets_disease_schema.json` and `opentargets_disease_sample.json`.

This completes the direct-by-datasource extraction gate only. The overall-direct disease score table and joint Network 2 validation must still run before candidate construction.

## Safe data model (target structure)

Keep the raw/source-specific association table at one row per source-specific target–disease association. Include:

- `uniprot_accession`, `targetId`, gene symbol and target biotype
- `diseaseId` and later disease label/ontology metadata
- `aggregationType`, `aggregationValue`, `associationScore`, `evidenceCount`
- `timeseries`, `currentNovelty`
- `opentargets_release`, retrieval/file provenance and `edge_provenance = curated`

The release's `association_overall_direct` table is the separate official overall score product. Retain its score in a separate per-target–disease table as the candidate anchor score. Do not manufacture an “overall” score by averaging datasource scores.

## Overall-direct score anchor

Open Targets 26.09 also publishes a separate `association_overall_direct` dataset. It contains one overall score for each direct target–disease pair, with `aggregationType=overall` and an empty `aggregationValue`. This is the correct anchor-score product for Network 2; it is not created by averaging the datasource-specific rows.

Open Targets describes the overall score as a harmonic sum of source-level association scores weighted by its datasource weights. It is between 0 and 1 and supports ranking, but the documentation explicitly cautions that it is a heuristic based on evidence availability—not a confidence score or causal proof. Under-studied diseases may have low scores despite potentially interesting targets. Use it only as a routing-priority signal and keep the source-specific dataset as separate provenance.

The feature-branch builder is `scripts/week10/build_network2_overall_direct.py`; the joint quality gate is `scripts/week10/validate_network2.py`. Candidate generation must not proceed until both datasets pass the validation audit.

## What the score does and does not mean

An association score is an evidence-ranking/association score. It helps rank target–disease relationships within the Open Targets framework. It is not a calibrated probability that the gene causes the disease and not proof of a causal mechanism. Scores also depend on source coverage and evidence availability; a low score may reflect under-studied biology.

The disease anchor is therefore a routing signal with a documented policy, not ground truth about causality. Any anchor thresholding rule must be written down before evaluation and kept fixed across the retrieval-policy experiment.

## Teaching analogy

Think of the ID bridge as a verified address book: Network 1 says “protein P36888”; Open Targets says “target ENSG…”. Cross-references tell us when those two records refer to the same biological target. Then association records say “this target has curated evidence linked to disease EFO… from source X.” The bridge identifies *which protein*; the association table describes *what disease evidence is linked to it*. Those are different jobs.

## Next gates

1. Re-run the 14-shard download/filter after pulling the cleanup fix.
2. Validate association counts, target/disease coverage, source distribution, duplicate keys, nulls and schema.
3. Confirm the release's overall-direct association dataset and disease metadata schema.
4. Build the curated Network 2 table and retain unresolved protein IDs separately.
5. Only then calibrate anchor-strength categories for the deterministic router.
