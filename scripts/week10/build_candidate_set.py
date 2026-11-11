from __future__ import annotations

"""Create a fixed, label-blind literature retrieval candidate set."""

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import requests

from src.network.router import derive_anchor_thresholds, classify_anchor


PREDICTIONS = PROJECT_ROOT / "reports/model_baseline/baseline_predictions_random_morgan_family.csv"
BRIDGE = PROJECT_ROOT / "outputs/week09_network2/uniprot_opentargets_primary_bridge.csv"
NETWORK2 = PROJECT_ROOT / "data/processed/network2_overall_direct.parquet"
OUTPUT_DIR = PROJECT_ROOT / "data/processed"
AUDIT_DIR = PROJECT_ROOT / "outputs/week10"
VALIDATION_AUDIT = AUDIT_DIR / "network2_validation_audit.json"
OUTPUT_CSV = OUTPUT_DIR / "week10_candidates.csv"
CACHE = AUDIT_DIR / "pubchem_title_cache.json"
PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{}/property/Title/JSON"


def resolve_pubchem_title(inchikey: str, timeout: tuple[int, int] = (10, 25)) -> tuple[str, str]:
    try:
        response = requests.get(
            PUBCHEM_URL.format(inchikey),
            timeout=timeout,
            headers={"User-Agent": "TrustDTI/0.1 research candidate name resolver"},
        )
        if response.status_code == 404:
            return "", "NOT_FOUND"
        response.raise_for_status()
        props = response.json().get("PropertyTable", {}).get("Properties", [])
        title = props[0].get("Title") if props else None
        return (str(title).strip(), "PUBCHEM_INCHIKEY") if title else ("", "NO_TITLE")
    except Exception as exc:
        return "", f"ERROR:{type(exc).__name__}"


def add_drug_names(frame: pd.DataFrame) -> pd.DataFrame:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    unique = sorted(set(frame["pik"].astype(str)))
    missing = [key for key in unique if key not in cache]
    print(f"Resolving {len(missing)} new compound InChIKeys through PubChem...")
    # Keep concurrency modest to avoid unnecessary load on the public service.
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(resolve_pubchem_title, key): key for key in missing}
        for future in as_completed(futures):
            key = futures[future]
            try:
                title, status = future.result()
            except Exception as exc:
                title, status = "", f"ERROR:{type(exc).__name__}"
            cache[key] = {"title": title, "status": status}
    CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    frame = frame.copy()
    frame["drug_name"] = frame["pik"].map(
        lambda key: cache.get(str(key), {}).get("title") or f"compound {key}"
    )
    frame["drug_name_source"] = frame["pik"].map(
        lambda key: cache.get(str(key), {}).get("status", "MISSING")
    )
    return frame


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-state", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-candidates", type=int, default=48)
    args = parser.parse_args()
    if args.per_state < 1 or args.max_candidates < 1:
        parser.error("per-state and max-candidates must be positive.")
    return args


def main():
    args = parse_args()
    for path in (PREDICTIONS, BRIDGE, NETWORK2):
        if not path.exists():
            raise SystemExit(f"Required file is missing: {path}")

    if not VALIDATION_AUDIT.exists():
        raise SystemExit(
            "Network 2 validation audit is missing. Run "
            "scripts/week10/validate_network2.py before building candidates."
        )
    validation = json.loads(VALIDATION_AUDIT.read_text(encoding="utf-8"))
    if not validation.get("all_critical_checks_passed", False):
        raise SystemExit(
            "Network 2 validation has not passed. Do not build retrieval candidates."
        )

    predictions = pd.read_csv(PREDICTIONS, dtype={"pik": str, "accession": str})
    required = {"pik", "accession", "p_active", "conformal_set"}
    if not required.issubset(predictions.columns):
        raise ValueError(f"Baseline predictions missing {sorted(required-set(predictions.columns))}")
    # The observed label column is intentionally discarded before candidate selection.
    predictions = predictions[list(required)].copy()
    predictions["p_active"] = pd.to_numeric(predictions["p_active"], errors="raise")

    bridge = pd.read_csv(BRIDGE, dtype=str)
    bridge = bridge[[
        "uniprot_accession", "ensembl_gene_id", "approved_gene_symbol", "target_biotype"
    ]].drop_duplicates("uniprot_accession")

    network_columns = [
        "uniprot_accession", "targetId", "diseaseId",
        "associationScore", "evidenceCount", "currentNovelty",
        "disease_name",
    ]
    network = pd.read_parquet(NETWORK2, columns=network_columns)
    must = {
        "uniprot_accession", "targetId", "diseaseId", "associationScore",
        "disease_name", "edge_provenance",
    }
    if not must.issubset(network.columns):
        raise ValueError(f"Network 2 parquet missing {sorted(must-set(network.columns))}")

    bridge_target_by_accession = bridge.set_index(
        "uniprot_accession"
    )["ensembl_gene_id"].to_dict()
    expected_targets = network["uniprot_accession"].astype(str).map(
        bridge_target_by_accession
    )
    target_mismatches = (
        expected_targets.isna()
        | network["targetId"].astype(str).ne(expected_targets)
    )
    if target_mismatches.any():
        examples = network.loc[
            target_mismatches,
            ["uniprot_accession", "targetId"],
        ].head(5).to_dict(orient="records")
        raise SystemExit(
            "Network 2 target mapping conflicts with the validated bridge. "
            f"Examples: {examples}"
        )

    scores = pd.to_numeric(network["associationScore"], errors="coerce").dropna()
    thresholds = derive_anchor_thresholds(scores)
    network["associationScore"] = pd.to_numeric(network["associationScore"], errors="coerce")
    network = network.sort_values(
        ["uniprot_accession", "associationScore", "evidenceCount"],
        ascending=[True, False, False],
        kind="mergesort",
    )
    top = network.drop_duplicates("uniprot_accession", keep="first")[[
        "uniprot_accession", "targetId", "diseaseId", "disease_name",
        "associationScore", "evidenceCount", "currentNovelty",
    ]]

    merged = predictions.merge(bridge, on="uniprot_accession", how="inner", validate="many_to_one")
    merged = merged.merge(top, on="uniprot_accession", how="left", validate="many_to_one")
    merged["anchor_tier"] = [
        classify_anchor(score, pd.notna(score), thresholds)
        for score in merged["associationScore"]
    ]
    merged["conformal_state"] = merged["conformal_set"].map(
        lambda value: (
            "ACTIVE_ONLY" if str(value).upper() == "ACTIVE"
            else "INACTIVE_ONLY" if str(value).upper() == "INACTIVE"
            else "UNCERTAIN" if set(str(value).upper().split("|")) == {"ACTIVE", "INACTIVE"}
            else "INVALID"
        )
    )
    merged = merged[merged["conformal_state"] != "INVALID"].copy()

    selected_parts = []
    for state, group in merged.groupby("conformal_state", sort=True):
        sample = group.sample(
            n=min(args.per_state, len(group)),
            random_state=args.seed + len(selected_parts),
        )
        selected_parts.append(sample)

    selected = pd.concat(selected_parts, ignore_index=True) if selected_parts else merged.head(0)
    selected = selected.drop_duplicates(["pik", "accession"])
    if len(selected) > args.max_candidates:
        selected = selected.sample(n=args.max_candidates, random_state=args.seed)

    selected = add_drug_names(selected)
    selected["candidate_id"] = [
        hashlib.sha256(
            (
                f"{row.pik}|{row.accession}|"
                f"{'NO_DISEASE' if pd.isna(row.diseaseId) else row.diseaseId}"
            ).encode()
        ).hexdigest()[:16]
        for row in selected.itertuples(index=False)
    ]

    output_cols = [
        "candidate_id", "pik", "drug_name", "drug_name_source",
        "accession", "ensembl_gene_id", "approved_gene_symbol", "target_biotype",
        "diseaseId", "disease_name", "associationScore", "evidenceCount",
        "currentNovelty", "anchor_tier", "p_active", "conformal_set",
        "conformal_state",
    ]
    selected = selected[output_cols].rename(columns={
        "accession": "uniprot_accession",
        "ensembl_gene_id": "target_id",
        "approved_gene_symbol": "gene_symbol",
        "diseaseId": "disease_id",
        "disease_name": "disease_name",
        "associationScore": "anchor_score",
    })
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    selected.to_csv(OUTPUT_CSV, index=False)

    audit = {
        "candidate_count": len(selected),
        "candidate_state_counts": selected["conformal_state"].value_counts().to_dict(),
        "anchor_tier_counts": selected["anchor_tier"].value_counts().to_dict(),
        "anchor_thresholds": thresholds,
        "candidate_selection_seed": args.seed,
        "per_state_requested": args.per_state,
        "max_candidates": args.max_candidates,
        "baseline_source": str(PREDICTIONS),
        "network2_source": str(NETWORK2),
        "label_blind_selection": True,
        "true_label_column_used": False,
        "drug_names_resolved": int(selected["drug_name_source"].eq("PUBCHEM_INCHIKEY").sum()),
        "drug_names_unresolved": int((~selected["drug_name_source"].eq("PUBCHEM_INCHIKEY")).sum()),
        "output": str(OUTPUT_CSV),
        "interpretation": (
            "A fixed, seed-controlled candidate set drawn from the random-split test predictions. "
            "The observed DTI label is excluded before candidate selection. One top overall-direct "
            "disease association is selected per protein for this prototype."
        ),
    }
    (AUDIT_DIR / "candidate_build_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
