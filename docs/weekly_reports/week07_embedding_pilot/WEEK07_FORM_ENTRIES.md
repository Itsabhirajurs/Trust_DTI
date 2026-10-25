# Week 7 Progress Form — TrustDTI

Use these entries for the course form. Verify the development-hours field reflects the time actually invested.

## Tasks & Work Completed During This Week
Completed protein-sequence preparation and the initial GPU embedding pipeline for TrustDTI. Audited 2,312 unique Network 1 protein accessions; all mapped to human target metadata. Retrieved 2,312 UniProt sequences with zero unmatched accessions, and all passed the implemented amino-acid checks with reported and actual sequence lengths matching. Prepared reproducible samples of 100 compounds and 20 human proteins. Generated ChemBERTa compound embeddings (100 × 384) and ESM-2 protein embeddings (20 × 320) on an NVIDIA Tesla T4 in Google Colab. Neither pilot truncated inputs, and all output values were finite. Verified identifier/input alignment and the saved NPZ files locally. Existing project tests: 9 passed, 1 deselected. This establishes a small-scale embedding pipeline; DTI model training and predictive evaluation have not started.

## Roadblocks & Challenges Encountered
The Windows environment did not have PyTorch or Transformers installed, and a usable local GPU environment was not established, so the pilot was moved to Google Colab. The package installer warned about dependency conflicts with preinstalled Hugging Face Hub consumers; model imports and inference succeeded, so unnecessary upgrades were avoided. NumPy object arrays for identifier text initially failed safe loading; they were converted to Unicode arrays and verified with allow_pickle=False. Both model loaders reported newly initialized pooler weights, but the pilot code used last_hidden_state and custom mean pooling instead.

## Plan & Roadmap for Next Week
Sync the verified pilot output files into GitHub and confirm notebook reproducibility from a clean runtime. Define a labelled drug–target pair dataset and implement a simple baseline. Evaluate with the project's leakage-aware splits before beginning uncertainty calibration. Estimate compute and storage needs before any full-dataset embedding run.

## Technologies / Tools Used
Python, pandas, NumPy, PyArrow, requests, UniProt REST API, Google Colab, NVIDIA Tesla T4, PyTorch 2.11.0+cu130, Hugging Face Transformers 4.57.6, DeepChem/ChemBERTa-77M-MLM, facebook/esm2_t6_8M_UR50D, pytest, Git and GitHub.

## Development Hours Invested
Enter the actual hours invested. The value entered previously was 10 hours; retain that only if it is accurate.

## Key Learning Outcome
Learned to retrieve and validate UniProt protein sequences and transform SMILES and amino-acid sequences into numerical vectors using pretrained language models. Understood GPU cloud workflows, mean pooling over last hidden states, identifier alignment, output-shape checks and safe NumPy serialization. Most importantly, distinguished technical embedding-pipeline validation from demonstrated DTI predictive performance.

## GitHub Repository / Commit URL (optional)
https://github.com/Itsabhirajurs/Trust_DTI

## Supporting Document / Demo Link
https://github.com/Itsabhirajurs/Trust_DTI/tree/main/docs/weekly_reports/week07_embedding_pilot
