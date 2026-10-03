# Week 4: weekly progress form (copy-paste)

**Theme:** lock the dataset rules, then build Network 1 (the clean, labelled, leakage-checked drug–protein table).

---

### TASKS & WORK COMPLETED DURING THIS WEEK
```
1. Locked the dataset scope from real data: ran a scope analysis over all 8.3M records and recorded 9 decisions (thresholds, endpoints, inactive rule, minimum data per protein, temporal cutoff, compound identity, splits) with the numbers behind each.
2. Standardised all 1,559,417 compounds with RDKit: stripped salts, neutralised charges, computed a canonical parent InChIKey and a Bemis–Murcko scaffold for each (only 1 unparseable; 50,339 salts/mixtures stripped).
3. Built Network 1: aggregated 8.3M measurements into 1,905,586 labelled drug–protein pairs (748,430 ACTIVE, 1,157,156 INACTIVE) over 2,312 proteins and 1,006,840 compounds.
4. Created the four train/test splits (random, drug-cold by scaffold, target-cold by protein, temporal pre-2020 vs 2020+), each with a calibration slice, and an automated leakage check — which PASSED (no scaffold or protein on both sides).
5. Wrote and committed the pipeline scripts (src/network/standardize_compounds.py, build_network1.py) and a reproducible manifest; aggregated repeated measurements by median and flagged 18,078 high-disagreement pairs.
6. Produced the interactive explainers and a repo-based "memory" system (project guide, status, diary, stage notes) so work continues cleanly across IDE sessions.
```

### ROADBLOCKS & CHALLENGES ENCOUNTERED
```
No local GPU, so Stage 3 embeddings are scheduled on a Kaggle GPU (not a blocker for Network 1). The first Network 1 build was silently killed by the OS — holding all 8.3M rows with their free-text comment column plus Python set operations exceeded the laptop's 16 GB RAM; fixed by dropping the text column early, using category types, and replacing Python sets with vectorised pandas joins (memory 2.3 GB → 1.6 GB). Two further build bugs were caught and fixed (a read-only-array shuffle and a non-serialisable missing-value key). Measurement disagreement is real: 23% of repeat-measured pairs differ by ≥1 log unit, so we aggregate by median and flag the disagreements.
```

### PLAN & ROADMAP FOR NEXT WEEK
```
Stage 3 (representation): embed every Network 1 compound with ChemBERTa and every protein with ESM-2 (frozen, on a Kaggle GPU), caching the vectors keyed by identifier; handle giant proteins (longest 34,350 residues vs ESM-2's ~1,024 limit) by truncation. Build classical fingerprint baselines (logistic regression, XGBoost) as the floor the trained model must beat, and sanity-check that similar compounds and same-family proteins cluster.
```

### TECHNOLOGIES / TOOLS USED
```
Python 3.12, RDKit, pandas, PyArrow/Parquet, NumPy, SQLite, Git/GitHub (planned next: ChemBERTa, ESM-2, PyTorch, Kaggle GPU)
```

### DEVELOPMENT HOURS INVESTED
```
15
```
*(Planned weekly load. Replace with your actual hours.)*

### KEY LEARNING OUTCOME
```
How dataset-labelling decisions (activity thresholds, handling censored measurements, and leakage-safe train/test splits) determine everything a model can possibly learn — the data design matters as much as the model.
```

### GITHUB REPOSITORY / COMMIT URL (optional)
```
https://github.com/Itsabhirajurs/Trust_DTI/commit/a88809bb84e55880d377cfe0a101eca7a8cff499
```

### SUPPORTING DOCUMENT / DEMO LINK  (mandatory)
```
<paste your Google Drive link for the Week 4 folder here>
```
*(Upload this folder's PDF + figures to your Drive "Week 4" folder, as you did for Weeks 2 and 3, and paste the share link. GitHub alternative: https://github.com/Itsabhirajurs/Trust_DTI/tree/main/docs/weekly_reports/week04_network1)*

---

## Files in this folder
| File | What it shows |
|---|---|
| `Week04_Network1_Report.pdf` | 4-page summary — open this first |
| `W4_01_construction_workflow.png` | The 5 steps that build Network 1 |
| `W4_02_label_logic.png` | How each pair gets ACTIVE / INACTIVE / excluded |
| `W4_03_label_counts.png` | The finished table's label counts |
| `W4_04_splits_explained.png` | The four splits and the question each answers |
| `W4_05_split_distributions.png` | Train / calibration / test for each split |
| `W4_06_week2_decisions.png` | The 9 scope decisions and their evidence |
| `references.md` | Data, tools, decisions, literature |
