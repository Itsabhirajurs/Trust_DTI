# Week 6 Progress Report — TrustDTI



## Tasks & Work Completed During This Week



1. Reviewed the existing TrustDTI repository and confirmed the local project environment using Python 3.12.6.

2. Executed the existing automated test suite: 9 tests passed and 1 test was deselected.

3. Implemented a reusable Network 1 validation script at `src/network/validate_network1.py`.

4. Validated the local Network 1 dataset against the committed manifest. All 13 validation checks passed.

5. Confirmed 1,905,586 drug–protein pairs: 748,430 ACTIVE and 1,157,156 INACTIVE.

6. Verified that split distributions match the manifest, there are no duplicate compound–protein pairs, and the drug-cold and target-cold partitions have zero group overlaps.

7. Verified temporal split handling: calibration data precedes 2020, test data starts in 2020, and 659,861 records without publication years remain unassigned to the temporal split.

8. Documented the validation methodology, results, limitations and next steps.



## Roadblocks & Challenges Encountered



The raw and processed datasets are excluded from Git tracking, so the validation requires access to the local data files. The default test run also emitted dependency and pytest configuration warnings, although the tests passed. GPU-based embedding generation has not yet started and remains part of the planned next stage.



## Plan & Roadmap for Next Week



Prepare the Stage 3 GPU workflow for ChemBERTa compound embeddings and ESM-2 protein embeddings. Test suitable model checkpoints and pooling strategies on a small pilot, plan the embedding cache and estimate GPU memory and runtime requirements before scaling up. Prepare classical fingerprint baselines for later model evaluation.



## Technologies / Tools Used



Python 3.12.6, pandas, PyArrow/Parquet, pytest, Git, GitHub and Git Bash.



## Development Hours Invested



Enter the actual hours spent on this work before submitting.



## Key Learning Outcome



Reproducible dataset validation is essential before model training. Drug-cold and target-cold splits test different forms of generalisation, while missing publication years limit temporal evaluation.



## GitHub Repository / Commit URL (optional)



Add the final commit URL after committing and pushing the Week 6 changes.



## Supporting Document / Demo Link (required)



https://github.com/Itsabhirajurs/Trust_DTI/tree/main/docs/weekly_reports/week06_network1_validation



This link will become accessible after the Week 6 report files are pushed to GitHub.
