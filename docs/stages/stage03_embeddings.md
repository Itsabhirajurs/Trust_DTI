# Stage 3 — Embeddings: what the pilot did

## Why embeddings exist

A neural model cannot directly learn from a chemical SMILES string or a protein's amino-acid letters as ordinary text. An encoder converts each input into a row of numbers, called an embedding. Downstream, a drug–target interaction (DTI) model can combine a compound vector with a protein vector to predict an interaction.

## The Week 7 pilot

| Input | Pretrained encoder | Pilot size | Output shape |
|---|---|---:|---:|
| Compound SMILES | DeepChem/ChemBERTa-77M-MLM | 100 compounds | 100 × 384 |
| Protein amino-acid sequence | facebook/esm2_t6_8M_UR50D | 20 proteins | 20 × 320 |

Both runs used a Google Colab NVIDIA Tesla T4 GPU. No pilot input was truncated, all vector values were finite, and identifiers were checked against the saved input order.

## What is mean pooling?

The encoder returns a vector for each token (SMILES token or amino acid). Mean pooling averages the vectors belonging to real input tokens into one fixed-length vector per molecule or protein. The pilot excludes padding and special boundary tokens. This is a baseline choice, not a proven best method.

## What did we prove?

We proved that the chosen checkpoints can load and produce correctly shaped, finite embeddings for small samples, and that the output rows align with the corresponding compound/protein identifiers.

We did **not** prove that the embeddings predict binding, that a DTI model is accurate, that uncertainty is calibrated, or that the future evidence-retrieval policy improves results. Those require labelled drug–target pairs, leakage-aware evaluation, and separate experiments.

## Next stage gates

1. Preserve the inputs, model IDs, pooling logic, output shapes, and runtime measurements.
2. Confirm the notebook runs after a clean runtime restart.
3. Construct the labelled compound–protein dataset from Network 1.
4. Train and evaluate a simple baseline with the existing random, drug-cold, target-cold, and temporal splits.
5. Only after baseline evaluation, proceed to calibration and the evidence-allocation question.

## Be able to explain

- What does a row of shape (100, 384) mean?
- Why can a finite embedding still be unhelpful for prediction?
- Why should training/test leakage be checked separately from embedding generation?
- Why is an encoder smoke test not evidence of DTI accuracy?
