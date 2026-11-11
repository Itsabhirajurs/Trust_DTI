import pandas as pd
import pytest

from scripts.week10.validate_network2 import validate_frames


def example_frames():
    bridge = pd.DataFrame([
        {"uniprot_accession": "P1", "ensembl_gene_id": "ENSG1"},
        {"uniprot_accession": "P2", "ensembl_gene_id": "ENSG2"},
    ])
    source = pd.DataFrame([
        {
            "targetId": "ENSG1", "diseaseId": "EFO1",
            "aggregationType": "datasourceId", "aggregationValue": "europepmc",
            "associationScore": 0.4, "evidenceCount": 2,
            "uniprot_accession": "P1", "edge_provenance": "curated",
            "opentargets_release": "26.09",
        }
    ])
    overall = pd.DataFrame([
        {
            "targetId": "ENSG1", "diseaseId": "EFO1",
            "aggregationType": "overall", "aggregationValue": None,
            "associationScore": 0.6, "evidenceCount": 3,
            "uniprot_accession": "P1", "edge_provenance": "curated",
            "opentargets_release": "26.09", "disease_name": "Disease 1",
        }
    ])
    return source, overall, bridge


def test_network2_validation_passes_for_separate_consistent_tables():
    source, overall, bridge = example_frames()
    result = validate_frames(source, overall, bridge)
    assert result["all_critical_checks_passed"]
    assert result["source_specific"]["datasource_counts"] == {"europepmc": 1}
    assert result["overall_direct"]["unique_target_disease_pairs"] == 1


def test_network2_validation_detects_target_identifier_mismatch():
    source, overall, bridge = example_frames()
    overall.loc[0, "targetId"] = "ENSG_WRONG"
    result = validate_frames(source, overall, bridge)
    assert not result["checks"]["overall_mapping_consistent"]
    assert not result["all_critical_checks_passed"]


def test_network2_validation_detects_duplicate_edges():
    source, overall, bridge = example_frames()
    source = pd.concat([source, source], ignore_index=True)
    result = validate_frames(source, overall, bridge)
    assert not result["checks"]["source_keys_unique"]


def test_network2_validation_detects_invalid_scores():
    source, overall, bridge = example_frames()
    source.loc[0, "associationScore"] = 1.2
    result = validate_frames(source, overall, bridge)
    assert not result["checks"]["source_score_within_0_1"]


def test_network2_validation_rejects_nonunique_bridge():
    source, overall, bridge = example_frames()
    bridge.loc[1, "uniprot_accession"] = "P1"
    with pytest.raises(ValueError, match="one row per UniProt"):
        validate_frames(source, overall, bridge)
