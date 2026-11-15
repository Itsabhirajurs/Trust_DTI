# Week 10 scripts

## Required run order

1. Validate the existing Network 2 products: `python scripts/week10/validate_network2.py`
2. Build a fixed label-blind candidate set: `python scripts/week10/build_candidate_set.py --per-state 3 --max-candidates 9`
3. Run all four Europe PMC strategies: `python scripts/week10/run_retrieval_demo.py --budget-per-candidate 5`
4. Prepare the blinded worksheet: `python scripts/week10/prepare_annotation_sheet.py`
5. After labels are finalized, evaluate: `python scripts/week10/evaluate_retrieval.py --budget-per-candidate 5`

Do not build candidates before the Network 2 validation audit passes.

| Script | Responsibility |
|---|---|
| `build_network2_overall_direct.py` | Build official overall-direct table and join disease labels |
| `validate_network2.py` | Validate bridge and both association products |
| `build_candidate_set.py` | Create a fixed, label-blind candidate set |
| `run_retrieval_demo.py` | Run fixed, uncertainty-only, disease-only and combined Europe PMC strategies |
| `prepare_annotation_sheet.py` | Deduplicate candidate-publication pairs and create blinded worksheet |
| `evaluate_retrieval.py` | Compare four arms after annotation |

Related code: `src/network/router.py`, `src/retrieval/europe_pmc.py`, `src/retrieval/pipeline.py`. The source-specific builder stays at its original Week 9 path: `scripts/week09/build_network2_direct_associations.py`.

Large Parquet tables, downloads, abstracts and private annotation keys remain local.
