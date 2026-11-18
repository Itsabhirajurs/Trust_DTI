# Week 11 final completion plan — TrustDTI

## Goal

Complete the defined Network 2 + adaptive literature-retrieval engineering pilot with real local execution evidence, blinded publication annotation and a matched-budget comparison. This is the final planned sprint for the course milestone, not a claim that the broader research programme is scientifically complete.

## Starting progress

A transparent weighted estimate starts at 70% complete and 30% remaining:

| Workstream | Weight | Completed | Remaining |
|---|---:|---:|---:|
| Data foundation, Network 1 and baseline | 20 | 20 | 0 |
| Network 2 mapping and both 14-shard extractions | 25 | 25 | 0 |
| Corrected local Network 2 validation | 10 | 5 | 5 |
| Router, Europe PMC client, four arms, annotation/evaluator code | 20 | 20 | 0 |
| Actual fixed-candidate and live retrieval run | 10 | 0 | 10 |
| Human evidence annotation | 10 | 0 | 10 |
| Matched-policy evaluation and final results | 5 | 0 | 5 |
| **Total** | **100** | **70** | **30** |

The estimate describes completion of the pilot workflow, not model accuracy or scientific validity.

## Work packages

### WP1 — Revalidate Network 2 (5%)

Input files are local-only: the random-split baseline predictions; validated UniProt–Ensembl/Open Targets target bridge; source-specific direct-association Parquet; overall-direct association Parquet with joined disease names.

Run the corrected joint validator. Acceptance: all critical checks pass, including target mapping, release, aggregation semantics, provenance, uniqueness, disease labels and score range.

### WP2 — Candidate set and live retrieval (10%)

After WP1 passes:
- Draw up to three candidates per conformal prediction state, with a fixed seed of 42 and a maximum of nine.
- Remove observed DTI labels before candidate selection.
- Resolve compound titles via PubChem; preserve InChIKeys when names are unavailable.
- Run fixed, uncertainty-only, disease-only and combined retrieval against the identical candidate pool.
- Use a maximum five-document budget per candidate per strategy.
- Preserve stable publication identifiers, source URLs, exact query and retrieval timestamp.
- Record query failures rather than silently discarding them.

Acceptance: candidate audit confirms label blindness; candidate set is non-empty; JSONL retrieval records are non-empty, unique within candidate/strategy, drawn only from the fixed pool, still UNANNOTATED, and within the per-candidate budget.

### WP3 — Blinded annotation (10%)

Create a worksheet with one row per unique candidate-publication. Keep the retrieval strategy manifest and key private until labels are finalized.

For every row, provide direction label SUPPORT, CONTRADICT or UNKNOWN; evidence category MECHANISTIC, DISEASE_CONTEXT, COUNTER, SAFETY or OTHER; and a concise content-based rationale.

The annotation is performed by a human; no LLM or search query assigns the truth label. UNKNOWN is never converted to CONTRADICT.

Acceptance: every unique row has one valid direction label, category and rationale; resolve disagreements before unblinding.

### WP4 — Matched-policy evaluation (5%)

Expand each blinded annotation back to every strategy exposure using the private manifest/key. Compare retrieved documents and candidate coverage; annotation coverage; relevant-evidence precision (SUPPORT + CONTRADICT among annotated records); SUPPORT, CONTRADICT and UNKNOWN counts; counter-evidence share; pooled candidate-set counter-evidence recall.

The recall denominator is the union of CONTRADICT-labelled records retrieved by the four policies for these candidates. It is not exhaustive recall across all published literature.

Acceptance: evaluator emits all four strategy arms, actual denominators and caveats; no incomplete annotations or budget violations.

## Execution

On the research workstation run `python scripts/week11/run_week11_pipeline.py --phase prepare`. After manually annotating and freezing the worksheet, run `python scripts/week11/run_week11_pipeline.py --phase evaluate`. Inspect local execution status with `python scripts/week11/run_week11_pipeline.py --phase status`.

## Definition of 100%

The Week 11 pilot reaches 100% only when automated tests pass; corrected data-backed Network 2 validation passes locally; candidate set and candidate-build audit exist and confirm label blindness; four live retrieval strategy outputs exist with same candidate pool and budget; every unique publication is annotated with valid label/category/rationale; four-arm matched-policy evaluation completes and the final report is updated with actual results.

The full deep-learning fusion model, formal calibration research, complete embedding cache and external validation are not included in this pilot's 100% scope and must remain explicitly identified as future research.
