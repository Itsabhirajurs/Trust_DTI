import pandas as pd
import pytest

from scripts.week10.evaluate_retrieval import evaluate, expand_blinded_annotations


def test_evaluation_keeps_unknown_separate_and_reports_pooled_counter_recall():
    frame = pd.DataFrame([
        {"candidate_id": "c1", "strategy": "fixed", "record_id": "a", "direction_label": "SUPPORT"},
        {"candidate_id": "c1", "strategy": "fixed", "record_id": "b", "direction_label": "CONTRADICT"},
        {"candidate_id": "c1", "strategy": "combined", "record_id": "b", "direction_label": "CONTRADICT"},
        {"candidate_id": "c1", "strategy": "combined", "record_id": "c", "direction_label": "UNKNOWN"},
    ])
    result = evaluate(frame, budget=10)
    fixed = result["strategies"]["fixed"]
    combined = result["strategies"]["combined"]
    assert fixed["support_count"] == 1
    assert fixed["contradict_count"] == 1
    assert combined["unknown_count"] == 1
    assert combined["pooled_candidate_set_counter_evidence_recall"] == 1.0


def test_evaluator_rejects_budget_violations():
    frame = pd.DataFrame([
        {"candidate_id": "c1", "strategy": "fixed", "record_id": str(i), "direction_label": "UNKNOWN"}
        for i in range(3)
    ])
    with pytest.raises(ValueError, match="budget"):
        evaluate(frame, budget=2)


def test_evaluator_rejects_duplicate_records_within_a_policy():
    frame = pd.DataFrame([
        {"candidate_id": "c1", "strategy": "fixed", "record_id": "a", "direction_label": "SUPPORT"},
        {"candidate_id": "c1", "strategy": "fixed", "record_id": "a", "direction_label": "SUPPORT"},
    ])
    with pytest.raises(ValueError, match="Duplicate"):
        evaluate(frame, budget=10)

def test_blinded_annotations_are_expanded_back_to_all_policy_exposures():
    annotations = pd.DataFrame([
        {
            "candidate_id": "c1",
            "record_id": "MED:1",
            "direction_label": "UNKNOWN",
            "annotation_rationale": "Abstract does not answer the question.",
        }
    ])
    manifest = pd.DataFrame([
        {"candidate_id": "c1", "record_id": "MED:1", "strategy_code": "POLICY_1"},
        {"candidate_id": "c1", "record_id": "MED:1", "strategy_code": "POLICY_2"},
    ])
    key = pd.DataFrame([
        {"strategy_code": "POLICY_1", "strategy": "fixed"},
        {"strategy_code": "POLICY_2", "strategy": "combined"},
    ])
    expanded = expand_blinded_annotations(annotations, manifest, key)
    assert len(expanded) == 2
    assert set(expanded["strategy"]) == {"fixed", "combined"}
    assert set(expanded["direction_label"]) == {"UNKNOWN"}


def test_blinded_annotation_requires_one_label_per_candidate_publication():
    annotations = pd.DataFrame([
        {"candidate_id": "c1", "record_id": "MED:1", "direction_label": "SUPPORT"},
        {"candidate_id": "c1", "record_id": "MED:1", "direction_label": "CONTRADICT"},
    ])
    manifest = pd.DataFrame([
        {"candidate_id": "c1", "record_id": "MED:1", "strategy_code": "POLICY_1"},
    ])
    key = pd.DataFrame([
        {"strategy_code": "POLICY_1", "strategy": "fixed"},
    ])
    with pytest.raises(ValueError, match="one row per candidate-publication"):
        expand_blinded_annotations(annotations, manifest, key)
