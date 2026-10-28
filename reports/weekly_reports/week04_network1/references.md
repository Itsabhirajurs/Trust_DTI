# Week 4 references

## What was built (all in the repo)
| What | Where |
|---|---|
| Week 2 scope analysis | `src/ingest/analyze_scope_week2.py` → `reports/week2/` |
| Compound standardisation | `src/network/standardize_compounds.py` → `data/interim/compounds_standardized.parquet` |
| Network 1 construction | `src/network/build_network1.py` → `data/processed/network1_v1.parquet` |
| Network 1 manifest (counts, splits, leakage check) | `reports/week2/network1_v1_manifest.json` |
| The decisions behind it | `DECISIONS.md` D-011 … D-019 |

Repository: https://github.com/Itsabhirajurs/Trust_DTI

## Key numbers (this build)
1,905,586 labelled pairs · 748,430 ACTIVE / 1,157,156 INACTIVE · 2,312 proteins · 1,006,840 compounds ·
333,583 scaffold groups · leakage check PASSED (all overlaps 0). Source: `reports/week2/network1_v1_manifest.json`.

## Tools and documentation
- RDKit (salt stripping, standardisation, Murcko scaffolds): https://www.rdkit.org/docs/
- RDKit MolStandardize (LargestFragmentChooser, Uncharger): https://www.rdkit.org/docs/source/rdkit.Chem.MolStandardize.html
- pandas: https://pandas.pydata.org/docs/ · Apache Arrow / Parquet: https://arrow.apache.org/docs/python/
- ChEMBL schema: https://chembl.gitbook.io/chembl-interface-documentation/

## Literature
- Bemis G.W., Murcko M.A. *The properties of known drugs. 1. Molecular frameworks.* J. Med. Chem. 39, 1996. (The scaffold definition used for the drug-cold split.)
- Bento A.P. et al. *The ChEMBL bioactivity database: an update.* Nucleic Acids Research 42(D1), 2014. (pChEMBL = −log10 molar potency; exact values only.)
- Zdrazil B. et al. *The ChEMBL Database in 2023.* Nucleic Acids Research 52(D1), 2024.
- On leakage-aware splitting for drug–target models: scaffold (drug-cold) and target (protein-cold) splits are standard practice for honest generalisation estimates in cheminformatics; random splits overstate performance.

## Note on method
Thresholds and endpoint choices were set from the data (`reports/week2/week2_scope_summary.json`), not from convention.
The active/inactive cut (pChEMBL ≥6.5 / ≤5.0 with a gray exclusion band) and the decision to label only from
dose-response affinities are recorded with their evidence in DECISIONS.md D-011/D-012.
