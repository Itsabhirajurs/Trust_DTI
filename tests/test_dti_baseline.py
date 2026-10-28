import numpy as np
import pandas as pd
import pytest

from src.model.evaluate_dti_baseline import (
    build_morgan_matrix,
    expected_calibration_error,
    split_conformal_prediction_sets,
    stratified_cap,
    validate_split_integrity,
)


def test_stratified_cap_is_reproducible_and_keeps_both_labels():
    frame = pd.DataFrame({
        "pik": [f"C{i}" for i in range(200)],
        "label": ["ACTIVE"] * 80 + ["INACTIVE"] * 120,
    })
    first = stratified_cap(frame, max_rows=80, seed=17)
    second = stratified_cap(frame, max_rows=80, seed=17)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 80
    assert set(first["label"]) == {"ACTIVE", "INACTIVE"}
    assert abs((first["label"] == "ACTIVE").mean() - 0.4) < 0.03


def test_non_positive_sample_cap_means_all_rows():
    frame = pd.DataFrame({
        "pik": ["a", "b", "c"],
        "label": ["ACTIVE", "ACTIVE", "INACTIVE"],
    })
    assert len(stratified_cap(frame, max_rows=0, seed=1)) == 3


def test_stratified_cap_rejects_small_class_when_sampling():
    frame = pd.DataFrame({"label": ["ACTIVE", "ACTIVE", "INACTIVE"]})
    with pytest.raises(ValueError, match="at least two"):
        stratified_cap(frame, max_rows=2, seed=1)


def test_split_conformal_sets_shape_and_quantile():
    p_cal = np.array([
        [0.90, 0.10], [0.10, 0.90], [0.80, 0.20], [0.20, 0.80],
        [0.70, 0.30], [0.30, 0.70], [0.85, 0.15], [0.15, 0.85],
        [0.60, 0.40], [0.40, 0.60],
    ])
    y_cal = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])
    p_eval = np.array([[0.60, 0.40], [0.20, 0.80], [0.50, 0.50]])
    prediction_sets, quantile = split_conformal_prediction_sets(
        p_cal, y_cal, p_eval, alpha=0.2
    )
    assert prediction_sets.shape == (3, 2)
    assert quantile == pytest.approx(0.4)
    assert prediction_sets[0].tolist() == [True, False]
    assert prediction_sets[1].tolist() == [False, True]


def test_split_conformal_rejects_invalid_alpha():
    with pytest.raises(ValueError, match="alpha"):
        split_conformal_prediction_sets(
            np.array([[0.5, 0.5]]),
            np.array([1]),
            np.array([[0.5, 0.5]]),
            alpha=1.0,
        )


def test_morgan_fingerprints_are_sparse_binary_and_keyed():
    matrix, key_to_row = build_morgan_matrix(
        ["drug-a", "drug-b"],
        {"drug-a": "CCO", "drug-b": "c1ccccc1"},
        radius=2,
        n_bits=128,
    )
    assert matrix.shape == (2, 128)
    assert set(key_to_row) == {"drug-a", "drug-b"}
    assert matrix.nnz > 0
    assert set(matrix.data.tolist()) == {1.0}


def test_target_cold_split_integrity_detects_target_overlap_and_duplicate_pair():
    frame = pd.DataFrame({
        "pik": ["a", "a", "c", "d", "e", "f"],
        "accession": ["P1", "P1", "P2", "P3", "P4", "P5"],
        "label": ["ACTIVE", "INACTIVE"] * 3,
        "split_targetcold": ["train", "test", "calib", "train", "calib", "test"],
    })
    checks = validate_split_integrity(frame, "targetcold")
    assert not checks["train_test_target_disjoint"]
    assert not checks["unique_compound_protein_pairs"]


def test_drugcold_split_integrity_checks_scaffold_separation():
    frame = pd.DataFrame({
        "pik": ["a", "b", "c", "d", "e", "f"],
        "accession": ["P1", "P2", "P3", "P4", "P5", "P6"],
        "label": ["ACTIVE", "INACTIVE"] * 3,
        "scaffold_group": ["S1", "S2", "S3", "S4", "S4", "S6"],
        "split_drugcold": ["train", "train", "calib", "calib", "test", "test"],
    })
    checks = validate_split_integrity(frame, "drugcold")
    assert not checks["calib_test_scaffold_disjoint"]


def test_split_integrity_requires_each_partition():
    frame = pd.DataFrame({
        "pik": ["a", "b"],
        "accession": ["P1", "P2"],
        "label": ["ACTIVE", "INACTIVE"],
        "split_random": ["train", "test"],
    })
    checks = validate_split_integrity(frame, "random")
    assert not checks["calib_nonempty"]


def test_ece_is_zero_for_perfectly_calibrated_binary_example():
    labels = np.array([0, 0, 1, 1])
    probabilities = np.array([0.1, 0.1, 0.9, 0.9])
    assert expected_calibration_error(labels, probabilities, n_bins=10) == pytest.approx(0.1)
