"""Run the four retrieval strategies against one fixed candidate set."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from src.network.router import STRATEGIES, allocate_intent_budget
from src.retrieval.europe_pmc import build_europe_pmc_query


def retrieve_candidate_set(
    candidates: Iterable[Mapping[str, Any]],
    client,
    budget_per_candidate: int = 10,
    strategies: tuple[str, ...] = STRATEGIES,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Retrieve policy-specific records for one fixed candidate set.

    The per-candidate document budget is a maximum cap. STOP intentionally uses
    zero retrieval slots. A publication found by multiple intents is deduplicated
    within candidate × strategy while all matched intents are retained.
    """
    if not isinstance(budget_per_candidate, int) or budget_per_candidate < 0:
        raise ValueError("budget_per_candidate must be a non-negative integer.")
    strategies = tuple(str(value).lower() for value in strategies)
    if not strategies or any(value not in STRATEGIES for value in strategies):
        raise ValueError(f"strategies must be a non-empty subset of {STRATEGIES}.")

    output: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    candidate_list = list(candidates)

    for candidate in candidate_list:
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        if not candidate_id:
            raise ValueError("Every candidate requires candidate_id.")
        for field in ("drug_name", "gene_symbol"):
            if not str(candidate.get(field) or "").strip():
                raise ValueError(f"Candidate {candidate_id} is missing {field}.")

        conformal_set = str(candidate.get("conformal_set") or "")
        anchor_tier = str(candidate.get("anchor_tier") or "NONE").upper()

        for strategy in strategies:
            allocations = allocate_intent_budget(
                strategy,
                conformal_set,
                anchor_tier,
                budget_per_candidate,
            )
            candidate_results: dict[str, dict[str, Any]] = {}

            for intent, slots in allocations.items():
                if slots <= 0:
                    continue

                query = None
                try:
                    # Missing disease names and malformed terms become an
                    # explicit query failure, not a crash of the entire run.
                    query = build_europe_pmc_query(intent, candidate)
                    articles = client.search(query, max_results=slots)
                    for article in articles:
                        record_id = str(article.get("record_id") or "").strip()
                        if not record_id:
                            raise ValueError("Retrieved article is missing record_id.")
                        if record_id not in candidate_results:
                            candidate_results[record_id] = {
                                **article,
                                "candidate_id": candidate_id,
                                "drug_name": str(candidate.get("drug_name") or ""),
                                "gene_symbol": str(candidate.get("gene_symbol") or ""),
                                "disease_name": str(candidate.get("disease_name") or ""),
                                "strategy": strategy,
                                "retrieval_intents": [intent],
                                "budget_cap": budget_per_candidate,
                                "conformal_set": conformal_set,
                                "anchor_tier": anchor_tier,
                                "p_active": candidate.get("p_active"),
                                "direction_label": None,
                                "annotation_status": "UNANNOTATED",
                            }
                        elif intent not in candidate_results[record_id]["retrieval_intents"]:
                            candidate_results[record_id]["retrieval_intents"].append(intent)
                except Exception as exc:
                    failures.append(
                        {
                            "candidate_id": candidate_id,
                            "strategy": strategy,
                            "intent": intent,
                            "query": query,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
                    continue

            output.extend(candidate_results.values())

    return output, failures
