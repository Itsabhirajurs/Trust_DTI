from src.retrieval.pipeline import retrieve_candidate_set


class FakeEuropePMC:
    def __init__(self):
        self.calls = []

    def search(self, query, max_results=10):
        self.calls.append((query, max_results))
        return [{
            "record_id": f"MED:{len(self.calls)}",
            "title": "Synthetic article",
            "abstract": "Synthetic abstract",
            "source_url": "https://europepmc.org/",
            "query": query,
            "annotation_status": "UNANNOTATED",
            "direction_label": None,
        }]


def test_four_strategies_share_fixed_candidate_pool_and_document_cap():
    client = FakeEuropePMC()
    candidates = [{
        "candidate_id": "c1",
        "drug_name": "imatinib",
        "gene_symbol": "ABL1",
        "disease_name": "leukaemia",
        "conformal_set": "ACTIVE|INACTIVE",
        "anchor_tier": "STRONG",
        "p_active": 0.52,
    }]
    records, failures = retrieve_candidate_set(candidates, client, budget_per_candidate=10)
    assert not failures
    assert {row["strategy"] for row in records} == {
        "fixed", "uncertainty_only", "disease_only", "combined"
    }
    for strategy in ("fixed", "uncertainty_only", "disease_only", "combined"):
        subset = [row for row in records if row["strategy"] == strategy]
        assert len(subset) <= 10
        assert all(row["annotation_status"] == "UNANNOTATED" for row in subset)
        assert all(row["direction_label"] is None for row in subset)


def test_invalid_candidate_is_rejected():
    client = FakeEuropePMC()
    try:
        retrieve_candidate_set([{"candidate_id": "c1"}], client)
    except ValueError as exc:
        assert "drug_name" in str(exc)
    else:
        raise AssertionError("Expected missing drug_name to fail.")

def test_missing_disease_name_is_recorded_as_query_failure_not_fatal():
    client = FakeEuropePMC()
    candidates = [{
        "candidate_id": "c2",
        "drug_name": "imatinib",
        "gene_symbol": "ABL1",
        "disease_name": "",
        "conformal_set": "ACTIVE",
        "anchor_tier": "STRONG",
        "p_active": 0.9,
    }]
    records, failures = retrieve_candidate_set(
        candidates,
        client,
        budget_per_candidate=10,
        strategies=("fixed", "disease_only", "combined"),
    )
    assert failures
    assert all(item["error_type"] == "ValueError" for item in failures)
    # Mechanistic searches still run even when a disease-context term is missing.
    assert any(item["title"] == "Synthetic article" for item in records)
