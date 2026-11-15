import pandas as pd
import pytest

from scripts.week10.build_candidate_set import (
    deduplicate_candidate_pairs,
    select_label_blind_predictions,
    select_primary_named_disease_association,
)


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



def test_candidate_deduplication_uses_renamed_uniprot_accession_key():
    candidates = pd.DataFrame([
        {"pik": "CMPD1", "uniprot_accession": "P12345", "disease_id": "EFO1"},
        {"pik": "CMPD1", "uniprot_accession": "P12345", "disease_id": "EFO2"},
        {"pik": "CMPD1", "uniprot_accession": "P54321", "disease_id": "EFO3"},
    ])
    result = deduplicate_candidate_pairs(candidates)
    assert len(result) == 2
    assert set(result["uniprot_accession"]) == {"P12345", "P54321"}


def test_candidate_deduplication_rejects_old_or_missing_key():
    with pytest.raises(ValueError, match="deduplication keys"):
        deduplicate_candidate_pairs(pd.DataFrame([{"pik": "CMPD1", "accession": "P12345"}]))



def test_primary_named_disease_anchor_skips_rows_without_joined_disease_name():
    network = pd.DataFrame([
        {
            "uniprot_accession": "P1", "targetId": "ENSG1",
            "diseaseId": "EFO_MISSING", "disease_name": None,
            "associationScore": 0.99, "evidenceCount": 100,
            "currentNovelty": 0.1,
        },
        {
            "uniprot_accession": "P1", "targetId": "ENSG1",
            "diseaseId": "EFO_NAMED", "disease_name": "Example disease",
            "associationScore": 0.55, "evidenceCount": 10,
            "currentNovelty": 0.2,
        },
    ])
    result = select_primary_named_disease_association(network)
    assert len(result) == 1
    assert result.iloc[0]["diseaseId"] == "EFO_NAMED"


def test_primary_named_disease_anchor_returns_empty_when_no_named_associations():
    network = pd.DataFrame([
        {
            "uniprot_accession": "P1", "targetId": "ENSG1",
            "diseaseId": "EFO_MISSING", "disease_name": None,
            "associationScore": 0.99, "evidenceCount": 100,
            "currentNovelty": 0.1,
        }
    ])
    result = select_primary_named_disease_association(network)
    assert result.empty
