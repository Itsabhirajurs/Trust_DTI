# Classical DTI baseline — before the fusion model

## Why we need a baseline

A pretrained encoder returning a vector does not prove it predicts drug–target interactions. We need a model trained on labelled interactions and metrics on held-out rows before saying the representations help. A classical baseline gives us a reference point and tests the evaluation path.

## The first baseline configuration

- Compound feature: RDKit Morgan fingerprint, radius 2, 2,048 bits.
- Protein feature: one-hot encoding of Network 1's `family_l1`.
- Estimator: scikit-learn logistic regression with balanced class weights.
- Labels: `INACTIVE = 0`, `ACTIVE = 1`; Network 1 contains labelled ACTIVE/INACTIVE pairs only.
- Partitions: committed `split_random`, `split_drugcold`, `split_targetcold`, or `split_temporal` assignments. Train/calibration/test are never remixed across split definitions.
- Resource caps default to 50,000 training, 10,000 calibration and 20,000 test rows. Caps are stratified by label and disclosed in the metrics JSON.

## Outputs and metrics

The runner writes JSON metrics and a CSV of test predictions to `reports/model_baseline/`. The fitted estimator is saved under `data/processed/`, which is gitignored. Metrics include accuracy, balanced accuracy, precision/recall/F1, ROC-AUC, average precision, Brier score, a 15-bin ECE diagnostic, confusion matrix, and empirical prediction-set coverage/size.

## Calibration and limitations

The prediction-set calculation uses the calibration partition and nonconformity (1 - p(y)). It reports empirical test coverage, but does not claim guaranteed coverage: exchangeability must be justified, and dependence or distribution shift may violate assumptions, particularly in drug-cold, target-cold and temporal tests.

The family-only target feature does not represent target-specific sequence information. This baseline is not the final ChemBERTa/ESM-2 fusion model. ECE is a fixed-bin diagnostic, not sufficient by itself to establish calibrated probabilities.

## How to run

From the repository root after local data files are available:

```bash
python -m src.model.evaluate_dti_baseline --split random
python -m src.model.evaluate_dti_baseline --split drugcold
python -m src.model.evaluate_dti_baseline --split targetcold
python -m src.model.evaluate_dti_baseline --split temporal
```

Run the random split first with defaults. Record runtime and resource use before increasing caps. Use `--max-train-rows 0 --max-calib-rows 0 --max-test-rows 0` only when deliberately running every row in each partition.

## Be able to explain

- Why a fingerprint baseline is useful even if the final model uses neural embeddings.
- Why each split answers a different generalisation question.
- Why calibration rows must not be used to fit the classifier.
- Why empirical conformal coverage under distribution shift is not automatically a guarantee.
