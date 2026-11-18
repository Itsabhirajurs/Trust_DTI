import pytest

from scripts.week11.run_week11_pipeline import (
    annotation_completion_summary,
    validate_candidate_audit,
    validate_retrieval_metadata,
    validate_retrieval_records,
)


def test_candidate_audit_requires_label_blind_selection_and_a_nonempty_fixed_pool():
    audit = {
        "candidate_count": 9,
        "label_blind_selection": True,
        "true_label_column_used": False,
    }
    assert validate_candidate_audit(audit, 9) == 9

    with pytest.raises(ValueError, match="label-blind"):
        validate_candidate_audit({**audit, "label_blind_selection": False}, 9)
    with pytest.raises(ValueError, match="outside"):
        validate_candidate_audit({**audit, "candidate_count": 10}, 9)


def test_retrieval_metadata_requires_all_four_arms_same_pool_and_budget():
    metadata = {
        "candidate_count": 9,
        "budget_per_candidate": 5,
        "retrieved_unique_candidate_strategy_records": 22,
        "strategies": ["fixed", "uncertainty_only", "disease_only", "combined"],
    }
    assert validate_retrieval_metadata(metadata, 9, 5) == 22

    with pytest.raises(ValueError, match="strategies"):
        validate_retrieval_metadata({**metadata, "strategies": ["fixed"]}, 9, 5)
    with pytest.raises(ValueError, match="budget"):
        validate_retrieval_metadata(metadata, 9, 10)
    with pytest.raises(ValueError, match="no usable records"):
        validate_retrieval_metadata({**metadata, "retrieved_unique_candidate_strategy_records": 0}, 9, 5)


def test_annotation_summary_requires_valid_direction_category_and_rationale():
    rows = [
        {
            "direction_label": "SUPPORT",
            "evidence_category": "MECHANISTIC",
            "annotation_rationale": "The abstract reports direct target inhibition.",
        },
        {
            "direction_label": "UNKNOWN",
            "evidence_category": "OTHER",
            "annotation_rationale": "The abstract lacks relevant mechanistic detail.",
        },
    ]
    assert annotation_completion_summary(rows)["complete"] is True

    incomplete = [rows[0], {**rows[1], "direction_label": ""}]
    summary = annotation_completion_summary(incomplete)
    assert summary["complete"] is False
    assert summary["rows_pending_or_invalid_label"] == [3]


def test_annotation_summary_rejects_missing_category_or_rationale():
    result = annotation_completion_summary([
        {
            "direction_label": "CONTRADICT",
            "evidence_category": "",
            "annotation_rationale": "",
        }
    ])
    assert result["complete"] is False
    assert result["rows_missing_category_or_rationale"] == [2]


def test_retrieval_records_validate_fixed_candidate_pool_budget_and_blind_state(tmp_path):
    path = tmp_path / "records.jsonl"
    rows = [
        {
            "candidate_id": "c1",
            "strategy": "fixed",
            "record_id": "PMID:1",
            "annotation_status": "UNANNOTATED",
            "direction_label": None,
        },
        {
            "candidate_id": "c1",
            "strategy": "combined",
            "record_id": "PMID:2",
            "annotation_status": "UNANNOTATED",
            "direction_label": None,
        },
    ]
    import json
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    summary = validate_retrieval_records(path, {"c1", "c2"}, budget=1)
    assert summary["record_count"] == 2
    assert summary["matched_budget_respected"] is True
    assert summary["strategy_record_counts"]["fixed"] == 1
    assert summary["strategy_record_counts"]["combined"] == 1


def test_retrieval_records_reject_out_of_pool_candidates_and_over_budget(tmp_path):
    import json

    path = tmp_path / "records.jsonl"
    rows = [
        {
            "candidate_id": "not-in-pool",
            "strategy": "fixed",
            "record_id": "PMID:1",
            "annotation_status": "UNANNOTATED",
            "direction_label": None,
        }
    ]
    path.write_text(json.dumps(rows[0]), encoding="utf-8")
    with pytest.raises(ValueError, match="outside the fixed pool"):
        validate_retrieval_records(path, {"c1"}, budget=5)

    rows = [
        {
            "candidate_id": "c1",
            "strategy": "fixed",
            "record_id": f"PMID:{index}",
            "annotation_status": "UNANNOTATED",
            "direction_label": None,
        }
        for index in (1, 2)
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="exceeded matched per-candidate budget"):
        validate_retrieval_records(path, {"c1"}, budget=1)


def test_retrieval_records_reject_automatic_evidence_labels(tmp_path):
    import json

    path = tmp_path / "records.jsonl"
    row = {
        "candidate_id": "c1",
        "strategy": "fixed",
        "record_id": "PMID:1",
        "annotation_status": "UNANNOTATED",
        "direction_label": "CONTRADICT",
    }
    path.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="must not auto-assign"):
        validate_retrieval_records(path, {"c1"}, budget=5)
