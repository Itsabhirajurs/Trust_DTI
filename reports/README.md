# TrustDTI — Reports and Experimental Outputs

This directory consolidates all experimental results, validation manifests, and formal course submissions for the TrustDTI research project.

## Directory Structure

| Folder | Stage / Phase | Description | Key Contents |
|---|---|---|---|
| [`stage0/`](stage0/) | Stage 1 (Data) | ChEMBL 37 & BindingDB extraction and profiling outputs | `chembl_profile_summary.json`, `chembl_sources.csv`, distribution figures |
| [`week2/`](week2/) | Stage 2 (Network 1) | Network 1 construction, scope lock, and leakage checks | `network1_v1_manifest.json`, `week2_scope_summary.json`, build logs |
| [`week07_pilot/`](week07_pilot/) | Stage 3 (Embeddings) | ChemBERTa & ESM-2 embedding pilot arrays and validation | `chemberta_pilot_embeddings.npz`, `esm2_pilot_embeddings.npz`, sample CSVs |
| [`weekly_reports/`](weekly_reports/) | Course Submissions | Formal weekly course reports, form text, figures, and PDFs | Subfolders for Weeks 2, 3, 4, 6, and 7, plus `_build/` |

---

## Weekly Submissions (`reports/weekly_reports/`)

- **Week 2**: Dataset selection, review, attributes, and project roadmap (`week02_dataset_selection/`)
- **Week 3**: Data pipeline implementation and profiling (`week03_data_pipeline/`)
- **Week 4**: Network 1 construction and leakage validation (`week04_network1/`)
- **Week 6**: Reproducible Network 1 validation (`week06_network1_validation/`)
- **Week 7**: Protein sequence audit and small-scale embedding pilot (`week07_embedding_pilot/`)
