import pandas as pd
import pytest

from scripts.week10.build_candidate_set import select_label_blind_predictions


def test_candidate_prediction_input_renames_accession_and_drops_observed_label():
    predictions = pd.DataFrame([
        {
            "pik": "CMPD1",
            "accession": "P12345",
            "p_active": 0.72,
            "conformal_set": "ACTIVE|INACTIVE",
            "label": "INACTIVE",
        }
    ])
    selected = select_label_blind_predictions(predictions)
    assert selected.loc[0, "uniprot_accession"] == "P12345"
    assert "accession" not in selected.columns
    assert "label" not in selected.columns
    assert set(selected.columns) == {
        "pik", "uniprot_accession", "p_active", "conformal_set"
    }


def test_candidate_prediction_input_rejects_missing_fields():
    with pytest.raises(ValueError, match="Baseline predictions missing"):
        select_label_blind_predictions(pd.DataFrame([{"pik": "CMPD1"}]))
