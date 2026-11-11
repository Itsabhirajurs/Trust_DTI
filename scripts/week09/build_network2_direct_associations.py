from __future__ import annotations

import csv
import gc
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import requests


# ============================================================
# TRUSTDTI - NETWORK 2 DIRECT ASSOCIATION EXTRACTION
# Open Targets Platform release 26.09
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OPENTARGETS_BASE = (
    "https://ftp.ebi.ac.uk/pub/databases/opentargets/"
    "platform/26.09/output/"
)

ASSOCIATION_URL = (
    OPENTARGETS_BASE + "association_by_datasource_direct/"
)

DISEASE_URL = OPENTARGETS_BASE + "disease/"

BRIDGE_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "week09_network2"
    / "uniprot_opentargets_primary_bridge.csv"
)

EXISTING_FIRST_SHARD = (
    PROJECT_ROOT
    / "data"
    / "external"
    / "opentargets"
    / "26.09"
    / "association_schema_check"
    / "parquet"
)

TEMP_DIR = (
    PROJECT_ROOT
    / "data"
    / "external"
    / "opentargets"
    / "26.09"
    / "_network2_download_tmp"
)

DISEASE_LOCAL_DIR = (
    PROJECT_ROOT
    / "data"
    / "external"
    / "opentargets"
    / "26.09"
    / "disease"
)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "week09_network2"

OUTPUT_PARQUET = (
    PROCESSED_DIR / "network2_direct_associations.parquet"
)

OUTPUT_AUDIT = (
    OUTPUT_DIR / "network2_direct_association_audit.json"
)

OUTPUT_SOURCE_COUNTS = (
    OUTPUT_DIR / "network2_association_source_counts.csv"
)

OUTPUT_MANIFEST = (
    OUTPUT_DIR / "network2_download_manifest.csv"
)

OUTPUT_DISEASE_SCHEMA = (
    OUTPUT_DIR / "opentargets_disease_schema.json"
)

OUTPUT_DISEASE_SAMPLE = (
    OUTPUT_DIR / "opentargets_disease_sample.json"
)

RELEASE = "26.09"
BATCH_SIZE = 100_000
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


# ============================================================
# DIRECTORY LISTING PARSER
# ============================================================

class ParquetLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return

        for key, value in attrs:
            if key.lower() == "href" and value:
                decoded = unquote(value)

                if decoded.lower().endswith(".parquet"):
                    self.links.append(value)


def discover_parquet_files(
    session: requests.Session,
    directory_url: str,
) -> list[str]:

    response = session.get(
        directory_url,
        timeout=(30, 90),
    )
    response.raise_for_status()

    parser = ParquetLinkParser()
    parser.feed(response.text)

    links = sorted(set(parser.links))

    return [
        urljoin(directory_url, link)
        for link in links
    ]


# ============================================================
# FILE HASHING AND DOWNLOAD
# ============================================================

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        while True:
            chunk = file.read(DOWNLOAD_CHUNK_SIZE)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def download_parquet(
    session: requests.Session,
    file_url: str,
    destination: Path,
) -> tuple[Path, str]:

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_suffix(
        destination.suffix + ".part"
    )

    print(f"\nDownloading: {destination.name}")

    with session.get(
        file_url,
        stream=True,
        timeout=(30, 180),
    ) as response:

        response.raise_for_status()

        total_bytes = int(
            response.headers.get("Content-Length", 0)
        )

        downloaded_bytes = 0
        last_reported_mb = -1

        with open(temporary_path, "wb") as file:
            for chunk in response.iter_content(
                chunk_size=DOWNLOAD_CHUNK_SIZE
            ):
                if not chunk:
                    continue

                file.write(chunk)
                downloaded_bytes += len(chunk)

                downloaded_mb = downloaded_bytes // (
                    10 * 1024 * 1024
                )

                if downloaded_mb > last_reported_mb:
                    last_reported_mb = downloaded_mb

                    if total_bytes:
                        percent = (
                            downloaded_bytes / total_bytes
                        ) * 100

                        print(
                            f"\r  "
                            f"{downloaded_bytes / 1024 / 1024:.1f} MB "
                            f"({percent:.1f}%)",
                            end="",
                        )
                    else:
                        print(
                            f"\r  "
                            f"{downloaded_bytes / 1024 / 1024:.1f} MB",
                            end="",
                        )

    temporary_path.replace(destination)

    print("\n  Download complete.")

    return destination, sha256_file(destination)


# ============================================================
# JSON-SAFE CONVERSION
# ============================================================

def make_json_safe(value):
    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            make_json_safe(item)
            for item in value
        ]

    if hasattr(value, "as_py"):
        return make_json_safe(value.as_py())

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


# ============================================================
# LOAD AND VALIDATE HIGH-CONFIDENCE TARGET BRIDGE
# ============================================================

def load_target_bridge():

    print("\n" + "=" * 70)
    print("LOADING HIGH-CONFIDENCE TARGET BRIDGE")
    print("=" * 70)

    if not BRIDGE_PATH.exists():
        raise FileNotFoundError(
            f"Required bridge file not found:\n{BRIDGE_PATH}"
        )

    bridge = pd.read_csv(
        BRIDGE_PATH,
        dtype=str,
    )

    required_columns = [
        "uniprot_accession",
        "ensembl_gene_id",
        "approved_gene_symbol",
        "target_biotype",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in bridge.columns
    ]

    if missing_columns:
        raise ValueError(
            "Bridge file is missing required columns: "
            + ", ".join(missing_columns)
        )

    bridge = bridge.dropna(
        subset=[
            "uniprot_accession",
            "ensembl_gene_id",
        ]
    ).copy()

    for column in required_columns:
        bridge[column] = (
            bridge[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    if bridge["ensembl_gene_id"].duplicated().any():
        duplicates = bridge.loc[
            bridge["ensembl_gene_id"].duplicated(keep=False),
            "ensembl_gene_id",
        ].tolist()

        raise ValueError(
            "Duplicate Ensembl target IDs in the primary bridge. "
            f"Examples: {duplicates[:10]}"
        )

    if bridge["uniprot_accession"].duplicated().any():
        raise ValueError(
            "Duplicate UniProt accessions found in the primary bridge."
        )

    target_mapping = {}

    for row in bridge.itertuples(index=False):
        target_mapping[row.ensembl_gene_id] = {
            "uniprot_accession": row.uniprot_accession,
            "approved_gene_symbol": row.approved_gene_symbol,
            "target_biotype": row.target_biotype,
        }

    print(f"High-confidence UniProt accessions: {len(bridge):,}")
    print(
        "Unique Ensembl target IDs: "
        f"{len(target_mapping):,}"
    )

    print("\nTarget biotype counts:")
    print(
        bridge["target_biotype"]
        .value_counts(dropna=False)
        .to_string()
    )

    return bridge, target_mapping


def close_and_remove_shard(
    parquet_file: pq.ParquetFile,
    local_path: Path,
    should_remove: bool,
) -> bool:
    """
    Explicitly release the Parquet reader before attempting Windows file cleanup.

    Returns True when cleanup is complete (or deletion was not requested).
    Returns False when Windows still prevents deletion; the file is retained
    so a later run can reuse it instead of crashing.
    """
    try:
        parquet_file.close(force=True)
    except Exception as error:
        print(f"WARNING: Could not force-close Parquet reader: {error}")
        return False

    gc.collect()

    if not should_remove:
        return True

    if not local_path.exists():
        return True

    try:
        local_path.unlink()
        return True
    except PermissionError as error:
        print(
            "WARNING: Windows still holds the temporary shard; "
            f"retaining it for reuse. Details: {error}"
        )
        return False


# ============================================================
# PROCESS ASSOCIATION SHARDS
# ============================================================

def process_association_shards(
    session: requests.Session,
    bridge: pd.DataFrame,
    target_mapping: dict,
):

    print("\n" + "=" * 70)
    print("DISCOVERING DIRECT ASSOCIATION SHARDS")
    print("=" * 70)

    shard_urls = discover_parquet_files(
        session,
        ASSOCIATION_URL,
    )

    if not shard_urls:
        raise RuntimeError(
            "No Parquet shards discovered in the association dataset."
        )

    print(f"Release: {RELEASE}")
    print(f"Association shards discovered: {len(shard_urls)}")

    target_ids = set(target_mapping.keys())

    target_value_array = pa.array(
        sorted(target_ids),
        type=pa.string(),
    )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    partial_output = OUTPUT_PARQUET.with_suffix(
        ".parquet.partial"
    )

    if partial_output.exists():
        partial_output.unlink()

    writer = None
    base_schema = None
    output_schema = None

    total_input_rows = 0
    total_target_rows = 0
    total_written_rows = 0
    total_non_datasource_rows = 0

    matched_targets = set()
    disease_ids = set()
    unique_association_keys = set()

    datasource_counts = Counter()
    aggregation_type_counts = Counter()

    score_sum = 0.0
    score_count = 0
    score_min = None
    score_max = None

    total_evidence_count = 0

    shard_audit = []
    manifest_rows = []

    try:
        for shard_number, shard_url in enumerate(
            shard_urls,
            start=1,
        ):

            filename = Path(
                shard_url.split("?")[0]
            ).name

            print("\n" + "-" * 70)
            print(
                f"SHARD {shard_number}/{len(shard_urls)}: "
                f"{filename}"
            )

            # Reuse the schema-inspection download for shard 1.
            existing_path = (
                EXISTING_FIRST_SHARD / filename
            )

            if (
                shard_number == 1
                and existing_path.exists()
                and existing_path.stat().st_size > 1_000_000
            ):
                local_path = existing_path
                file_hash = sha256_file(local_path)
                reused_existing = True

                print(
                    "Reusing existing first-shard download: "
                    f"{local_path}"
                )

            else:
                local_path = TEMP_DIR / filename

                local_path, file_hash = download_parquet(
                    session,
                    shard_url,
                    local_path,
                )

                reused_existing = False

            file_size = local_path.stat().st_size

            parquet_file = pq.ParquetFile(local_path)
            input_schema = parquet_file.schema_arrow

            required_input_columns = [
                "diseaseId",
                "targetId",
                "aggregationType",
                "aggregationValue",
                "associationScore",
                "evidenceCount",
                "timeseries",
                "currentNovelty",
            ]

            missing = [
                column
                for column in required_input_columns
                if column not in input_schema.names
            ]

            if missing:
                raise ValueError(
                    f"{filename} is missing columns: {missing}"
                )

            if base_schema is None:
                base_schema = input_schema

                output_schema = (
                    base_schema
                    .append(
                        pa.field(
                            "uniprot_accession",
                            pa.string(),
                        )
                    )
                    .append(
                        pa.field(
                            "approved_gene_symbol",
                            pa.string(),
                        )
                    )
                    .append(
                        pa.field(
                            "target_biotype",
                            pa.string(),
                        )
                    )
                    .append(
                        pa.field(
                            "opentargets_release",
                            pa.string(),
                        )
                    )
                )

            elif not input_schema.equals(
                base_schema,
                check_metadata=False,
            ):
                raise ValueError(
                    "Parquet schema mismatch detected in "
                    f"{filename}. Stopping to prevent mixed-schema output."
                )

            shard_input_rows = parquet_file.metadata.num_rows
            shard_target_rows = 0
            shard_written_rows = 0

            total_input_rows += shard_input_rows

            print(
                f"Input rows: {shard_input_rows:,} "
                f"| Row groups: {parquet_file.num_row_groups}"
            )

            # Read in batches rather than loading the entire shard.
            for batch in parquet_file.iter_batches(
                batch_size=BATCH_SIZE,
            ):

                batch_table = pa.Table.from_batches([batch])

                target_mask = pc.is_in(
                    batch_table.column("targetId"),
                    value_set=target_value_array,
                )

                target_mask = pc.fill_null(
                    target_mask,
                    False,
                )

                matched_table = batch_table.filter(
                    target_mask
                )

                if matched_table.num_rows == 0:
                    continue

                shard_target_rows += matched_table.num_rows
                total_target_rows += matched_table.num_rows

                # This dataset is grouped by datasource.
                # Keep datasource-level rows only.
                aggregation_type_counts.update(
                    value
                    for value in matched_table[
                        "aggregationType"
                    ].to_pylist()
                    if value is not None
                )

                datasource_mask = pc.equal(
                    matched_table["aggregationType"],
                    "datasourceId",
                )

                datasource_mask = pc.fill_null(
                    datasource_mask,
                    False,
                )

                source_rows = matched_table.filter(
                    datasource_mask
                )

                excluded_rows = (
                    matched_table.num_rows
                    - source_rows.num_rows
                )

                total_non_datasource_rows += excluded_rows

                if source_rows.num_rows == 0:
                    continue

                target_batch_ids = source_rows[
                    "targetId"
                ].to_pylist()

                # Attach the direct UniProt-to-Ensembl bridge.
                source_rows = source_rows.append_column(
                    "uniprot_accession",
                    pa.array(
                        [
                            target_mapping[target_id][
                                "uniprot_accession"
                            ]
                            for target_id in target_batch_ids
                        ],
                        type=pa.string(),
                    ),
                )

                source_rows = source_rows.append_column(
                    "approved_gene_symbol",
                    pa.array(
                        [
                            target_mapping[target_id][
                                "approved_gene_symbol"
                            ]
                            for target_id in target_batch_ids
                        ],
                        type=pa.string(),
                    ),
                )

                source_rows = source_rows.append_column(
                    "target_biotype",
                    pa.array(
                        [
                            target_mapping[target_id][
                                "target_biotype"
                            ]
                            for target_id in target_batch_ids
                        ],
                        type=pa.string(),
                    ),
                )

                source_rows = source_rows.append_column(
                    "opentargets_release",
                    pa.array(
                        [RELEASE] * source_rows.num_rows,
                        type=pa.string(),
                    ),
                )

                # Capture audit statistics from the retained rows.
                matched_targets.update(target_batch_ids)

                disease_values = source_rows[
                    "diseaseId"
                ].to_pylist()

                disease_ids.update(
                    value
                    for value in disease_values
                    if value is not None
                )

                datasource_values = source_rows[
                    "aggregationValue"
                ].to_pylist()

                datasource_counts.update(
                    str(value)
                    for value in datasource_values
                    if value is not None
                )

                score_values = source_rows[
                    "associationScore"
                ].to_pylist()

                for value in score_values:
                    if value is None:
                        continue

                    value = float(value)

                    score_sum += value
                    score_count += 1

                    score_min = (
                        value
                        if score_min is None
                        else min(score_min, value)
                    )

                    score_max = (
                        value
                        if score_max is None
                        else max(score_max, value)
                    )

                evidence_values = source_rows[
                    "evidenceCount"
                ].to_pylist()

                total_evidence_count += sum(
                    int(value)
                    for value in evidence_values
                    if value is not None
                )

                # Count repeated target-disease-source keys
                # without deleting any source records.
                for target_id, disease_id, datasource_id in zip(
                    target_batch_ids,
                    disease_values,
                    datasource_values,
                ):
                    unique_association_keys.add(
                        (
                            target_id,
                            disease_id,
                            datasource_id,
                        )
                    )

                if writer is None:
                    writer = pq.ParquetWriter(
                        partial_output,
                        output_schema,
                        compression="zstd",
                    )

                writer.write_table(
                    source_rows,
                    row_group_size=50_000,
                )

                shard_written_rows += source_rows.num_rows
                total_written_rows += source_rows.num_rows

            print(
                f"Rows linked to primary target bridge: "
                f"{shard_target_rows:,}"
            )

            print(
                f"Datasource-level rows retained: "
                f"{shard_written_rows:,}"
            )

            shard_audit.append(
                {
                    "shard": filename,
                    "url": shard_url,
                    "file_size_bytes": file_size,
                    "input_rows": shard_input_rows,
                    "target_matched_rows": shard_target_rows,
                    "datasource_rows_written": shard_written_rows,
                    "reused_existing_download": reused_existing,
                    "sha256": file_hash,
                }
            )

            manifest_rows.append(
                {
                    "release": RELEASE,
                    "dataset": "association_by_datasource_direct",
                    "filename": filename,
                    "url": shard_url,
                    "file_size_bytes": file_size,
                    "sha256": file_hash,
                    "reused_existing_download": reused_existing,
                }
            )

            # Close the native Parquet reader before deleting the shard.
            # Windows otherwise may raise WinError 32 even after iteration ends.
            cleanup_completed = close_and_remove_shard(
                parquet_file,
                local_path,
                should_remove=not reused_existing,
            )
            del parquet_file
            gc.collect()

            if not reused_existing and cleanup_completed:
                print("Temporary shard removed.")

        if writer is not None:
            writer.close()
            writer = None

        if total_written_rows == 0:
            raise RuntimeError(
                "No datasource-level association rows matched "
                "the high-confidence target bridge."
            )

        # Publish the completed Parquet only after every shard succeeds.
        os.replace(
            partial_output,
            OUTPUT_PARQUET,
        )

    except Exception:
        if writer is not None:
            writer.close()

        if partial_output.exists():
            partial_output.unlink()

        raise

    # --------------------------------------------------------
    # WRITE SOURCE COUNTS AND DOWNLOAD MANIFEST
    # --------------------------------------------------------

    source_total = sum(datasource_counts.values())

    with open(
        OUTPUT_SOURCE_COUNTS,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        fieldnames = [
            "datasource_id",
            "record_count",
            "percentage_of_retained_rows",
        ]

        csv_writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        csv_writer.writeheader()

        for datasource_id, count in (
            datasource_counts.most_common()
        ):
            csv_writer.writerow(
                {
                    "datasource_id": datasource_id,
                    "record_count": count,
                    "percentage_of_retained_rows": round(
                        count / source_total * 100,
                        4,
                    ) if source_total else 0,
                }
            )

    with open(
        OUTPUT_MANIFEST,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        fieldnames = [
            "release",
            "dataset",
            "filename",
            "url",
            "file_size_bytes",
            "sha256",
            "reused_existing_download",
        ]

        csv_writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        csv_writer.writeheader()
        csv_writer.writerows(manifest_rows)

    average_score = (
        score_sum / score_count
        if score_count
        else None
    )

    audit = {
        "project": "TrustDTI",
        "task": "Open Targets direct association filtering",
        "release": RELEASE,
        "retrieved_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_dataset": ASSOCIATION_URL,
        "input_shards_discovered": len(shard_urls),
        "input_rows_total": total_input_rows,
        "primary_bridge_accessions": len(bridge),
        "primary_bridge_target_ids": len(target_mapping),
        "rows_matching_primary_target_bridge": total_target_rows,
        "datasource_level_rows_written": total_written_rows,
        "non_datasource_rows_excluded": total_non_datasource_rows,
        "unique_target_ids_with_associations": len(matched_targets),
        "primary_targets_without_association_rows": sorted(
            target_ids - matched_targets
        ),
        "unique_disease_ids": len(disease_ids),
        "unique_target_disease_datasource_keys": len(
            unique_association_keys
        ),
        "duplicate_target_disease_datasource_rows": (
            total_written_rows
            - len(unique_association_keys)
        ),
        "aggregation_type_counts_for_matched_targets": dict(
            aggregation_type_counts
        ),
        "datasource_record_counts": dict(
            datasource_counts
        ),
        "association_score_summary": {
            "count": score_count,
            "mean": average_score,
            "minimum": score_min,
            "maximum": score_max,
        },
        "sum_of_evidence_count": total_evidence_count,
        "shard_audit": shard_audit,
        "outputs": {
            "filtered_parquet": str(OUTPUT_PARQUET),
            "source_counts_csv": str(OUTPUT_SOURCE_COUNTS),
            "download_manifest_csv": str(OUTPUT_MANIFEST),
        },
        "interpretation_note": (
            "associationScore is an Open Targets source-level "
            "association score. It is not a calibrated probability "
            "or proof of causality. Source-specific rows are retained "
            "separately and are not averaged or summed here."
        ),
    }

    with open(
        OUTPUT_AUDIT,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            audit,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "=" * 70)
    print("DIRECT ASSOCIATION FILTERING SUMMARY")
    print("=" * 70)

    print(f"Input shards processed: {len(shard_urls)}")
    print(f"Input rows across all shards: {total_input_rows:,}")
    print(
        "Rows matching the primary target bridge: "
        f"{total_target_rows:,}"
    )
    print(
        "Datasource-level rows retained: "
        f"{total_written_rows:,}"
    )
    print(
        "Unique targets represented: "
        f"{len(matched_targets):,}"
    )
    print(f"Unique disease IDs: {len(disease_ids):,}")
    print(
        "Unique target-disease-source keys: "
        f"{len(unique_association_keys):,}"
    )
    print(
        "Duplicate key rows retained for audit: "
        f"{total_written_rows - len(unique_association_keys):,}"
    )

    print("\nTop data sources:")
    for source, count in datasource_counts.most_common(15):
        print(f"  {source}: {count:,}")

    print("\nSaved:")
    print(OUTPUT_PARQUET)
    print(OUTPUT_SOURCE_COUNTS)
    print(OUTPUT_MANIFEST)
    print(OUTPUT_AUDIT)

    return disease_ids


# ============================================================
# DOWNLOAD AND INSPECT DISEASE METADATA
# ============================================================

def inspect_disease_metadata(
    session: requests.Session,
):

    print("\n" + "=" * 70)
    print("DOWNLOADING AND INSPECTING DISEASE METADATA")
    print("=" * 70)

    disease_files = discover_parquet_files(
        session,
        DISEASE_URL,
    )

    if not disease_files:
        raise RuntimeError(
            "No disease metadata Parquet file was discovered."
        )

    DISEASE_LOCAL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # The current release listing is expected to contain one
    # disease metadata file. Inspect all files if more appear.
    disease_summaries = []

    for file_url in disease_files:
        filename = Path(file_url.split("?")[0]).name
        local_path = DISEASE_LOCAL_DIR / filename

        if (
            not local_path.exists()
            or local_path.stat().st_size < 1_000_000
        ):
            local_path, _ = download_parquet(
                session,
                file_url,
                local_path,
            )
        else:
            print(
                f"Using existing disease file: {local_path}"
            )

        parquet_file = pq.ParquetFile(local_path)
        schema = parquet_file.schema_arrow

        print(f"\nFile: {filename}")
        print(f"Rows: {parquet_file.metadata.num_rows:,}")
        print(f"Columns: {len(schema.names)}")

        column_details = []

        for field in schema:
            column_details.append(
                {
                    "name": field.name,
                    "type": str(field.type),
                    "nullable": field.nullable,
                }
            )

            print(
                f"  {field.name}: {field.type}"
            )

        sample_batch = next(
            parquet_file.iter_batches(
                batch_size=3,
            ),
            None,
        )

        sample_rows = (
            sample_batch.to_pylist()
            if sample_batch is not None
            else []
        )

        safe_sample = [
            make_json_safe(row)
            for row in sample_rows
        ]

        disease_summaries.append(
            {
                "file": filename,
                "url": file_url,
                "rows": parquet_file.metadata.num_rows,
                "columns": column_details,
                "local_path": str(local_path),
            }
        )

        with open(
            OUTPUT_DISEASE_SAMPLE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                safe_sample,
                file,
                indent=2,
                ensure_ascii=False,
            )

        print("\nFirst disease metadata records:")
        print(
            json.dumps(
                safe_sample,
                indent=2,
                ensure_ascii=False,
            )
        )

    with open(
        OUTPUT_DISEASE_SCHEMA,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            disease_summaries,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\nDisease metadata inspection saved:")
    print(OUTPUT_DISEASE_SCHEMA)
    print(OUTPUT_DISEASE_SAMPLE)


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "TrustDTI-Network2-Research/1.0"
        }
    )

    try:
        bridge, target_mapping = load_target_bridge()

        process_association_shards(
            session,
            bridge,
            target_mapping,
        )

        inspect_disease_metadata(session)

        print("\n" + "=" * 70)
        print("NETWORK 2 ASSOCIATION EXTRACTION COMPLETED")
        print("=" * 70)

    except requests.RequestException as error:
        print(f"\nNETWORK ERROR: {error}")
        raise

    except Exception as error:
        print(f"\nPROCESSING ERROR: {error}")
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()