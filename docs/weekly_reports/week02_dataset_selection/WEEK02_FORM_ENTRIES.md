# Week 2: weekly progress form (copy-paste)

**Theme:** dataset selection, review, attribute understanding, planning.

---

### TASKS & WORK COMPLETED DURING THIS WEEK
```
1. Finalised project scope with the team: a universal drug–protein network covering all human single-protein targets, reported per protein family (chosen over kinase-only; trade-offs documented).
2. Reviewed and selected data sources: ChEMBL 37 (primary bioactivity data), BindingDB 202609 (cross-check), UniProt (protein IDs), Open Targets/DisGeNET (disease links, later), PubMed/PubTator (evidence, later).
3. Studied the ChEMBL schema: mapped the 11 tables we need and the join path measurement → assay → target → protein → family.
4. Built an attribute dictionary of 21 key fields (potency, units, relation, pChEMBL, confidence, assay type, source, year, InChIKey, UniProt ID).
5. Verified two data traps on real rows (imatinib): censored values like "IC50 > 30,000 nM"; a common pChEMBL filter keeps only 833 of 4,878 rows and drops all 1,335 censored ones.
6. Fixed the labelling rule: ACTIVE / INACTIVE / UNTESTED; untested or "inconclusive" is never treated as inactive.
7. Locked the 12-week plan (10 build + 2 buffer weeks) with weekly gates and a dated decision log (DECISIONS.md).
```

### ROADBLOCKS & CHALLENGES ENCOUNTERED
```
The ChEMBL bulk download (5.8 GB) failed repeatedly on our network and left a corrupt partial file; resolved by resuming on another network and accepting it only after the checksum matched. Planning documents disagreed on scope (kinase-only vs all proteins) and schedule; resolved with the team and recorded in DECISIONS.md.
```

### PLAN & ROADMAP FOR NEXT WEEK
```
Build the data pipeline: verify and extract both databases, profile proteins/compounds/pairs per family, check data sources and quality, measure ChEMBL–BindingDB overlap, and publish a Stage 0 data report with an open-issue list.
```

### TECHNOLOGIES / TOOLS USED
```
ChEMBL 37, BindingDB, UniProt, ChEMBL web client, Python, pandas, Jupyter, SQLite, Git/GitHub
```

### DEVELOPMENT HOURS INVESTED
```
15
```
*(Planned load is 15 h/week. Replace with your actual hours.)*

### KEY LEARNING OUTCOME
```
How a value was measured (censoring, units, assay, source) matters as much as the value itself.
```

### GITHUB REPOSITORY / COMMIT URL
```
https://github.com/Itsabhirajurs/Trust_DTI/commit/c6fd1553d9e19f6a331fc5dbecb096cab6134b14
```
*(Commit with the verified dataset manifest and ChEMBL schema notes. Alternative: the scope/decision-log commit `2430958c632a98171afd075aa9267ac5e0532c96`.)*

### SUPPORTING DOCUMENT / DEMO LINK (OPTIONAL)
```
<paste your Google Drive folder link for this week's files>
```
*(Or link the GitHub folder: https://github.com/Itsabhirajurs/Trust_DTI/tree/main/docs/weekly_reports/week02_dataset_selection)*

---

## Files in this folder

| File | What it shows |
|---|---|
| `Week02_Dataset_Selection_Report.pdf` | 3-page summary of this week: the one to open first |
| `W2_01_system_pipeline.png` | The whole TrustDTI system: offline build and online query |
| `W2_02_data_source_selection.png` | Each data source, its role, and why it was chosen |
| `W2_03_chembl_schema_join_path.png` | How ChEMBL tables link a measurement to drug, protein and family |
| `W2_04_labels_and_censored_data.png` | The three-state label rule and the censored-value trap |
| `W2_05_project_roadmap.png` | The 12-week plan and where we are |
| `W2_06_attribute_dictionary.csv` | Key data fields: meaning, example, why they matter |
| `references.md` | Data sources and literature we relied on |
