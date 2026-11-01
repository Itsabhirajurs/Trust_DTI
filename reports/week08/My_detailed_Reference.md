# TrustDTI — Week 08 Detailed Reference

> **Purpose:** A plain-language, end-to-end record of what was built, tested, measured, discovered, and left for Week 09. This is a learning reference as well as a technical record. It distinguishes completed work from hypotheses and pending investigations.

**Project:** TrustDTI — uncertainty-aware drug–target interaction (DTI) prediction and evidence retrieval  
**Week covered:** Week 08  
**Reference location:** \`reports/week08/My_detailed_Reference.md\`

---

## 1. Start with the big picture: what is TrustDTI trying to do?

TrustDTI is being developed to investigate this question:

> Does using calibrated uncertainty from drug–target interaction predictions, together with disease relevance, help a literature-evidence retrieval system find more useful supporting evidence and more counter-evidence than a fixed retrieval strategy?

In simpler words:

1. A model receives a drug and a protein.
2. It estimates whether the drug and protein interact.
3. We examine how reliable that prediction is, rather than trusting every probability equally.
4. A later evidence-retrieval system will use the prediction and its uncertainty to search scientific literature.
5. The system should look for evidence that supports a prediction **and** evidence that challenges it.
6. We will compare this adaptive approach with a fixed retrieval strategy under the same candidate set and search budget.

**Important:** Week 08 did not complete the final deep-learning model, disease network, literature retrieval system, or the full research comparison. Week 08 built and evaluated a classical reference baseline and investigated a temporal-performance problem. Those results provide a foundation for the next stage.

## 2. Where the project stood before Week 08

The project already had three important foundations:

| Stage | What existed before this week's baseline work |
|---|---|
| Stage 1 — Data profiling | ChEMBL 37 and BindingDB extraction/profiling work had been documented. |
| Stage 2 — Network 1 | A labelled drug–protein pair dataset and four evaluation split assignments had been created. |
| Stage 3 — Embedding pilot | Small ChemBERTa and ESM-2 embedding pilots had been completed in Week 07. |

The Week 07 pilot used:
- ChemBERTa: 100 compounds, embedding dimension 384.
- ESM-2: 20 proteins, embedding dimension 320.

Those were embedding-generation pilots. They were **not** used by the Week 08 classical baseline.

## 3. Understand the actual data used

### 3.1 Network 1: the main DTI dataset

Local file:

\`data/processed/network1_v1.parquet\`

Previously validated dataset counts:

| Property | Count |
|---|---:|
| Drug–protein pair rows | 1,905,586 |
| ACTIVE pairs | 748,430 |
| INACTIVE pairs | 1,157,156 |
| Distinct compounds | 1,006,840 |
| Distinct proteins | 2,312 |
| Distinct scaffold groups | 333,583 |

One row represents one compound–protein pair and its assigned label, alongside measurement summaries, experimental flags, chemical scaffold information, year, and split assignments.

The dataset has 19 columns. Some important ones are:

| Column | Meaning |
|---|---|
| \`pik\` | Standardised parent compound identifier (full InChIKey). |
| \`accession\` | Protein identifier, mapped to the protein metadata. |
| \`family_l1\` | Broad protein-family category, such as Enzyme or Membrane receptor. |
| \`label\` | The final Network 1 class: ACTIVE or INACTIVE. |
| \`median_p\` | Median pChEMBL-like potency value from qualifying exact measurements, when available. |
| \`n_exact\` | Number of exact affinity measurements used in the aggregation. |
| \`iqr\` | Interquartile range of the exact-measurement potency values. |
| \`has_cens\` | Flag for qualifying censored affinity evidence. |
| \`has_comment\` | Flag for an activity comment matching the inactive-comment rule. |
| \`has_qhts\` | Flag for qualifying qHTS inactive evidence. |
| \`scaffold\`, \`scaffold_group\` | Chemical framework information; scaffold groups are used in the drug-cold split. |
| \`year\` | Earliest document year associated with the compound–protein pair in the Network 1 build. |
| \`split_random\` | Random partition assignment. |
| \`split_drugcold\` | Scaffold-group-held-out partition assignment. |
| \`split_targetcold\` | Protein-accession-held-out partition assignment. |
| \`split_temporal\` | Time-based partition assignment. |
| \`high_disagreement\` | True when the aggregated IQR is at least 1.0. |

### 3.2 Where the molecule structures come from

The main Network 1 table contains the compound identifier, but the standardised compound table stores the molecular structure:

\`data/interim/compounds_standardized.parquet\`

It contains 1,559,417 rows and seven columns, including:
- \`parent_smiles\`: standardised parent molecular structure as SMILES text.
- \`parent_inchikey\`: full parent InChIKey used to match the compound.
- \`scaffold\`: core chemical framework.
- \`had_multi_fragment\`: whether the input contained multiple fragments.
- \`status\`: standardisation status.
- \`molregno\`: ChEMBL molecule registration number.
- \`inchikey_block\`: first block of the InChIKey.

The local audit found exact full-InChIKey matches for all 1,006,840 distinct Network 1 compound IDs: **100% identifier coverage**.

However, there is an unresolved data-quality issue:
- 5,111 Network 1 compound IDs had repeated rows in the standardised compound table.
- 95 of those IDs had more than one distinct non-missing SMILES.

The baseline currently filters to status \`ok\`, non-missing identifiers and SMILES, then calls \`drop_duplicates("parent_inchikey")\`. That selects one row per key, but the 95 differing-SMILES cases need an explicit audit and resolution policy. Do not assume those 95 mappings are already correct.

### 3.3 One real example traced from data to structure

A real pair inspected during the practical lesson was:

| Field | Value |
|---|---|
| Compound InChIKey | \`AAAAKTROWFNLEP-UHFFFAOYSA-N\` |
| Protein accession | \`P49137\` |
| Protein family | \`Enzyme\` |
| Observed Network 1 label | \`INACTIVE\` |
| Standardised SMILES | \`CC1CNC(=O)c2[nH]c3ccc(C(=O)N(C)C)cc3c21\` |
| RDKit atoms | 20 |
| RDKit bonds | 22 |

This example was used to understand how a real chemical structure becomes numerical input.

## 4. How a drug becomes numbers: Morgan fingerprints

A machine-learning model needs numerical features. A chemical drawing or SMILES string must therefore be converted into a numerical representation.

Week 08's baseline uses an RDKit **Morgan binary fingerprint** with:
- Radius = 2.
- Fingerprint size = 2,048 bits.

A bit has only two values:
- \`0\`: this fingerprint position was not activated.
- \`1\`: at least one local chemical pattern was mapped to this position.

The Morgan algorithm examines atom-centred local environments. With radius 2, it considers neighbourhoods extending up to two bond steps from each atom. It generates identifiers for those environments and hashes them into the fixed set of 2,048 positions.

For the real example above, RDKit produced:
- Fingerprint length: 2,048.
- Bits set to 1: 42.
- Bits set to 0: 2,006.

**Important:** bit position 47 does not mean atom number 47. It is a hashed fingerprint position. Different patterns can collide at the same bit position, so 42 active bits does not necessarily mean exactly 42 unique chemical patterns.

Why this is useful: it gives the model a consistent, compact way to compare chemical structures. It is not a 3D binding model and does not prove how a molecule binds to a protein.

## 5. How a protein becomes numbers: family one-hot encoding

Network 1 has 16 distinct \`family_l1\` categories across the full dataset. Examples include:
- Enzyme
- Membrane receptor
- Ion channel
- Transporter
- Transcription factor
- Epigenetic regulator

One-hot encoding gives each category its own position. For example, a simplified three-category example could encode Enzyme as:

\`[1, 0, 0]\`

The actual Week 08 script uses scikit-learn's \`OneHotEncoder\`, fitted only on the sampled training partition. Missing family values are replaced with \`UNCLASSIFIED\`, and unknown categories are ignored during transformation.

A useful correction from our first teaching demonstration:
- The full dataset has 16 family categories.
- In the actual capped random baseline run, the training sample contained 15 categories.
- Therefore the actual baseline's combined sparse feature dimension was **2,063**, not 2,064: 2,048 molecular bits + 15 learned family columns.

The encoder is fitted on training data and then reused for calibration and test data. This is the correct general pattern: test data must not be used to fit the feature encoder.

A category absent from the training sample is not learned by the encoder; with \`handle_unknown="ignore"\`, that unseen category is represented by zeros in the family block. This is worth monitoring, especially in small capped samples.

## 6. How both feature sets become one drug–protein input

The real baseline creates:
1. A sparse Morgan fingerprint matrix for unique compounds.
2. A one-hot family matrix for each pair's protein.
3. A combined matrix using SciPy's \`hstack\`.

Conceptually:

\`pair_features = [2,048 chemical features | learned family features]\`

For the actual capped baseline run:

\`2,048 + 15 = 2,063 sparse features per pair\`

Why sparse matrices? Most Morgan positions are zero. A sparse matrix stores the non-zero values and their positions instead of storing every zero explicitly. This reduces memory use when processing many compounds and pairs.

The code also creates a lookup from each compound InChIKey to the row containing its fingerprint. Each Network 1 pair uses that lookup to retrieve the correct compound representation.

## 7. The model: Logistic Regression

Week 08 implemented and ran a classical reference model:

**RDKit Morgan fingerprint + protein-family one-hot features + scikit-learn Logistic Regression**

Important settings:
- Solver: \`liblinear\`.
- Class weighting: \`balanced\`.
- Maximum iterations: 200.
- Random seed: 42.
- Classification threshold: 0.5.
- Labels: INACTIVE = 0; ACTIVE = 1.

In simple terms:
1. The model receives the combined numerical features.
2. It learns weights from labelled training pairs.
3. It produces an estimated probability for INACTIVE and ACTIVE.
4. The ACTIVE probability is compared with the 0.5 threshold to produce the predicted class.

\`class_weight="balanced"\` gives additional weight to the less frequent class in the training sample. This helps avoid learning a decision rule that simply favours the majority class.

This is a **reference baseline**, not the final ChemBERTa/ESM-2 fusion model. It does not use protein sequences, protein identity embeddings, docking, or a learned 3D interaction representation.

## 8. Why we tested four different splits

A model can look good on a random test set but fail when it sees new compounds, new proteins, or later data. The four split strategies test different kinds of generalisation.

| Split | What is held out? | Question being tested |
|---|---|---|
| Random | Random compound–protein pairs | Can the model predict held-out pairs from a similar overall dataset? |
| Drug-cold | Scaffold groups | Can it generalise to chemical scaffold groups not used for training? |
| Target-cold | Protein accessions | Can it generalise to protein targets not used for training? |
| Temporal | Later-dated records | Can it generalise from pre-2020 records to records from 2020 onward? |

The temporal design uses:
- Training: dated records before 2020, after carving out calibration data.
- Calibration: records before 2020.
- Test: records from 2020 onward.
- Records without a year: left unassigned for this split.

The Network 1 manifest records:
- Temporal train: 724,919.
- Temporal calibration: 127,927.
- Temporal test: 392,879.
- Undated/unassigned: 659,861.

The year is the earliest document year associated with the pair in the builder. It is not necessarily the date of every measurement contributing to the pair.

## 9. Week 08 environment and execution

### 9.1 Test suite

The local command:

\`python -m pytest -q\`

returned:

**19 passed, 1 deselected in 18.64 seconds.**

This confirms that the tests included in that run passed. The deselected test was not executed; passing tests do not establish that the model has good predictive performance.

### 9.2 Running the model correctly

The direct command:

\`python src/model/evaluate_dti_baseline.py\`

failed because the script imports \`from src import config\` and Python did not resolve the project package in direct-script mode.

Running it as a module from the repository root fixed the import:

\`python -m src.model.evaluate_dti_baseline\`

### 9.3 Manifest path issue

The script expects:

\`reports/week2/network1_v1_manifest.json\`

During repository reorganisation, the local working copy had the data under \`reports/week02/\`, while the tracked canonical path was \`reports/week2/\`. The runner therefore stopped before training.

The tracked files were restored locally with:

\`git restore --worktree -- reports/week2/\`

The model then ran successfully. The local \`reports/week02/\` directory was left untouched and appeared as untracked in Git status. Do not stage it blindly; review it separately before any future commit. The repository's canonical Stage 2 manifest path is \`reports/week2/\`.

### 9.4 Capped experiment settings

Each split was run with:
- Maximum training rows: 5,000.
- Maximum calibration rows: 1,000.
- Maximum test rows: 2,000.

The code uses reproducible, label-stratified sampling within each partition. These are capped pilot samples, not full-partition evaluations.

Command pattern:

\`\`\`bash
python -m src.model.evaluate_dti_baseline \\
  --split random \\
  --max-train-rows 5000 \\
  --max-calib-rows 1000 \\
  --max-test-rows 2000
\`\`\`

The same command was executed for \`drugcold\`, \`targetcold\`, and \`temporal\`.

## 10. First baseline results: all four splits

Each result below uses a 2,000-pair test sample. The metrics describe those samples only.

| Split | Accuracy | Balanced accuracy | ROC-AUC | Average precision | ACTIVE F1 |
|---|---:|---:|---:|---:|---:|
| Random | 0.7445 | 0.7362 | 0.8103 | 0.7296 | 0.6820 |
| Drug-cold | 0.7070 | 0.6970 | 0.7785 | 0.6846 | 0.6410 |
| Target-cold | 0.7530 | 0.7230 | 0.8009 | 0.6484 | 0.6300 |
| Temporal | 0.5730 | 0.5790 | 0.6117 | 0.5887 | 0.6010 |

Additional metrics:

| Split | Brier score | ECE (15 bins) | Empirical prediction-set coverage | Mean set size |
|---|---:|---:|---:|---:|
| Random | 0.1883 | 0.1104 | 0.9005 | 1.421 |
| Drug-cold | 0.2115 | 0.1421 | 0.8955 | 1.444 |
| Target-cold | 0.1843 | 0.1163 | 0.9315 | 1.514 |
| Temporal | 0.3293 | 0.2741 | 0.8335 | 1.577 |

### How to read these metrics

- **Accuracy:** fraction of test pairs whose thresholded class was correct.
- **Balanced accuracy:** average recall across ACTIVE and INACTIVE classes; helpful when class counts differ.
- **Precision (ACTIVE):** among pairs predicted ACTIVE, the fraction labelled ACTIVE.
- **Recall (ACTIVE):** among actual ACTIVE pairs, the fraction predicted ACTIVE.
- **F1 (ACTIVE):** combines ACTIVE precision and recall.
- **ROC-AUC:** measures how well scores rank ACTIVE above INACTIVE pairs. 0.5 is chance-level ranking.
- **Average precision:** summarises the precision–recall curve. It depends on the positive-class prevalence, so compare it with prevalence and avoid interpreting it in isolation.
- **Brier score:** mean squared error of the predicted probabilities; lower is better.
- **ECE:** an approximate calibration diagnostic using 15 probability bins; lower is better, but it depends on binning and sample size.
- **Prediction-set coverage:** fraction of test examples whose observed label was included in the set generated using calibration data.
- **Mean set size:** average number of labels included (0, 1, or 2 in this binary problem).

### What the first comparison suggests

1. The model learns useful signal on the random split: ROC-AUC 0.8103.
2. Drug-cold and target-cold ROC-AUCs are also above 0.77 in these capped samples.
3. Temporal ROC-AUC drops to 0.6117; accuracy falls to 0.5730.
4. Temporal Brier score and ECE are much worse, indicating unreliable probabilities as well as weaker ranking.
5. These findings justify a deeper temporal and label-provenance investigation before a more complex model is introduced.

Do not claim that the baseline has been validated at full scale. The four test sets were capped at 2,000 rows.

## 11. Calibration and prediction uncertainty findings

The temporal test sample had:
- Actual ACTIVE prevalence: 46.9%.
- Mean predicted ACTIVE probability: 60.0%.
- Fraction assigned ACTIVE at the 0.5 threshold: 60.4%.
- Brier score: 0.3293.
- ECE: 0.2741.
- Empirical prediction-set coverage: 83.35%, despite a nominal alpha of 0.10 (90% target).

For the temporal sample's 90%-to-100% probability bin:
- 626 pairs.
- Mean predicted probability: 96.8%.
- Actual ACTIVE rate: 60.5%.

For the 0%-to-10% probability bin:
- 265 pairs.
- Mean predicted probability: 4.2%.
- Actual ACTIVE rate: 39.2%.

These are strong signs of poor calibration in the temporal sample.

The code produces split-conformal-style prediction sets using a calibration nonconformity quantile. **No formal coverage guarantee is claimed.** Standard split-conformal coverage depends on exchangeability assumptions; temporal distribution shift and dependence between related drug–protein pairs may violate them. The 83.35% result is an empirical observation, not a guarantee.

## 12. Temporal drift: what changed after 2020?

Full temporal test partition:
- Rows: 392,879.
- Years: 2020–2025.
- ACTIVE prevalence: 46.9%.

Training and calibration were both pre-2020:
- Training ACTIVE rate: 64.66%.
- Calibration ACTIVE rate: 64.82%.

Full temporal test ACTIVE rates by year:

| Year | Test pairs | ACTIVE rate |
|---|---:|---:|
| 2020 | 63,313 | 75.8% |
| 2021 | 112,772 | 40.8% |
| 2022 | 57,195 | 73.9% |
| 2023 | 117,231 | 20.5% |
| 2024 | 30,950 | 54.1% |
| 2025 | 11,418 | 62.9% |

This is not a smooth year-on-year decline. The label prevalence swings sharply. Therefore we should not describe it as a simple linear drift.

### 12.1 Protein-family composition also changes

Some examples from the full temporal test data:

- In 2023, membrane receptors contributed 57,936 pairs (49.4% of that year's records) and had a 6.7% ACTIVE rate.
- In 2023, enzymes contributed 33,651 pairs (28.7%) and had a 45.0% ACTIVE rate.
- In 2022, membrane receptors contributed 9,509 pairs (16.6%) and had a 78.3% ACTIVE rate.
- In 2021, enzymes represented 80,272 pairs (71.2%) and had a 34.9% ACTIVE rate.

Both the family mix and within-family label proportions vary. The current baseline's broad family feature cannot explain all these changes.

## 13. How Network 1 labels are constructed

This section is essential for understanding the Week 08 temporal investigation.

The builder is:

\`src/network/build_network1.py\`

The relevant label policy is:

| Evidence condition | Network 1 label |
|---|---|
| Exact affinity median \`median_p >= 6.5\` | ACTIVE |
| Exact affinity median \`median_p <= 5.0\` | INACTIVE |
| Exact median between 5.0 and 6.5 | GRAY; excluded from the labelled Network 1 set |
| No exact median, but at least one qualifying inactive-evidence flag | INACTIVE |
| No exact median and no qualifying inactive evidence | UNTESTED; excluded |

The potency value is calculated from an exact dose-response affinity measurement in nM using:

\`p = 9 - log10(value_in_nM)\`

The exact-measurement aggregation is performed per compound–protein pair.

### What the evidence flags mean in the builder

- \`has_cens\`: qualifying censored affinity evidence. The build checks dose-response affinity types (IC50, Ki, Kd, EC50), censored relations such as \`>\`, \`>=\`, or \`>>\`, nM units, and values at least 10,000 nM.
- \`has_comment\`: an activity comment matching the inactive-comment expression, such as “inactive”, “not active”, or “no activity”.
- \`has_qhts\`: qualifying qHTS evidence using the Potency or AC50 types, censored relations, nM units, and values at least 10,000 nM.
- \`high_disagreement\`: set when the IQR of exact-measurement potency values is at least 1.0.

The three inactive-evidence flags are used as part of label construction when the pair has **no exact median measurement**. If an exact median exists, the median thresholds determine ACTIVE, INACTIVE, or GRAY.

This means two pairs labelled INACTIVE can have different evidence histories:
1. One may have an exact weak-affinity measurement.
2. Another may have no exact median and may be labelled through a censored value, an inactive comment, qHTS evidence, or a combination.

The labels follow the project's chosen policy. The analysis does not establish that fallback labels are wrong. It establishes that their evidence provenance differs and should be measured.

## 14. What the provenance investigation found

### 14.1 Flag prevalence in the full temporal test set

| Year | ACTIVE rate | qHTS flag share | Comment flag share | Missing-median share |
|---|---:|---:|---:|---:|
| 2020 | 75.8% | 0.1% | 0.1% | 13.9% |
| 2021 | 40.8% | ~0.0% | 44.9% | 52.2% |
| 2022 | 73.9% | 0.1% | 3.5% | 15.8% |
| 2023 | 20.5% | 66.8% | 2.3% | 74.8% |
| 2024 | 54.1% | ~0.0% | 17.3% | 34.2% |
| 2025 | 62.9% | ~0.0% | 3.6% | 22.6% |

### 14.2 The 2021 pattern

In the full 2021 temporal test partition:
- 50,673 pairs had \`has_comment=True\`.
- 99.74% of these flagged pairs had no exact median.
- 50,395 were comment-only fallback pairs.
- 8,330 were censored-only fallback pairs.
- The complete fallback-only group had 58,881 INACTIVE labels.

### 14.3 The 2023 pattern

In the full 2023 temporal test partition:
- 78,297 pairs had \`has_qhts=True\`, about 66.8% of the year's records.
- 99.75% of these qHTS-flagged pairs had no exact median.
- 77,593 were qHTS-only fallback pairs.
- The complete fallback-only group had 87,653 INACTIVE labels.

These patterns explain why the years 2021 and 2023 deserve special investigation. They do not prove the labels are incorrect. They show that evidence-source composition is strongly associated with the observed year-wise label distribution.

### 14.4 Overall fallback combinations in the full temporal test partition

| Evidence combination | INACTIVE pairs |
|---|---:|
| Censored only | 38,866 |
| Comment only | 60,157 |
| Comment + censored | 322 |
| qHTS only | 77,664 |
| qHTS + censored | 38 |
| qHTS + comment | 477 |
| qHTS + comment + censored | 13 |

These combinations were counted using the flags together, so a pair with multiple flags is not counted as a single-source case.

## 15. How the model behaved on exact-measurement and fallback groups

We joined the 2,000 capped temporal test predictions back to Network 1 using the compound and protein identifiers.

The sample contained:
- 1,101 exact-measurement pairs.
- 899 fallback-only pairs.

### Exact-measurement subgroup

| Measure | Result |
|---|---:|
| Pairs | 1,101 |
| ACTIVE | 938 |
| INACTIVE | 163 |
| ACTIVE prevalence | 85.2% |
| Mean predicted ACTIVE probability | 63.87% |
| Accuracy | 66.21% |
| ROC-AUC | 0.6487 |
| Average precision | 0.9056 |
| Brier score | 0.2488 |

Average precision is high partly because this subgroup has a very high ACTIVE prevalence (85.2%). It should not be read as a stand-alone indication of strong predictive performance.

### Fallback-only subgroup

| Measure | Result |
|---|---:|
| Pairs | 899 |
| ACTIVE | 0 |
| INACTIVE | 899 |
| Mean predicted ACTIVE probability | 55.32% |
| Predicted ACTIVE rate at 0.5 | 53.73% |
| Accuracy | 46.27% |
| Brier score | 0.4279 |

ROC-AUC is undefined for this subgroup because it contains only one observed class. The model predicted about 483 of these 899 pairs as ACTIVE, even though their Network 1 labels are all INACTIVE.

Interpretation: the mixed-trained model struggles with fallback-only negatives in this temporal sample. This is a subgroup diagnostic, not a comparison between two independently trained models. It does not show that fallback evidence is false; it shows a mismatch between model scores and labels generated under this evidence policy.

## 16. What this work adds to TrustDTI

Week 08 contributes more than a first accuracy number.

1. **A reproducible classical reference point:** future feature and model changes can be compared with a known baseline.
2. **Evaluation beyond random pairs:** drug-cold, target-cold, and temporal splits reveal different generalisation challenges.
3. **A concrete calibration warning:** temporal probabilities are much less reliable, so uncertainty should not yet be used as a trusted routing signal.
4. **Evidence provenance awareness:** Network 1's INACTIVE class contains both exact-measurement and fallback-evidence cases.
5. **A hypothesis for follow-up research:** temporal changes in evidence-source and protein-family composition may contribute to poor future-period performance.

This is directly connected to the TrustDTI research question. Before an uncertainty-aware retrieval system can decide when to search more broadly or seek counter-evidence, we need to understand whether the model's uncertainty estimates are meaningful under distribution shift.

## 17. Limitations and issues still open

These must remain visible in reports and future comparisons.

1. **Capped samples:** All four test metrics came from 2,000 sampled pairs per split, not the full test partitions.
2. **No embedding fusion yet:** ChemBERTa and ESM-2 pilots exist, but the Week 08 baseline uses Morgan fingerprints and family labels only.
3. **Temporal distribution shift:** The temporal test results are substantially weaker and poorly calibrated.
4. **Label-source heterogeneity:** Fallback-only labels are assigned under a different evidence route from exact-measurement labels.
5. **95 conflicting structure mappings:** 95 DTI compound identifiers have multiple distinct SMILES in the standardised table. The current first-row de-duplication needs investigation.
6. **Family-only protein features:** A broad family is not a full protein sequence or target-specific representation.
7. **Sampled family vocabulary:** The capped training sample learned 15 family categories while the whole dataset has 16. The effect of unseen categories should be checked.
8. **Conformal assumptions:** Empirical coverage is reported, but no formal coverage guarantee is claimed.
9. **No evidence-retrieval validation:** The project has not yet shown that uncertainty-guided retrieval improves evidence precision or counter-evidence recall.

## 18. Local outputs created during Week 08

The baseline runner saved outputs locally.

Metrics:
- \`reports/model_baseline/baseline_metrics_random_morgan_family.json\`
- \`reports/model_baseline/baseline_metrics_drugcold_morgan_family.json\`
- \`reports/model_baseline/baseline_metrics_targetcold_morgan_family.json\`
- \`reports/model_baseline/baseline_metrics_temporal_morgan_family.json\`

Predictions:
- \`reports/model_baseline/baseline_predictions_random_morgan_family.csv\`
- \`reports/model_baseline/baseline_predictions_drugcold_morgan_family.csv\`
- \`reports/model_baseline/baseline_predictions_targetcold_morgan_family.csv\`
- \`reports/model_baseline/baseline_predictions_temporal_morgan_family.csv\`

Model artifacts (stored under the locally gitignored processed-data directory):
- \`data/processed/dti_baseline_random_morgan_family.joblib\`
- \`data/processed/dti_baseline_drugcold_morgan_family.joblib\`
- \`data/processed/dti_baseline_targetcold_morgan_family.joblib\`
- \`data/processed/dti_baseline_temporal_morgan_family.joblib\`

These were generated locally by the runs. This reference document does not imply that the CSV, JSON, or Joblib files have been committed to GitHub. Large processed datasets, trained models, and raw source data should remain out of Git unless a deliberate project decision says otherwise.

## 19. Week 09 plan: continue from the evidence

Week 09 should start with the most important unresolved question from Week 08: how much does label-evidence provenance affect DTI model performance?

### Priority 1 — Audit the 95 conflicting compound structures
- List each affected full InChIKey.
- Inspect every associated parent SMILES and standardisation status.
- Determine why one key has multiple structures.
- Define a transparent resolution rule.
- Do not silently keep an arbitrary structure for these cases.

### Priority 2 — Run a controlled exact-measurement sensitivity experiment
Compare two model setups on a common, clearly defined exact-measurement test subset:
- **Model A:** existing mixed-label training policy.
- **Model B:** training and calibration restricted to exact-measurement-supported pairs.

Keep the molecular features, protein features, random seed, split boundaries, and evaluation candidates controlled as far as possible. Report the change in sample counts and class balance. Do not overwrite Network 1 or change its original labels.

Fallback-only test records should be reported separately. Because they are all INACTIVE under the current label policy, ROC-AUC is not defined for that subset.

### Priority 3 — Improve and evaluate calibration
- Inspect reliability diagrams and calibration bins.
- Compare probability calibration on random, drug-cold, target-cold, and temporal settings.
- Consider a calibration method only after defining an appropriate calibration/evaluation design.
- Do not use a calibration method to hide distribution shift.
- Test whether uncertainty signals are stable enough for downstream routing.

### Priority 4 — Return to the broader TrustDTI pipeline
After the baseline and label-provenance work are defensible:
- Compare learned ChemBERTa and ESM-2 representations with the classical reference.
- Build the separate, provenance-tagged protein–disease evidence network.
- Define deterministic uncertainty/disease-context routing.
- Prototype literature retrieval that records source, date, query, policy, and evidence direction.
- Evaluate supporting-evidence precision and counter-evidence recall under matched retrieval budgets.

### Week 09 starting point

Begin with the existing local files and this reference. Do not rebuild Network 1, overwrite the baseline outputs, open sealed evaluation cases early, or add new modelling scope without recording the reason and the experiment design.

---

## 20. Key code and project references

Use these files to understand or reproduce the Week 08 workflow:

| Purpose | Repository file |
|---|---|
| Baseline training and evaluation | \`src/model/evaluate_dti_baseline.py\` |
| Network 1 creation and labels | \`src/network/build_network1.py\` |
| Week 2 scope and label-rule analysis | \`src/ingest/analyze_scope_week2.py\` |
| Network 1 manifest | \`reports/week2/network1_v1_manifest.json\` |
| Baseline stage notes | \`docs/stages/baseline_before_fusion.md\` |
| Week 8 sprint plan | \`docs/plans/week08_core_pipeline_sprint.md\` |
| Project status | \`docs/STATUS.md\` |
| Main project guide | \`docs/PROJECT_GUIDE.md\` |

Useful commands from the repository root:

\`\`\`bash
# Activate the local environment in Git Bash
source .venv/Scripts/activate

# Run the tests
python -m pytest -q

# Run one capped baseline experiment
python -m src.model.evaluate_dti_baseline \\
  --split random \\
  --max-train-rows 5000 \\
  --max-calib-rows 1000 \\
  --max-test-rows 2000

# Other split names: drugcold, targetcold, temporal
\`\`\`

**Week 08 final status:** the classical baseline was implemented, tested, and executed on four capped evaluation splits. Temporal weakness and label-evidence provenance were investigated. The cause is not fully resolved; the controlled exact-measurement sensitivity experiment and subsequent calibration work are Week 09 priorities.
