# STATUS: where we are right now

*Last updated: 2026-10-25. Rewrite this file at the end of every session. History goes in `PROJECT_LOG.md`.*

## One-line state
**Stages 1 (Data) and 2 (Network 1) are built and verified. Stage 3 (Embeddings) has passed a small pilot only.** The full-dataset embeddings, DTI model training/evaluation, conformal calibration, disease anchors, and adaptive evidence-retrieval policy remain unfinished.

Network 1 contains 1,905,586 labelled drug–protein pairs (748,430 ACTIVE / 1,157,156 INACTIVE), 2,312 proteins, and 1,006,840 compounds, with four split definitions.

## Calendar
- The course Week 7 progress report covers the preliminary Stage 3 embedding pilot performed on 2026-10-25.
- Course report weeks and the project's 12-week build-plan weeks are different numbering systems.
- The pilot used Google Colab / NVIDIA Tesla T4. It was a smoke test, not the planned full-scale embedding run.

## Done
- **Stage 1 (Data):** ChEMBL 37 + BindingDB verified, extracted, and profiled; see `docs/stage0_report.md` and `reports/stage0/`.
- **Week 2 scope:** `src/ingest/analyze_scope_week2.py` → `reports/week2/`; decisions D-011–D-019 recorded.
- **Stage 2 (Network 1):** compound standardization and `src/network/build_network1.py`; Network 1 and leakage validation are documented. Network 1 validation script: `src/network/validate_network1.py`.
- **Stage 3 pilot (course Week 7):** audited 2,312 protein accessions, retrieved 2,312 human protein sequences from UniProt, and validated sequence lengths/characters. Generated 100 ChemBERTa vectors (100 × 384) and 20 ESM-2 vectors (20 × 320) on a Tesla T4. Local output alignment and finite-value checks passed. Model training has not started.
- **Tests:** most recent local test run returned 9 passed, 1 deselected.
- **Documentation:** Week 7 report, form entries, references, infographic, and pilot notebook have been prepared.

## Next actions (in order)
1. Synchronize the current GitHub documentation commit into the Windows working copy without overwriting the locally generated seven-file pilot result folder.
2. Add the locally validated NPZ embedding outputs and sample CSV files to `TrustDTI_Week07_Pilot_Results/`, then rerun the local artifact audit and commit those data artifacts.
3. Restart Colab and verify that the Week 7 notebook can reproduce the two small pilots; record dependency versions and output checksums.
4. Estimate storage and throughput before deciding full-scale embedding execution (about 1,006,840 compound rows, plus 2,312 protein rows).
5. Construct/evaluate a labelled DTI baseline using the existing random, drug-cold, target-cold, and temporal splits, then consider calibration as a separate stage.

## Open decisions
| Topic | State |
|---|---|
| ChemBERTa model/pooling | Week 7 smoke-test choice only; benchmark before locking final method |
| ESM-2 checkpoint/pooling | ESM-2 8M + mean pooling used only for the pilot; final choice open |
| Full-scale embedding hardware | Colab/Kaggle/HPC; estimate quotas, memory, storage, and recovery first |
| DTI baseline/fusion head | Not started |
| Conformal calibration | Not started |
| Curated protein–disease network | Planned after the DTI baseline stage |
| Adaptive evidence router and retrieval evaluation | Not started |

## Key numbers
- Network 1: 1,905,586 labelled pairs; 748,430 ACTIVE; 1,157,156 INACTIVE.
- Unique Network 1 compounds: 1,006,840.
- Unique Network 1 proteins: 2,312.
- Week 7 protein sequence retrieval: 2,312 / 2,312 returned and passed implemented checks.
- Week 7 pilot: ChemBERTa (100, 384); ESM-2 (20, 320); both with zero truncated inputs and finite outputs.

## Where things are
`README.md` → front door. `docs/PROJECT_GUIDE.md` → research design. `docs/PROJECT_LOG.md` → history. `DECISIONS.md` → method decisions. `docs/stages/` → stage teaching notes. `docs/weekly_reports/week07_embedding_pilot/` → course Week 7 evidence.
