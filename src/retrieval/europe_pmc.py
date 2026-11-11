"""Small, provenance-preserving client for the Europe PMC REST search API.

Search intent is stored separately from biological evidence direction. Every
retrieved publication starts UNANNOTATED; query wording never labels it SUPPORT
or CONTRADICT.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import quote

import requests


EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _quoted_term(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("\\", " ").replace('"', " ").replace("(", " ").replace(")", " ")
    text = " ".join(text.split())
    if not text:
        raise ValueError("A required literature search term is empty.")
    return f'"{text}"'


def build_europe_pmc_query(intent: str, candidate: Mapping[str, Any]) -> str:
    """Build a title/abstract query; query intent is not an evidence label."""
    intent = str(intent).strip().upper()
    drug = _quoted_term(candidate.get("drug_name"))
    gene = _quoted_term(candidate.get("gene_symbol"))

    if intent == "MECHANISTIC":
        expression = (
            f"{drug} AND {gene} AND "
            '(bind* OR inhibit* OR agonist OR antagonist OR interact* OR target*)'
        )
    elif intent == "COUNTER":
        expression = (
            f"{drug} AND {gene} AND "
            '(resistan* OR ineffective OR "no effect" OR '
            '"failed to inhibit" OR "does not bind" OR "lack of activity")'
        )
    elif intent == "DISEASE_CONTEXT":
        disease = _quoted_term(candidate.get("disease_name"))
        expression = f"{gene} AND {disease}"
    elif intent == "GENERAL":
        expression = f"{drug} AND {gene}"
    else:
        raise ValueError(
            "intent must be MECHANISTIC, COUNTER, DISEASE_CONTEXT or GENERAL."
        )

    return f"TITLE_ABS:({expression})"


def _publication_url(record: Mapping[str, Any]) -> str:
    pmid = record.get("pmid")
    pmcid = record.get("pmcid")
    doi = record.get("doi")

    if pmid:
        return f"https://europepmc.org/article/MED/{pmid}"
    if pmcid:
        return f"https://europepmc.org/articles/{pmcid}"
    if doi:
        return f"https://doi.org/{doi}"
    return "https://europepmc.org/"


def normalise_article(
    record: Mapping[str, Any],
    query: str,
    retrieved_at_utc: str | None = None,
) -> dict[str, Any]:
    """Extract a stable, compact article record from a Europe PMC core result."""
    source = str(record.get("source") or "UNKNOWN")
    source_id = str(record.get("id") or record.get("pmid") or record.get("doi") or "")
    pmid = record.get("pmid")
    if pmid is None and source.upper() == "MED":
        pmid = record.get("id")

    journal_info = record.get("journalInfo") or {}
    journal = record.get("journalTitle")
    if not journal:
        journal = (journal_info.get("journal") or {}).get("title")

    record_id = f"{source}:{source_id}" if source_id else str(record.get("doi") or "")
    if not record_id:
        raise ValueError("Europe PMC record has no stable source identifier.")

    return {
        "record_id": record_id,
        "source": source,
        "source_id": source_id,
        "pmid": str(pmid) if pmid else None,
        "pmcid": record.get("pmcid"),
        "doi": record.get("doi"),
        "title": record.get("title"),
        "author_string": record.get("authorString"),
        "journal": journal,
        "publication_year": record.get("pubYear"),
        "first_publication_date": record.get("firstPublicationDate"),
        "abstract": record.get("abstractText"),
        "is_open_access": record.get("isOpenAccess"),
        "source_url": _publication_url({**record, "pmid": pmid}),
        "query": query,
        "retrieved_at_utc": retrieved_at_utc or datetime.now(timezone.utc).isoformat(),
        "annotation_status": "UNANNOTATED",
        "direction_label": None,
    }


class EuropePMCClient:
    """Europe PMC REST client. A shared requests.Session is reused across searches."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: tuple[float, float] = (15.0, 45.0),
        max_retries: int = 3,
    ):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries
        self.session.headers.update(
            {"User-Agent": "TrustDTI/0.1 (research prototype; Europe PMC REST client)"}
        )

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        if not query or not query.strip():
            raise ValueError("query must be non-empty.")
        if not isinstance(max_results, int) or max_results < 0:
            raise ValueError("max_results must be a non-negative integer.")
        if max_results == 0:
            return []
        if max_results > 1000:
            raise ValueError("Europe PMC pageSize is capped at 1000 per request.")

        params = {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": max_results,
        }

        response = None
        for attempt in range(self.max_retries + 1):
            response = self.session.get(
                EUROPE_PMC_SEARCH_URL,
                params=params,
                timeout=self.timeout,
            )
            if response.status_code not in RETRYABLE_STATUS:
                response.raise_for_status()
                break
            if attempt >= self.max_retries:
                response.raise_for_status()

            retry_after = response.headers.get("Retry-After")
            try:
                delay = min(10.0, max(0.5, float(retry_after))) if retry_after else 0.5 * (2 ** attempt)
            except ValueError:
                delay = 0.5 * (2 ** attempt)
            import time
            time.sleep(delay)

        payload = response.json()
        results = (payload.get("resultList") or {}).get("result") or []
        timestamp = datetime.now(timezone.utc).isoformat()
        return [
            normalise_article(item, query, timestamp)
            for item in results[:max_results]
        ]

    def close(self) -> None:
        self.session.close()
