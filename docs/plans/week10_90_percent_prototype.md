# Week 10: 90% engineering-prototype sprint

## Acceptance target

The 90% milestone means a reproducible engineering prototype with the following pieces connected and tested. It does not mean that the scientific hypothesis has been proven.

1. Complete Network 2 overall-direct association extraction and disease metadata join.
2. Preserve the source-specific association network separately.
3. Validate target/disease coverage, schema, nulls, key uniqueness and score ranges.
4. Freeze a deterministic uncertainty × disease-anchor router with tests.
5. Retrieve Europe PMC publication metadata/abstracts with provenance and explicit failure handling.
6. Build one label-blind fixed candidate set.
7. Compare fixed, uncertainty-only, disease-only and combined retrieval at the same per-candidate cap.
8. Provide an annotation worksheet, evaluator, reproducible command path and limitations.

## Current branch implementation

The feature branch `work/90-percent-prototype` adds:

- `src/network/router.py`
- `src/retrieval/europe_pmc.py`
- `src/retrieval/pipeline.py`
- `scripts/week10/build_network2_overall_direct.py`
- `scripts/week10/build_candidate_set.py`
- `scripts/week10/run_retrieval_demo.py`
- `scripts/week10/prepare_annotation_sheet.py`
- `scripts/week10/evaluate_retrieval.py`
- unit tests for routing, retrieval, provenance and matched-budget evaluation.

## Owner-side data gate

The Open Targets Parquet datasets and Network 1 data are local-only. After pulling this branch, run:

```bash
python -m pytest -q

# Build and preserve both separate Network 2 association products.
python scripts/week09/build_network2_direct_associations.py
python scripts/week10/build_network2_overall_direct.py
python scripts/week10/validate_network2.py

# Start with a small, reproducible 9-candidate retrieval pilot.
python scripts/week10/build_candidate_set.py --per-state 3 --max-candidates 9
python scripts/week10/run_retrieval_demo.py --budget-per-candidate 5
python scripts/week10/prepare_annotation_sheet.py
# Annotate each unique candidate-publication once. Keep the strategy key
# and manifest private from the annotator until the labels are finalized.
```

Manually annotate each unique candidate-publication once. Keep `retrieval_strategy_manifest.csv` and `retrieval_strategy_key.csv` separate from the annotator; the worksheet itself hides strategy and query intent. After annotations are finalized, run:

```bash
python scripts/week10/evaluate_retrieval.py --budget-per-candidate 5
```

The evaluator uses the private manifest/key to expand each annotation back onto the retrieval policies that found the publication.

The Week 9 `association_by_datasource_direct` build is run first and remains a separate output. The overall-direct builder uses its own official score product rather than averaging the source-level rows. The validation step requires both products and confirms their identifiers, provenance and score ranges before candidate sampling.

## Research safeguards

- The candidate builder discards the observed DTI label before sampling; it does not use test labels to choose candidates.
- The router is deterministic and does not use an LLM.
- Query intent is not an evidence truth label.
- UNKNOWN remains UNKNOWN.
- A missing literature result is not CONTRADICT.
- Source-specific and overall association scores are not averaged together.
- All evidence records retain stable identifiers, original queries, URLs and UTC retrieval times.
- The current counter-evidence recall is pooled within the retrieved candidate set; it is not exhaustive recall across all published literature.
- No performance improvement is claimed until the same fixed candidates are evaluated with human-adjudicated annotations.
