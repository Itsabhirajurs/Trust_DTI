
"""
TrustDTI Week 09:
Validate UniProt-to-Ensembl mappings against Open Targets 26.09.

Input:
    UniProt-Ensembl mapping candidates
    Network 1 protein accessions
    Open Targets target-index Parquet shards

Outputs:
    Target index
    UniProt-to-Open Targets bridge
    Per-accession validation summary
    Validation issues
    Audit JSON

Preserves all one-to-many mappings.
Does not arbitrarily select ambiguous gene identifiers.
Does not modify Network 1 or UniProt input datasets.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import json
import re

import pandas as pd
import requests
import pyarrow.parquet as pq

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

RELEASE = "26.09"

TARGET_URL = (
    f"https://ftp.ebi.ac.uk/pub/databases/"
    f"opentargets/platform/{RELEASE}/output/target/"
)

DOWNLOAD_DIR = (
    ROOT / "data" / "external"
    / "opentargets" / RELEASE / "target"
)

# One canonical output directory throughout this script.
OUTPUT_DIR = (
    ROOT / "outputs" / "week09_network2"
)

TIMEOUT = 120
CHUNK_SIZE = 1024 * 1024

ENSEMBL_PATTERN = re.compile(
    r"^(ENSG\d{11})(?:\.\d+)?$"
)


# ============================================================
# 2. PREPARE DIRECTORIES
# ============================================================

DOWNLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# 3. HTTP SESSION WITH RETRIES
# ============================================================

retry = Retry(
    total=5,
    connect=5,
    read=5,
    status=5,
    backoff_factor=1,
    status_forcelist=[
        429,
        500,
        502,
        503,
        504,
    ],
    allowed_methods=frozenset(["GET"]),
    respect_retry_after_header=True,
)

session = requests.Session()

session.mount(
    "https://",
    HTTPAdapter(max_retries=retry),
)

session.headers.update({
    "User-Agent": "TrustDTI-Research/1.0"
})


# ============================================================
# 4. PARQUET DIRECTORY LINK PARSER
# ============================================================

class ParquetLinkParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):

        if tag.lower() != "a":
            return

        attributes = dict(attrs)

        href = attributes.get("href")

        if not href:
            return

        parsed = urlparse(href)

        if parsed.path.lower().endswith(".parquet"):

            self.links.append(
                urljoin(TARGET_URL, href)
            )


# ============================================================
# 5. DISCOVER PARQUET SHARDS
# ============================================================

def discover_parquet_files():

    print("\n" + "=" * 65)
    print("DISCOVERING OPEN TARGETS PARQUET SHARDS")
    print("=" * 65)

    response = session.get(
        TARGET_URL,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    parser = ParquetLinkParser()
    parser.feed(response.text)

    files = sorted(set(parser.links))

    if not files:
        raise RuntimeError(
            "No Parquet files found in Open Targets target directory."
        )

    print("Release:", RELEASE)
    print("Parquet shards:", len(files))

    for index, url in enumerate(files[:10], start=1):

        filename = urlparse(url).path.rsplit("/", 1)[-1]

        print(f"{index}. {filename}")

    if len(files) > 10:
        print(f"... and {len(files) - 10} more")

    return files


# ============================================================
# 6. VALIDATE EXISTING PARQUET FILES
# ============================================================

def is_valid_parquet(path: Path) -> bool:

    if not path.exists() or path.stat().st_size == 0:
        return False

    try:

        parquet_file = pq.ParquetFile(path)

        return parquet_file.metadata.num_rows > 0

    except Exception:

        return False


# ============================================================
# 7. DOWNLOAD PARQUET FILES
# ============================================================

def download_one_file(url: str) -> Path:

    filename = urlparse(url).path.rsplit("/", 1)[-1]

    destination = DOWNLOAD_DIR / filename

    temporary = destination.with_suffix(
        destination.suffix + ".part"
    )

    # Reuse previously downloaded valid shards.
    if is_valid_parquet(destination):

        print("Already downloaded and validated:", filename)

        return destination

    # Remove any incomplete or invalid previous copy.
    if destination.exists():
        destination.unlink()

    if temporary.exists():
        temporary.unlink()

    print("\nDownloading:", filename)

    try:

        with session.get(
            url,
            stream=True,
            timeout=TIMEOUT,
        ) as response:

            response.raise_for_status()

            expected_size = response.headers.get(
                "Content-Length"
            )

            downloaded_size = 0

            with temporary.open("wb") as handle:

                for chunk in response.iter_content(
                    chunk_size=CHUNK_SIZE
                ):

                    if not chunk:
                        continue

                    handle.write(chunk)
                    downloaded_size += len(chunk)

            if (
                expected_size is not None
                and downloaded_size != int(expected_size)
            ):

                raise IOError(
                    f"Incomplete download: {filename}"
                )

        if downloaded_size == 0:
            raise IOError("Downloaded Parquet file is empty.")

        # Validate before replacing the destination.
        parquet_file = pq.ParquetFile(temporary)

        if parquet_file.metadata.num_rows == 0:
            raise IOError("Parquet file has zero rows.")

        temporary.replace(destination)

        print(
            "Downloaded:",
            filename,
            f"({downloaded_size / (1024 * 1024):.2f} MB)",
        )

        return destination

    except Exception:

        if temporary.exists():
            temporary.unlink()

        raise


def download_all_files(urls):

    downloaded = []

    for index, url in enumerate(urls, start=1):

        print(
            f"\nShard {index}/{len(urls)}"
        )

        downloaded.append(
            download_one_file(url)
        )

    return downloaded


# ============================================================
# 8. INSPECT TARGET DATASET SCHEMA
# ============================================================

def inspect_schema(parquet_files):

    print("\n" + "=" * 65)
    print("INSPECTING OPEN TARGETS SCHEMA")
    print("=" * 65)

    schema = pq.read_schema(parquet_files[0])

    columns = schema.names

    print("Available columns:")

    for column in columns:
        print(" -", column)

    required = [
        "id",
        "approvedSymbol",
        "biotype",
    ]

    missing = [
        column
        for column in required
        if column not in columns
    ]

    if missing:
        raise ValueError(
            f"Required target columns missing: {missing}"
        )

    has_protein_ids = "proteinIds" in columns

    print(
        "\nUniProt cross-reference available:",
        has_protein_ids,
    )

    return has_protein_ids


# ============================================================
# 9. LOAD OPEN TARGETS TARGET INDEX
# ============================================================

def load_target_index(
    parquet_files,
    has_protein_ids,
):

    print("\n" + "=" * 65)
    print("LOADING OPEN TARGETS TARGET INDEX")
    print("=" * 65)

    columns = [
        "id",
        "approvedSymbol",
        "biotype",
    ]

    if has_protein_ids:
        columns.append("proteinIds")

    frames = []

    for index, path in enumerate(
        parquet_files,
        start=1,
    ):

        print(
            f"Reading shard {index}/{len(parquet_files)}:",
            path.name,
        )

        frame = pd.read_parquet(
            path,
            columns=columns,
        )

        frames.append(frame)

    targets = pd.concat(
        frames,
        ignore_index=True,
    )

    if targets.empty:
        raise RuntimeError(
            "Open Targets target index is empty."
        )

    targets = targets.dropna(
        subset=["id"]
    ).copy()

    targets["id"] = (
        targets["id"]
        .astype("string")
        .str.strip()
    )

    # Remove optional Ensembl version suffixes for matching.
    targets["ensembl_gene_id"] = (
        targets["id"]
        .str.replace(
            r"\.\d+$",
            "",
            regex=True,
        )
    )

    targets["approvedSymbol"] = (
        targets["approvedSymbol"]
        .astype("string")
        .str.strip()
    )

    targets["biotype"] = (
        targets["biotype"]
        .astype("string")
        .str.strip()
    )

    print("\nTarget-index rows:", len(targets))

    print(
        "Unique target IDs:",
        targets["id"].nunique(),
    )

    print(
        "Unique stable Ensembl IDs:",
        targets["ensembl_gene_id"].nunique(),
    )

    # Detect conflicting annotations before deduplicating.
    duplicate_ids = targets[
        targets["ensembl_gene_id"].duplicated(keep=False)
    ]

    if not duplicate_ids.empty:

        conflicts = (
            duplicate_ids.groupby("ensembl_gene_id")
            .agg(
                symbol_count=("approvedSymbol", "nunique"),
                biotype_count=("biotype", "nunique"),
            )
        )

        conflicting = conflicts[
            (conflicts["symbol_count"] > 1)
            | (conflicts["biotype_count"] > 1)
        ]

        if not conflicting.empty:

            raise ValueError(
                "Conflicting Open Targets annotations found:\n"
                f"{conflicting.head(10)}"
            )

        print(
            "Repeated stable IDs with consistent annotations:",
            len(duplicate_ids),
        )

        # Keep one record only after consistency checks.
        targets = targets.drop_duplicates(
            "ensembl_gene_id",
            keep="first",
        )

    return targets


# ============================================================
# 10. ROBUST UNIPROT CROSS-REFERENCE CHECK
# ============================================================

def has_uniprot_cross_reference(
    protein_ids,
    accession,
):
    """
    Handle nested proteinIds values returned by Parquet.

    Supported representations:
        list
        tuple
        NumPy array
        list of dictionaries
        list of objects exposing an id attribute
    """

    if protein_ids is None:
        return False

    if isinstance(protein_ids, (str, bytes, dict)):
        return False

    try:
        iterator = iter(protein_ids)

    except TypeError:
        return False

    accession = str(accession).strip().upper()

    for item in iterator:

        if isinstance(item, dict):

            identifier = item.get("id")

        elif isinstance(item, str):

            identifier = item

        else:

            identifier = getattr(
                item,
                "id",
                None,
            )

            if identifier is None and hasattr(item, "get"):
                identifier = item.get("id")

        if (
            identifier is not None
            and str(identifier).strip().upper() == accession
        ):

            return True

    return False


# ============================================================
# 11. LOAD UNIPROT MAPPING FILES
# ============================================================

def load_mapping_files():

    print("\n" + "=" * 65)
    print("LOADING UNIPROT-ENSEMBL MAPPINGS")
    print("=" * 65)

    candidates_path = (
        OUTPUT_DIR / "uniprot_ensembl_gene_candidates.csv"
    )

    coverage_path = (
        OUTPUT_DIR / "uniprot_ensembl_accession_coverage.csv"
    )

    for path in [
        candidates_path,
        coverage_path,
    ]:

        if not path.exists():
            raise FileNotFoundError(path)

    candidates = pd.read_csv(
        candidates_path,
        dtype="string",
    )

    coverage = pd.read_csv(
        coverage_path,
        dtype="string",
    )

    required_candidate_columns = [
        "uniprot_accession",
        "ensembl_gene_id",
        "ensembl_gene_id_versioned",
    ]

    required_coverage_columns = [
        "uniprot_accession",
        "mapping_status",
        "ensembl_gene_count",
    ]

    for column in required_candidate_columns:

        if column not in candidates.columns:
            raise ValueError(
                f"Missing mapping candidate column: {column}"
            )

    for column in required_coverage_columns:

        if column not in coverage.columns:
            raise ValueError(
                f"Missing coverage column: {column}"
            )

    candidates["uniprot_accession"] = (
        candidates["uniprot_accession"]
        .str.strip()
        .str.upper()
    )

    coverage["uniprot_accession"] = (
        coverage["uniprot_accession"]
        .str.strip()
        .str.upper()
    )

    candidates["ensembl_gene_id"] = (
        candidates["ensembl_gene_id"]
        .str.strip()
        .str.replace(
            r"\.\d+$",
            "",
            regex=True,
        )
    )

    if coverage["uniprot_accession"].duplicated().any():

        raise ValueError(
            "UniProt coverage table contains duplicate accessions."
        )

    print(
        "UniProt accessions:",
        coverage["uniprot_accession"].nunique(),
    )

    print(
        "Ensembl candidate rows:",
        len(candidates),
    )

    return candidates, coverage


# ============================================================
# 12. VALIDATE ENSEMBL TARGET MEMBERSHIP
# ============================================================

def build_target_bridge(
    candidates,
    coverage,
    targets,
    has_protein_ids,
):

    print("\n" + "=" * 65)
    print("VALIDATING TARGET MEMBERSHIP")
    print("=" * 65)

    target_columns = [
        "ensembl_gene_id",
        "id",
        "approvedSymbol",
        "biotype",
    ]

    if has_protein_ids:
        target_columns.append("proteinIds")

    target_lookup = targets[
        target_columns
    ].copy()

    target_lookup = target_lookup.rename(
        columns={
            "id": "opentargets_target_id",
            "approvedSymbol": "approved_gene_symbol",
            "biotype": "target_biotype",
            "proteinIds": "opentargets_protein_ids",
        }
    )

    # Deduplicate candidate gene mappings without choosing
    # one candidate over another.
    candidate_columns = [
        "uniprot_accession",
        "ensembl_gene_id",
        "ensembl_gene_id_versioned",
    ]

    if "ensembl_version" in candidates.columns:
        candidate_columns.append("ensembl_version")

    candidate_subset = candidates[
        candidate_columns
    ].drop_duplicates()

    # One row per UniProt-to-Ensembl candidate.
    bridge = coverage.merge(
        candidate_subset,
        on="uniprot_accession",
        how="left",
        validate="one_to_many",
    )

    # Attach Open Targets target metadata.
    bridge = bridge.merge(
        target_lookup,
        on="ensembl_gene_id",
        how="left",
        validate="many_to_one",
    )

    bridge["target_present"] = (
        bridge["opentargets_target_id"].notna()
    )

    if has_protein_ids:

        bridge["uniprot_direct_match"] = bridge.apply(
            lambda row: (
                has_uniprot_cross_reference(
                    row["opentargets_protein_ids"],
                    row["uniprot_accession"],
                )
                if row["target_present"]
                else False
            ),
            axis=1,
        )

    else:

        bridge["uniprot_direct_match"] = pd.NA

    # Classification is descriptive; it does not resolve
    # one-to-many mappings automatically.
    def classify_target(row):

        if pd.isna(row["ensembl_gene_id"]):
            return "NO_ENSEMBL_MAPPING"

        if not row["target_present"]:
            return "ENSEMBL_ID_NOT_IN_OPENTARGETS"

        if has_protein_ids:

            if row["uniprot_direct_match"]:
                return "TARGET_FOUND_AND_UNIPROT_XREF_MATCH"

            return "TARGET_FOUND_BUT_UNIPROT_XREF_NOT_MATCHED"

        return "TARGET_FOUND_XREF_UNAVAILABLE"

    bridge["target_validation_status"] = bridge.apply(
        classify_target,
        axis=1,
    )

    bridge["opentargets_release"] = RELEASE

    return bridge


# ============================================================
# 13. BUILD PER-ACCESSION SUMMARY
# ============================================================

def build_accession_summary(
    bridge,
    coverage,
    has_protein_ids,
):

    summaries = []

    for _, accession_row in coverage.iterrows():

        accession = accession_row["uniprot_accession"]

        group = bridge.loc[
            bridge["uniprot_accession"].eq(accession)
        ]

        candidate_ids = (
            group["ensembl_gene_id"]
            .dropna()
            .unique()
            .tolist()
        )

        found_ids = (
            group.loc[
                group["target_present"],
                "ensembl_gene_id",
            ]
            .dropna()
            .unique()
            .tolist()
        )

        direct_match_ids = (
            group.loc[
                group["uniprot_direct_match"].fillna(False),
                "ensembl_gene_id",
            ]
            .dropna()
            .unique()
            .tolist()
        )

        candidate_count = len(candidate_ids)
        found_count = len(found_ids)
        direct_count = len(direct_match_ids)

        if candidate_count == 0:

            validation_status = "NO_ENSEMBL_MAPPING"

        elif found_count == 0:

            validation_status = "NO_OPENTARGETS_TARGET"

        elif candidate_count == 1:

            if not has_protein_ids:

                validation_status = (
                    "ONE_TO_ONE_TARGET_FOUND_XREF_UNAVAILABLE"
                )

            elif direct_count == 1:

                validation_status = (
                    "ONE_TO_ONE_TARGET_XREF_CONFIRMED"
                )

            else:

                validation_status = (
                    "ONE_TO_ONE_TARGET_XREF_NOT_CONFIRMED"
                )

        else:

            # Do not resolve one-to-many mappings automatically.
            if direct_count > 0:

                validation_status = (
                    "ONE_TO_MANY_REVIEW_REQUIRED_XREF_AVAILABLE"
                )

            else:

                validation_status = (
                    "ONE_TO_MANY_REVIEW_REQUIRED"
                )

        summaries.append({

            "uniprot_accession": accession,

            "original_mapping_status": (
                accession_row["mapping_status"]
            ),

            "ensembl_candidate_count": candidate_count,

            "opentargets_targets_found": found_count,

            "opentargets_targets_missing": (
                candidate_count - found_count
            ),

            "direct_uniprot_xref_candidate_count": direct_count,

            "target_validation_status": validation_status,

        })

    return pd.DataFrame(summaries)


# ============================================================
# 14. SAVE OUTPUTS AND AUDIT
# ============================================================

def save_outputs(
    targets,
    bridge,
    accession_summary,
    coverage,
    has_protein_ids,
    parquet_files,
):

    # FIXED: OUTPUT_DIR is explicitly defined in configuration.
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_output = (
        OUTPUT_DIR / "opentargets_target_index.csv"
    )

    bridge_output = (
        OUTPUT_DIR / "uniprot_opentargets_target_bridge.csv"
    )

    summary_output = (
        OUTPUT_DIR / "uniprot_opentargets_accession_summary.csv"
    )

    issues_output = (
        OUTPUT_DIR / "opentargets_target_validation_issues.csv"
    )

    audit_output = (
        OUTPUT_DIR / "opentargets_target_validation_audit.json"
    )

    # Save slim target index.
    targets.drop(
        columns=["proteinIds"],
        errors="ignore",
    ).to_csv(
        target_output,
        index=False,
    )

    # Save bridge without nested proteinIds structures.
    bridge.drop(
        columns=["opentargets_protein_ids"],
        errors="ignore",
    ).to_csv(
        bridge_output,
        index=False,
    )

    accession_summary.to_csv(
        summary_output,
        index=False,
    )

    # Keep unresolved candidates and ambiguous mappings
    # visible for review.
    ambiguous_accessions = set(
        accession_summary.loc[
            accession_summary["ensembl_candidate_count"].astype(int) > 1,
            "uniprot_accession",
        ]
    )

    xref_unconfirmed = (
        bridge["target_present"]
        & bridge["uniprot_direct_match"].eq(False)
        if has_protein_ids
        else pd.Series(False, index=bridge.index)
    )

    target_missing = (
        bridge["ensembl_gene_id"].notna()
        & ~bridge["target_present"]
    )

    ambiguous_rows = bridge[
        "uniprot_accession"
    ].isin(ambiguous_accessions)

    issues = bridge.loc[
        target_missing
        | xref_unconfirmed
        | ambiguous_rows
    ].copy()

    issues.drop(
        columns=["opentargets_protein_ids"],
        errors="ignore",
    ).to_csv(
        issues_output,
        index=False,
    )

    # --------------------------------------------------------
    # Audit calculations
    # --------------------------------------------------------

    total_accessions = len(coverage)

    mapped_accessions = int(
        coverage["ensembl_gene_count"]
        .astype(int)
        .gt(0)
        .sum()
    )

    target_found = int(
        accession_summary["opentargets_targets_found"]
        .gt(0)
        .sum()
    )

    direct_match_accessions = int(
        accession_summary["direct_uniprot_xref_candidate_count"]
        .gt(0)
        .sum()
    )

    status_distribution = (
        accession_summary["target_validation_status"]
        .value_counts()
        .to_dict()
    )

    audit = {

        "project": "TrustDTI",

        "task": "Open Targets target-index validation",

        "release": RELEASE,

        "source_url": TARGET_URL,

        "retrieved_at_utc": (
            datetime.now(timezone.utc).isoformat()
        ),

        "downloaded_parquet_shards": len(parquet_files),

        "target_index_rows": int(len(targets)),

        "target_index_unique_ids": int(
            targets["ensembl_gene_id"].nunique()
        ),

        "input_uniprot_accessions": total_accessions,

        "accessions_with_ensembl_mapping": mapped_accessions,

        "accessions_with_at_least_one_opentargets_target": (
            target_found
        ),

        "accessions_without_any_opentargets_target": (
            total_accessions - target_found
        ),

        "accessions_with_direct_uniprot_xref": (
            direct_match_accessions
        ),

        "protein_ids_cross_reference_available": (
            has_protein_ids
        ),

        "mapping_candidates_total": int(
            bridge["ensembl_gene_id"].notna().sum()
        ),

        "candidate_targets_found": int(
            bridge["target_present"].sum()
        ),

        "candidate_targets_not_found": int(
            (
                bridge["ensembl_gene_id"].notna()
                & ~bridge["target_present"]
            ).sum()
        ),

        "protein_coding_candidate_records": int(
            bridge["target_biotype"]
            .eq("protein_coding")
            .sum()
        ),

        "ambiguous_accessions_preserved": int(
            accession_summary[
                "ensembl_candidate_count"
            ].astype(int).gt(1).sum()
        ),

        "target_validation_status_distribution": {
            str(key): int(value)
            for key, value in status_distribution.items()
        },

        "opentargets_target_found_percentage": round(
            target_found / total_accessions * 100,
            4,
        ),

        "outputs": {
            "target_index": str(target_output),
            "target_bridge": str(bridge_output),
            "accession_summary": str(summary_output),
            "validation_issues": str(issues_output),
        },

    }

    with audit_output.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            audit,
            handle,
            indent=2,
        )

    return audit


# ============================================================
# 15. MAIN WORKFLOW
# ============================================================

def main():

    print("\n" + "=" * 70)
    print("TRUSTDTI: OPEN TARGETS 26.09 TARGET VALIDATION")
    print("=" * 70)

    print("\nOutput directory:")
    print(OUTPUT_DIR)

    # Step 1: Discover shards.
    urls = discover_parquet_files()

    # Step 2: Download or reuse existing shards.
    parquet_files = download_all_files(urls)

    # Step 3: Inspect schema.
    has_protein_ids = inspect_schema(parquet_files)

    # Step 4: Load target index.
    targets = load_target_index(
        parquet_files,
        has_protein_ids,
    )

    # Step 5: Load UniProt-Ensembl mappings.
    candidates, coverage = load_mapping_files()

    # Step 6: Validate target membership.
    bridge = build_target_bridge(
        candidates,
        coverage,
        targets,
        has_protein_ids,
    )

    # Step 7: Build accession summary.
    accession_summary = build_accession_summary(
        bridge,
        coverage,
        has_protein_ids,
    )

    # Step 8: Save reports and audit.
    audit = save_outputs(
        targets,
        bridge,
        accession_summary,
        coverage,
        has_protein_ids,
        parquet_files,
    )

    # ========================================================
    # FINAL RESULTS
    # ========================================================

    print("\n" + "=" * 70)
    print("FINAL OPEN TARGETS VALIDATION")
    print("=" * 70)

    print(
        json.dumps(
            audit,
            indent=2,
        )
    )

    print("\nACCESSION VALIDATION STATUS")

    print(
        accession_summary[
            "target_validation_status"
        ]
        .value_counts()
        .to_string()
    )

    print("\nFIRST 20 VALIDATED TARGET MAPPINGS")

    print(
        bridge[
            [
                "uniprot_accession",
                "ensembl_gene_id",
                "approved_gene_symbol",
                "target_biotype",
                "target_present",
                "uniprot_direct_match",
                "target_validation_status",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print("\nOUTPUT FILES")

    for filename in [
        "opentargets_target_index.csv",
        "uniprot_opentargets_target_bridge.csv",
        "uniprot_opentargets_accession_summary.csv",
        "opentargets_target_validation_issues.csv",
        "opentargets_target_validation_audit.json",
    ]:

        print(OUTPUT_DIR / filename)

    print("\nOPEN TARGETS VALIDATION COMPLETED SUCCESSFULLY.")


# ============================================================
# 16. ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print("\nExecution interrupted.")

        raise

    except Exception as error:

        print("\n" + "=" * 65)
        print("OPEN TARGETS VALIDATION FAILED")
        print("=" * 65)

        print(type(error).__name__ + ":", str(error))

        raise
