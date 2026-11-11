from __future__ import annotations

"""Run fixed, uncertainty-only, disease-only and combined Europe PMC retrieval."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.retrieval.europe_pmc import EuropePMCClient
from src.retrieval.pipeline import retrieve_candidate_set


CANDIDATES = PROJECT_ROOT / "data/processed/week10_candidates.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/week10"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget-per-candidate", type=int, default=10)
    parser.add_argument("--limit-candidates", type=int, default=0)
    args = parser.parse_args()

    if args.budget_per_candidate < 0 or args.limit_candidates < 0:
        parser.error("Budget and candidate limit must be non-negative.")
    if not CANDIDATES.exists():
        raise SystemExit(f"Candidate file not found: {CANDIDATES}")

    frame = pd.read_csv(CANDIDATES).fillna("")
    if args.limit_candidates:
        frame = frame.head(args.limit_candidates)
    candidates = frame.to_dict(orient="records")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = EuropePMCClient()
    try:
        records, failures = retrieve_candidate_set(
            candidates,
            client,
            budget_per_candidate=args.budget_per_candidate,
        )
    finally:
        client.close()

    records_path = OUTPUT_DIR / "retrieval_records.jsonl"
    failures_path = OUTPUT_DIR / "retrieval_failures.json"
    metadata_path = OUTPUT_DIR / "retrieval_run_metadata.json"

    with records_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    failures_path.write_text(json.dumps(failures, indent=2), encoding="utf-8")

    summary = {
        "candidate_count": len(candidates),
        "strategies": ["fixed", "uncertainty_only", "disease_only", "combined"],
        "budget_per_candidate": args.budget_per_candidate,
        "retrieved_unique_candidate_strategy_records": len(records),
        "retrieval_failures": len(failures),
        "records_path": str(records_path),
        "failures_path": str(failures_path),
        "annotation_status": "All records are UNANNOTATED; queries do not determine SUPPORT/CONTRADICT.",
    }
    metadata_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
