from __future__ import annotations

"""Run or evaluate the final TrustDTI Week 11 local experiment.

The script deliberately stops at the first failed gate. Raw data, retrieved
abstracts, blinded annotations, the strategy key, and run outputs stay local.
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "outputs" / "week11"
STATUS_PATH = OUTPUT_DIR / "week11_execution_status.json"

VALIDATION_AUDIT = ROOT / "outputs/week10/network2_validation_audit.json"
CANDIDATE_AUDIT = ROOT / "outputs/week10/candidate_build_audit.json"
CANDIDATES = ROOT / "data/processed/week10_candidates.csv"
RETRIEVAL_META = ROOT / "outputs/week10/retrieval_run_metadata.json"
RETRIEVAL_RECORDS = ROOT / "outputs/week10/retrieval_records.jsonl"
ANNOTATION_SHEET = ROOT / "outputs/week10/retrieval_annotation_sheet.csv"
STRATEGY_MANIFEST = ROOT / "outputs/week10/retrieval_strategy_manifest.csv"
STRATEGY_KEY = ROOT / "outputs/week10/retrieval_strategy_key.csv"
EVALUATION = OUTPUT_DIR / "retrieval_policy_comparison.json"

EXPECTED_STRATEGIES = ("fixed", "uncertainty_only", "disease_only", "combined")
VALID_LABELS = {"SUPPORT", "CONTRADICT", "UNKNOWN"}
VALID_CATEGORIES = {"MECHANISTIC", "DISEASE_CONTEXT", "COUNTER", "SAFETY", "OTHER"}

REQUIRED_LOCAL_INPUTS = (
    ROOT / "reports/model_baseline/baseline_predictions_random_morgan_family.csv",
    ROOT / "outputs/week09_network2/uniprot_opentargets_primary_bridge.csv",
    ROOT / "data/processed/network2_direct_associations.parquet",
    ROOT / "data/processed/network2_overall_direct.parquet",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required run artifact is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required CSV is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_candidate_audit(audit: Mapping[str, Any], max_candidates: int) -> int:
    count = int(audit.get("candidate_count", 0))
    if not audit.get("label_blind_selection", False):
        raise ValueError("Candidate audit does not confirm label-blind selection.")
    if audit.get("true_label_column_used") is not False:
        raise ValueError("Candidate audit does not confirm observed labels were excluded.")
    if count < 1 or count > max_candidates:
        raise ValueError(
            f"Candidate count {count} is outside the requested range 1..{max_candidates}."
        )
    return count


def validate_retrieval_metadata(
    metadata: Mapping[str, Any],
    expected_candidates: int,
    budget: int,
) -> int:
    strategies = tuple(metadata.get("strategies", ()))
    if set(strategies) != set(EXPECTED_STRATEGIES) or len(strategies) != len(EXPECTED_STRATEGIES):
        raise ValueError(f"Retrieval run did not declare all four expected strategies: {strategies}")
    if int(metadata.get("candidate_count", -1)) != expected_candidates:
        raise ValueError("Retrieval candidate count differs from the fixed candidate set.")
    if int(metadata.get("budget_per_candidate", -1)) != budget:
        raise ValueError("Retrieval budget differs from the requested matched budget.")
    records = int(metadata.get("retrieved_unique_candidate_strategy_records", 0))
    if records < 1:
        raise ValueError("Europe PMC returned no usable records; inspect retrieval_failures.json.")
    return records


def validate_retrieval_records(
    path: Path,
    expected_candidate_ids: set[str],
    budget: int,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Retrieval JSONL is missing: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on retrieval line {line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Retrieval line {line_number} is not a JSON object.")
            rows.append(row)

    if not rows:
        raise ValueError("Europe PMC retrieval JSONL is empty.")
    counts: dict[tuple[str, str], int] = {}
    unique_records: set[tuple[str, str, str]] = set()
    strategy_counts = {strategy: 0 for strategy in EXPECTED_STRATEGIES}
    candidates_seen: set[str] = set()
    for row in rows:
        candidate_id = str(row.get("candidate_id") or "").strip()
        strategy = str(row.get("strategy") or "").strip().lower()
        record_id = str(row.get("record_id") or "").strip()
        if candidate_id not in expected_candidate_ids:
            raise ValueError(f"Retrieval contains candidate outside the fixed pool: {candidate_id!r}")
        if strategy not in EXPECTED_STRATEGIES:
            raise ValueError(f"Unexpected retrieval strategy in JSONL: {strategy!r}")
        if not record_id:
            raise ValueError("Retrieved publication is missing a stable record_id.")
        if str(row.get("annotation_status") or "").upper() != "UNANNOTATED":
            raise ValueError("Retrieved records must remain UNANNOTATED until human review.")
        if row.get("direction_label") not in (None, ""):
            raise ValueError("Retrieval output must not auto-assign evidence direction.")
        key = (candidate_id, strategy, record_id)
        if key in unique_records:
            raise ValueError(f"Duplicate candidate-strategy-publication row: {key}")
        unique_records.add(key)
        pair = (candidate_id, strategy)
        counts[pair] = counts.get(pair, 0) + 1
        strategy_counts[strategy] += 1
        candidates_seen.add(candidate_id)

    over_budget = {
        f"{candidate}|{strategy}": count
        for (candidate, strategy), count in counts.items()
        if count > budget
    }
    if over_budget:
        raise ValueError(f"Retrieval exceeded matched per-candidate budget: {over_budget}")
    return {
        "record_count": len(rows),
        "candidate_count_with_retrieval": len(candidates_seen),
        "strategy_record_counts": strategy_counts,
        "candidate_ids_with_retrieval": sorted(candidates_seen),
        "max_documents_for_any_candidate_strategy": max(counts.values(), default=0),
        "matched_budget_respected": True,
    }


def annotation_completion_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    materialized = list(rows)
    pending = []
    invalid = []
    for index, row in enumerate(materialized, start=2):
        label = str(row.get("direction_label", "")).strip().upper()
        category = str(row.get("evidence_category", "")).strip().upper()
        rationale = str(row.get("annotation_rationale", "")).strip()
        if label not in VALID_LABELS:
            pending.append(index)
        if category not in VALID_CATEGORIES or not rationale:
            invalid.append(index)
    return {
        "rows_total": len(materialized),
        "rows_with_valid_direction_label": len(materialized) - len(pending),
        "rows_pending_or_invalid_label": pending,
        "rows_missing_category_or_rationale": invalid,
        "complete": bool(materialized) and not pending and not invalid,
    }


def run_command(name: str, command: list[str], log: list[dict[str, Any]]) -> None:
    print(f"\n=== {name} ===", flush=True)
    started = utc_now()
    completed = subprocess.run(command, cwd=ROOT, check=False)
    log.append({
        "step": name,
        "command": command,
        "started_at_utc": started,
        "completed_at_utc": utc_now(),
        "returncode": completed.returncode,
    })
    if completed.returncode != 0:
        raise RuntimeError(
            f"{name} failed with exit code {completed.returncode}; inspect the output above."
        )


def run_prepare(args: argparse.Namespace) -> dict[str, Any]:
    status: dict[str, Any] = {
        "project": "TrustDTI",
        "milestone": "Week 11 final completion sprint",
        "phase": "prepare",
        "started_at_utc": utc_now(),
        "gates": {},
        "commands": [],
        "limitations": [
            "The script does not invent, infer or auto-assign human evidence-direction labels.",
            "Local research data and generated abstracts/annotations are not committed.",
        ],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        missing = [str(path.relative_to(ROOT)) for path in REQUIRED_LOCAL_INPUTS if not path.exists()]
        if missing:
            raise FileNotFoundError(
                "Required owner-local datasets are missing. Restore these files before continuing:\n- "
                + "\n- ".join(missing)
            )
        status["gates"]["local_inputs_present"] = True

        if not args.skip_tests:
            run_command("Fast automated test suite", [sys.executable, "-m", "pytest", "-q"], status["commands"])
        status["gates"]["automated_tests"] = "passed" if not args.skip_tests else "not_run_by_request"

        run_command(
            "Network 2 data-backed validation",
            [sys.executable, "scripts/week10/validate_network2.py"],
            status["commands"],
        )
        validation = read_json(VALIDATION_AUDIT)
        if validation.get("all_critical_checks_passed") is not True:
            raise RuntimeError("Network 2 audit did not set all_critical_checks_passed=true.")
        status["gates"]["network2_validation"] = {
            "passed": True,
            "checks": validation.get("checks", {}),
            "validated_at_utc": validation.get("validated_at_utc"),
        }

        run_command(
            "Build fixed label-blind candidate set",
            [
                sys.executable, "scripts/week10/build_candidate_set.py",
                "--per-state", str(args.per_state),
                "--seed", str(args.seed),
                "--max-candidates", str(args.max_candidates),
            ],
            status["commands"],
        )
        candidate_audit = read_json(CANDIDATE_AUDIT)
        candidate_count = validate_candidate_audit(candidate_audit, args.max_candidates)
        candidate_rows = read_csv_rows(CANDIDATES)
        if len(candidate_rows) != candidate_count:
            raise ValueError("Candidate CSV row count does not match candidate_build_audit.json.")
        candidate_ids = [str(row.get("candidate_id") or "").strip() for row in candidate_rows]
        if any(not candidate_id for candidate_id in candidate_ids):
            raise ValueError("Candidate CSV contains an empty candidate_id.")
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("Candidate CSV contains duplicate candidate_id values.")
        status["gates"]["candidate_set"] = {
            "passed": True,
            "candidate_count": candidate_count,
            "seed": args.seed,
            "label_blind": True,
        }

        run_command(
            "Run four Europe PMC retrieval strategies",
            [
                sys.executable, "scripts/week10/run_retrieval_demo.py",
                "--budget-per-candidate", str(args.budget_per_candidate),
            ],
            status["commands"],
        )
        retrieval_meta = read_json(RETRIEVAL_META)
        record_count = validate_retrieval_metadata(
            retrieval_meta, candidate_count, args.budget_per_candidate
        )
        candidate_id_set = set(candidate_ids)
        retrieval_audit = validate_retrieval_records(
            RETRIEVAL_RECORDS, candidate_id_set, args.budget_per_candidate
        )
        if retrieval_audit["record_count"] != record_count:
            raise ValueError("Retrieval JSONL record count does not match the run metadata.")
        failures_path = ROOT / "outputs/week10/retrieval_failures.json"
        if not failures_path.exists():
            raise FileNotFoundError(f"Retrieval failure log is missing: {failures_path}")
        failures = json.loads(failures_path.read_text(encoding="utf-8"))
        if not isinstance(failures, list):
            raise ValueError("Retrieval failure log must be a JSON list.")
        status["gates"]["live_retrieval"] = {
            "passed": True,
            "candidate_count": candidate_count,
            "records": record_count,
            "failures": int(retrieval_meta.get("retrieval_failures", 0)),
            "failure_records_loaded": True,
            "budget_per_candidate": args.budget_per_candidate,
            "strategies": list(EXPECTED_STRATEGIES),
            "record_audit": retrieval_audit,
        }

        run_command(
            "Prepare blinded annotation worksheet",
            [sys.executable, "scripts/week10/prepare_annotation_sheet.py"],
            status["commands"],
        )
        annotation_rows = read_csv_rows(ANNOTATION_SHEET)
        status["gates"]["blinded_annotation_sheet"] = {
            "passed": bool(annotation_rows),
            "unique_candidate_publications": len(annotation_rows),
            "human_annotations_pending": len(annotation_rows),
            "worksheet": str(ANNOTATION_SHEET.relative_to(ROOT)),
            "private_strategy_files": [
                str(STRATEGY_MANIFEST.relative_to(ROOT)),
                str(STRATEGY_KEY.relative_to(ROOT)),
            ],
        }
        if not annotation_rows:
            raise RuntimeError("The annotation worksheet is empty; no evidence records are ready to annotate.")

        status["next_required_action"] = (
            "Complete the blinded worksheet with SUPPORT / CONTRADICT / UNKNOWN, "
            "an evidence category, and a short rationale for every unique candidate-publication."
        )
        status["completed_at_utc"] = utc_now()
        write_json(STATUS_PATH, status)
        print(f"\nWeek 11 preparation completed. Status saved to {STATUS_PATH}")
        return status
    except Exception as exc:
        status["error"] = f"{type(exc).__name__}: {exc}"
        status["completed_at_utc"] = utc_now()
        write_json(STATUS_PATH, status)
        raise


def run_evaluate(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_csv_rows(ANNOTATION_SHEET)
    annotation_summary = annotation_completion_summary(rows)
    if not annotation_summary["complete"]:
        write_json(STATUS_PATH, {
            "project": "TrustDTI",
            "milestone": "Week 11 final completion sprint",
            "phase": "evaluate",
            "updated_at_utc": utc_now(),
            "gates": {"human_annotation": annotation_summary},
            "next_required_action": (
                "Complete every annotation row with a valid direction label, evidence category "
                "and rationale. Do not reveal the private strategy key before annotation is frozen."
            ),
        })
        raise RuntimeError(
            "Evaluation blocked: annotation sheet is incomplete. "
            f"{annotation_summary['rows_pending_or_invalid_label']} rows need direction labels; "
            f"{annotation_summary['rows_missing_category_or_rationale']} rows need category/rationale."
        )

    if not STRATEGY_MANIFEST.exists() or not STRATEGY_KEY.exists():
        raise FileNotFoundError("The private retrieval strategy manifest/key are required for evaluation.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "scripts/week10/evaluate_retrieval.py",
        "--input", str(ANNOTATION_SHEET),
        "--output", str(EVALUATION),
        "--budget-per-candidate", str(args.budget_per_candidate),
        "--candidates", str(CANDIDATES),
        "--strategy-key", str(STRATEGY_KEY),
        "--strategy-manifest", str(STRATEGY_MANIFEST),
    ]
    log: list[dict[str, Any]] = []
    run_command("Evaluate four matched-budget retrieval strategies", command, log)
    result = read_json(EVALUATION)
    if set(result.get("strategies", {})) != set(EXPECTED_STRATEGIES):
        raise ValueError("Evaluation output does not contain all four expected strategy arms.")

    prior = {}
    if STATUS_PATH.exists():
        try:
            prior = read_json(STATUS_PATH)
        except (ValueError, OSError):
            prior = {}
    prior.update({
        "project": "TrustDTI",
        "milestone": "Week 11 final completion sprint",
        "phase": "evaluated",
        "updated_at_utc": utc_now(),
        "gates": {
            **prior.get("gates", {}),
            "human_annotation": {
                "passed": True,
                **annotation_summary,
            },
            "matched_policy_evaluation": {
                "passed": True,
                "output": str(EVALUATION.relative_to(ROOT)),
                "budget_per_candidate": args.budget_per_candidate,
                "strategy_names": list(EXPECTED_STRATEGIES),
            },
        },
        "evaluation_summary": result,
        "evaluation_commands": log,
    })
    prior["next_required_action"] = (
        "Review the metrics and limitations. Keep counter-evidence recall explicitly scoped "
        "to the pooled retrieved candidate set; do not describe it as exhaustive literature recall."
    )
    write_json(STATUS_PATH, prior)
    print(f"\nWeek 11 evaluation completed. Status saved to {STATUS_PATH}")
    return prior


def run_status() -> dict[str, Any]:
    gates: dict[str, Any] = {}
    if VALIDATION_AUDIT.exists():
        audit = read_json(VALIDATION_AUDIT)
        gates["network2_validation"] = bool(audit.get("all_critical_checks_passed"))
    else:
        gates["network2_validation"] = False
    if CANDIDATE_AUDIT.exists():
        audit = read_json(CANDIDATE_AUDIT)
        gates["candidate_set"] = {
            "candidate_count": int(audit.get("candidate_count", 0)),
            "label_blind": bool(audit.get("label_blind_selection", False)),
        }
    else:
        gates["candidate_set"] = False
    if RETRIEVAL_META.exists():
        metadata = read_json(RETRIEVAL_META)
        gates["live_retrieval"] = {
            "records": int(metadata.get("retrieved_unique_candidate_strategy_records", 0)),
            "failures": int(metadata.get("retrieval_failures", 0)),
            "budget_per_candidate": metadata.get("budget_per_candidate"),
        }
    else:
        gates["live_retrieval"] = False
    if ANNOTATION_SHEET.exists():
        gates["human_annotation"] = annotation_completion_summary(read_csv_rows(ANNOTATION_SHEET))
    else:
        gates["human_annotation"] = False
    if EVALUATION.exists():
        result = read_json(EVALUATION)
        gates["matched_policy_evaluation"] = set(result.get("strategies", {})) == set(EXPECTED_STRATEGIES)
    else:
        gates["matched_policy_evaluation"] = False
    status = {
        "project": "TrustDTI",
        "milestone": "Week 11 final completion sprint",
        "updated_at_utc": utc_now(),
        "gates": gates,
    }
    print(json.dumps(status, indent=2))
    return status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "evaluate", "status"), default="prepare")
    parser.add_argument("--per-state", type=int, default=3)
    parser.add_argument("--max-candidates", type=int, default=9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget-per-candidate", type=int, default=5)
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest (not recommended for the final run).")
    args = parser.parse_args()
    if args.per_state < 1 or args.max_candidates < 1:
        parser.error("--per-state and --max-candidates must be positive.")
    if args.max_candidates > 48:
        parser.error("--max-candidates must not exceed 48 for the planned pilot.")
    if args.budget_per_candidate < 0:
        parser.error("--budget-per-candidate must be non-negative.")
    return args


def main() -> None:
    args = parse_args()
    if args.phase == "prepare":
        run_prepare(args)
    elif args.phase == "evaluate":
        run_evaluate(args)
    else:
        run_status()


if __name__ == "__main__":
    main()
