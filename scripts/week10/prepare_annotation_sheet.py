from __future__ import annotations

"""Create a blinded, deduplicated article-annotation sheet and private join files."""

import argparse
import json
import secrets
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "outputs/week10/retrieval_records.jsonl"
OUTPUT = ROOT / "outputs/week10/retrieval_annotation_sheet.csv"
STRATEGY_MANIFEST = ROOT / "outputs/week10/retrieval_strategy_manifest.csv"
STRATEGY_KEY = ROOT / "outputs/week10/retrieval_strategy_key.csv"

STRATEGIES = ("fixed", "uncertainty_only", "disease_only", "combined")
PAIR_KEY = ["candidate_id", "record_id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--strategy-manifest", type=Path, default=STRATEGY_MANIFEST)
    parser.add_argument("--strategy-key", type=Path, default=STRATEGY_KEY)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Retrieval records not found: {args.input}")

    rows = []
    with args.input.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise SystemExit("No retrieved records. Annotation sheet not created.")

    required = set(PAIR_KEY + ["strategy", "record_id", "title", "source_url"])
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Retrieval records missing required fields: {missing}")

    observed = set(frame["strategy"].dropna().astype(str))
    if not observed.issubset(set(STRATEGIES)):
        raise ValueError(f"Unexpected retrieval strategies: {sorted(observed-set(STRATEGIES))}")

    # The same candidate/publication can be found by more than one strategy.
    # Check metadata consistency, then expose it once for human annotation.
    metadata_columns = [
        column for column in (
            "drug_name", "gene_symbol", "disease_name", "title", "abstract",
            "publication_year", "journal", "source_url",
        ) if column in frame.columns
    ]
    conflicts = {}
    for column in metadata_columns:
        counts = frame.groupby(PAIR_KEY, dropna=False)[column].nunique(dropna=False)
        if (counts > 1).any():
            conflicts[column] = int((counts > 1).sum())
    if conflicts:
        raise ValueError(
            "Conflicting article/candidate metadata across strategies: "
            f"{conflicts}"
        )

    annotation = frame.drop_duplicates(PAIR_KEY, keep="first").copy()
    annotation["evidence_category"] = ""
    annotation["direction_label"] = ""
    annotation["annotation_rationale"] = ""
    annotation["annotator"] = ""
    annotation["annotation_status"] = "PENDING"

    # Randomize opaque codes per run. Neither strategy nor retrieval intent is
    # exposed in the sheet. The manifest and key stay local until annotation ends.
    names = sorted(observed)
    secrets.SystemRandom().shuffle(names)
    codes = [f"POLICY_{index + 1}" for index in range(len(names))]
    strategy_map = dict(zip(names, codes))

    manifest = frame[PAIR_KEY + ["strategy"]].drop_duplicates().copy()
    manifest["strategy_code"] = manifest["strategy"].map(strategy_map)
    manifest = manifest.drop(columns=["strategy"])

    key_frame = pd.DataFrame(
        [
            {"strategy_code": code, "strategy": strategy}
            for strategy, code in strategy_map.items()
        ]
    ).sort_values("strategy_code")

    visible_columns = [
        "candidate_id", "drug_name", "gene_symbol", "disease_name",
        "record_id", "title", "abstract", "publication_year",
        "journal", "source_url", "evidence_category", "direction_label",
        "annotation_rationale", "annotator", "annotation_status",
    ]
    visible_columns = [
        column for column in visible_columns if column in annotation.columns
    ]

    for path in (args.output, args.strategy_manifest, args.strategy_key):
        path.parent.mkdir(parents=True, exist_ok=True)

    annotation[visible_columns].to_csv(args.output, index=False)
    manifest.to_csv(args.strategy_manifest, index=False)
    key_frame.to_csv(args.strategy_key, index=False)

    print(f"Unique candidate-publication annotation rows: {len(annotation):,}")
    print(f"Saved blinded worksheet: {args.output}")
    print(f"Saved private retrieval-strategy manifest: {args.strategy_manifest}")
    print(f"Saved private strategy code key: {args.strategy_key}")
    print("Do not share the manifest or key with annotators.")
    print("Allowed evidence_category: MECHANISTIC, DISEASE_CONTEXT, COUNTER, SAFETY, OTHER")
    print("Allowed direction_label: SUPPORT, CONTRADICT, UNKNOWN")
    print("Annotate the article content, not search intent. UNKNOWN is not CONTRADICT.")


if __name__ == "__main__":
    main()
