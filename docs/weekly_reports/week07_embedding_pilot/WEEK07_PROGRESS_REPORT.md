# TrustDTI — Week 7 Progress Report

**Focus:** Protein sequence validation and a GPU-based compound/protein embedding pilot  
**Status:** Small-scale pilot completed; downstream DTI model training has not started.  
**Reporting date:** 25 October 2026

## 1. Objective

Validate protein inputs used by Network 1 and establish a reproducible workflow for representing compounds and proteins as numerical vectors (embeddings).

## 2. Protein identifier and sequence preparation

- Unique Network 1 protein accessions audited: **2,312**.
- Accessions mapped to human target metadata: **2,312 / 2,312**.
- Organism reported by matched metadata: *Homo sapiens*.
- UniProt sequence records retrieved: **2,312 / 2,312**.
- Unmatched accessions: **0**.
- Sequences passing the implemented amino-acid character checks: **2,312**.
- Reported and observed sequence lengths matched: **2,312**.

These results confirm successful retrieval and the implemented structural checks. They do not independently prove every sequence's biological correctness or suitability for every downstream task.

## 3. Compute environment

- Runtime: Google Colab.
- GPU: NVIDIA Tesla T4; reported memory approximately **14.56 GiB**.
- Python: **3.13.16**.
- PyTorch: **2.11.0+cu130**.
- Transformers: **4.57.6**.

## 4. Compound embeddings — ChemBERTa

- Model: `DeepChem/ChemBERTa-77M-MLM`.
- Pilot compounds: **100**.
- Embedding matrix: **100 × 384**; dimension per compound: **384**.
- Maximum token length observed: **163**.
- Truncated inputs: **0**.
- All embedding values finite: **Yes**.
- Model loading time observed: **10.88 s**.
- Inference time observed: **1.39 s**.

Mean pooling was applied to `last_hidden_state`, excluding special tokens and padding. The newly initialized pooler weights reported by the model loader were not used by this pooling code.

## 5. Protein embeddings — ESM-2

- Model: `facebook/esm2_t6_8M_UR50D`.
- Pilot proteins: **20**.
- Embedding matrix: **20 × 320**; dimension per protein: **320**.
- Maximum sequence length: **618 amino acids**.
- Truncated proteins: **0**.
- All embedding values finite: **Yes**.
- Model loading time observed: **2.66 s**.
- Inference time observed: **0.54 s**.

Mean pooling was applied to `last_hidden_state`, excluding special tokens and padding. The reported pooler weights were not used by the implemented method.

## 6. Integrity checks

The downloaded artifacts were validated on the local machine. The audit confirmed:

- Seven expected result files were present.
- ChemBERTa output shape was `(100, 384)`.
- ESM-2 output shape was `(20, 320)`.
- Compound InChIKeys and SMILES matched the saved input sample order.
- Protein accessions and sequences matched the saved input sample order.
- Both embedding matrices contained only finite values.
- The validation JSON recorded all ten shape, alignment, and numerical checks as passing.
- Existing project tests: **9 passed, 1 deselected**.

The pilot NPZ arrays and CSV inputs were validated in the local working copy. They are listed in `TrustDTI_Week07_Pilot_Results/README.md`; their binary contents still need to be synchronized from that working copy to GitHub after the local branch is reconciled with this documentation commit.

## 7. Visual and reproducible artifacts

- Infographic: [`week07_infographic.svg`](week07_infographic.svg).
- Reproducible notebook: [`week07_embedding_pilot.ipynb`](../../../notebooks/week07/week07_embedding_pilot.ipynb).
- Form text: [`WEEK07_FORM_ENTRIES.md`](WEEK07_FORM_ENTRIES.md).
- Model/data references: [`references.md`](references.md).

## 8. Limitations and interpretation

This was a **small-scale embedding and pipeline-validation experiment**. It does not demonstrate DTI predictive performance, uncertainty calibration, conformal coverage, or improved biomedical evidence acquisition. The 100 compounds and 20 proteins are independent encoder smoke-test samples, not a labelled drug–target evaluation set.

Finite values and correct identifier alignment are technical integrity results; they do not prove that the representations are biologically informative or improve prediction. The next stage must construct labelled compound–protein pairs and evaluate a baseline on leakage-aware splits.

## 9. Next steps

1. Sync the locally validated NPZ arrays and pilot CSV inputs into the repository and verify the resulting commit.
2. Re-run the notebook after a clean Colab restart and confirm reproducibility.
3. Define the labelled DTI training/evaluation dataset and a simple baseline.
4. Evaluate performance and leakage-aware splits before adding calibration and adaptive evidence acquisition.
5. Estimate storage, throughput, and failure-recovery needs before larger-scale embedding generation.

## 10. Week 7 completion status

**Completed:** preliminary protein accession audit, sequence retrieval and checks, GPU preflight, 100-compound ChemBERTa pilot, 20-protein ESM-2 pilot, output alignment/numerical validation, local artifact audit, and documentation.

**Not started:** full-dataset embedding generation, DTI model training/evaluation, uncertainty calibration, disease-anchor integration, and adaptive evidence retrieval.
