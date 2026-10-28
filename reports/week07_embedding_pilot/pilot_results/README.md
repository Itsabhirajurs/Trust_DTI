# Week 7 Pilot Output Inventory

The local pilot completed and was audited. The workstation folder was:

`reports/week07_embedding_pilot/pilot_results/`

Expected output files:
- `chemberta_pilot_embeddings.npz` — 100 × 384 float32 compound embeddings plus aligned identifiers and SMILES.
- `chemberta_pilot_summary.json` — model, timing, shape, and truncation summary.
- `esm2_pilot_embeddings.npz` — 20 × 320 float32 protein embeddings plus aligned accessions and sequences.
- `esm2_pilot_summary.json` — model, timing, shape, and truncation summary.
- `pilot_compounds.csv` — 100 sampled compound records used in the pilot.
- `pilot_proteins.csv` — 20 sampled protein sequence records used in the pilot.
- `week07_pilot_validation.json` — identifier alignment and numerical validation checks.

**Repository sync note:** those seven files exist and passed local audit in the user's workstation. They have not yet been uploaded by the GitHub connector because the binary NPZ/CSV files are not available in the connected workspace. After synchronizing the remote documentation commit into the local checkout, add the seven local files with Git and push them. Do not add raw ChEMBL/BindingDB data, the `.venv`, or caches.

Recheck the exact file list and run the local audit before committing.
