from src.retrieval.europe_pmc import build_europe_pmc_query, normalise_article


def candidate():
    return {"drug_name": "imatinib", "gene_symbol": "ABL1", "disease_name": "leukaemia"}


def test_queries_encode_search_intent_but_not_evidence_truth():
    assert "inhibit" in build_europe_pmc_query("MECHANISTIC", candidate())
    counter = build_europe_pmc_query("COUNTER", candidate())
    assert "resistan" in counter
    assert "SUPPORT" not in counter.upper()
    assert "CONTRADICT" not in counter.upper()


def test_disease_context_query_uses_gene_and_disease():
    query = build_europe_pmc_query("DISEASE_CONTEXT", candidate())
    assert "ABL1" in query and "leukaemia" in query


def test_article_normalisation_preserves_provenance_and_starts_unannotated():
    article = normalise_article(
        {
            "source": "MED",
            "id": "12345",
            "title": "Example",
            "abstractText": "Example abstract",
            "pubYear": "2024",
            "doi": "10.1/example",
        },
        query="TITLE_ABS:(example)",
    )
    assert article["record_id"] == "PMID:12345"
    assert article["pmid"] == "12345"
    assert article["annotation_status"] == "UNANNOTATED"
    assert article["direction_label"] is None
    assert article["source_url"].endswith("/12345")
