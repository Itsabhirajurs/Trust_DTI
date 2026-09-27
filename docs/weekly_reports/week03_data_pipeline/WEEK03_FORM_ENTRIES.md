# Week 3: weekly progress form (copy-paste)

**Theme:** coding the data pipeline, profiling results, trial and error.

---

### TASKS & WORK COMPLETED DURING THIS WEEK
```
1. Set up a reproducible repo: moved it out of OneDrive, pinned Python packages and data versions, and wrote a data manifest with checksums.
2. Downloaded and verified ChEMBL 37 (5.8 GB, SHA-256) and BindingDB 202609 (MD5); extracted the 30 GB database (row count matches the release notes).
3. Wrote the extraction pipeline (src/ingest): 8.3M measurements covering 5,738 human proteins, 1.56M compounds and 5.06M drug–protein pairs; streamed the 9 GB BindingDB file down to 2.34M human records.
4. Profiled the data by protein family, source, assay quality, endpoint and missing values, with plots (interaction skew, potency distribution).
5. Measured ChEMBL–BindingDB overlap: the naive count is 13× inflated because each database copies the other; BindingDB would add only ~8% new pairs.
6. Added 10 automated tests (e.g. censored values survive extraction). A full re-run reproduced all 16 result files byte-for-byte. Published the Stage 0 data report.
```

### ROADBLOCKS & CHALLENGES ENCOUNTERED
```
Found and fixed silent data issues: blank/corrupt lines in the BindingDB file (caught by reconciling row counts), undocumented ">>"/"<<" operators, and a notebook filter that over-counted censored rows. PubChem screening data distorts per-family potency (oxidoreductase median 4.8 vs 6.4 without it), so it is flagged for threshold design. A full-database test took ~1 h, so it now runs separately from the fast test suite.
```

### PLAN & ROADMAP FOR NEXT WEEK
```
Lock the dataset rules from the real numbers: which endpoints count (IC50/Ki/Kd/EC50 vs screening "Potency"), activity thresholds that control for data source, measured-inactive rules, minimum data per protein, and a time-split cutoff. Write the specification into DECISIONS.md, then start building the clean network.
```

### TECHNOLOGIES / TOOLS USED
```
Python 3.12, pandas, PyArrow/Parquet, SQLite, matplotlib, pytest, Jupyter, curl + SHA-256/MD5, Git/GitHub
```

### DEVELOPMENT HOURS INVESTED
```
15
```
*(Planned load is 15 h/week. Replace with your actual hours.)*

### KEY LEARNING OUTCOME
```
Verify, don't assume: checksums, row-count reconciliation and source checks caught errors that would have silently changed results.
```

### GITHUB REPOSITORY / COMMIT URL
```
https://github.com/Itsabhirajurs/Trust_DTI/compare/2430958c632a98171afd075aa9267ac5e0532c96...9df4a36bef17fdea2b57e83ff7561d8ee5a51f9d
```
*(Shows every pipeline commit together. For a single commit, use the Stage 0 report commit: https://github.com/Itsabhirajurs/Trust_DTI/commit/9df4a36bef17fdea2b57e83ff7561d8ee5a51f9d)*

### SUPPORTING DOCUMENT / DEMO LINK (OPTIONAL)
```
<paste your Google Drive folder link for this week's files>
```
*(Or link the GitHub folder: https://github.com/Itsabhirajurs/Trust_DTI/tree/main/docs/weekly_reports/week03_data_pipeline)*

---

## Files in this folder

| File | What it shows |
|---|---|
| `Week03_Data_Pipeline_Report.pdf` | 4-page summary of this week: the one to open first |
| `W3_01_code_workflow.png` | Pipeline steps, scripts, outputs and checks |
| `W3_02_headline_numbers.png` | Key numbers of the dataset at a glance |
| `W3_03_family_counts.png` | Drug–protein pairs per protein family |
| `W3_04_data_sources.png` | Where the records come from (and which lack a year) |
| `W3_05_overlap_naive_vs_independent.png` | Why the ChEMBL–BindingDB overlap was 13× inflated |
| `W3_06_pubchem_confounding.png` | How screening data shifts family potency |
| `W3_07_interaction_skew.png` | Partners per protein and per compound (log scale) |
| `W3_08_pchembl_distribution.png` | Potency distribution, overall and top 3 families |
| `W3_09_trial_and_error_log.png` | What went wrong, how we caught it, what changed |
| `references.md` | Data sources, tools and literature |
