# Stage teaching notes

One file per pipeline stage, written as the stage is explained. Each note covers why the stage exists, why those tools, the task, real results, open decisions, and questions to check understanding.

| # | Stage | Status | Note |
|---|---|---|---|
| 1 | Data | done, verified | [stage01_data.md](stage01_data.md) |
| 2 | Network 1 | built and verified | [stage02_network1.md](stage02_network1.md) |
| 3 | Embeddings (ChemBERTa, ESM-2) | small pilot passed; full-scale cache pending | [stage03_embeddings.md](stage03_embeddings.md) |
| 4 | Classical baseline before fusion | runner and tests added; actual dataset run pending | [baseline_before_fusion.md](baseline_before_fusion.md) |
| 5 | Fusion head and evaluation | not started; baseline comparison first | planned |
| 6 | Conformal calibration | baseline prediction-set diagnostic only; formal calibration analysis pending | not yet written |
| 7 | Network 2 (disease anchor) | planned | not yet written |
| A–F | Online half: query, router, evidence retrieval, extraction, synthesis, report | planned | not yet written |

**To add a note:** follow the structure of the earlier stage notes, add real numbers and unresolved choices, and update this table and the project log.
