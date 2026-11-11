from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import pyarrow.parquet as pq
import requests


# ------------------------------------------------------------
# PATHS AND SETTINGS
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/opentargets/"
    "platform/26.09/output/association_by_datasource_direct/"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "external"
    / "opentargets"
    / "26.09"
    / "association_schema_check"
)

PARQUET_DIR = OUTPUT_DIR / "parquet"

SCHEMA_JSON = OUTPUT_DIR / "association_schema.json"
SAMPLE_JSON = OUTPUT_DIR / "association_sample_rows.json"

CHUNK_SIZE = 1024 * 1024


# ------------------------------------------------------------
# HTML DIRECTORY LISTING PARSER
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# DOWNLOAD ONE PARQUET SHARD
# ------------------------------------------------------------

def discover_first_shard(session: requests.Session) -> str:
    print("Inspecting Open Targets dataset directory...")

    response = session.get(DATASET_URL, timeout=(30, 90))
    response.raise_for_status()

    parser = ParquetLinkParser()
    parser.feed(response.text)

    links = sorted(set(parser.links))

    if not links:
        raise RuntimeError(
            "No Parquet files were found in the directory listing."
        )

    first_url = urljoin(DATASET_URL, links[0])

    print(f"Parquet shards discovered: {len(links)}")
    print(f"Selected first shard: {links[0]}")

    return first_url


def download_shard(
    session: requests.Session,
    file_url: str,
) -> Path:
    filename = Path(urlparse(file_url).path).name
    local_path = PARQUET_DIR / filename
    temporary_path = local_path.with_suffix(
        local_path.suffix + ".part"
    )

    if local_path.exists() and local_path.stat().st_size > 1_000_000:
        print(f"\nUsing existing download: {local_path}")
        return local_path

    print("\nDownloading the first Parquet shard...")
    print(f"URL: {file_url}")

    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    with session.get(
        file_url,
        stream=True,
        timeout=(30, 180),
    ) as response:
        response.raise_for_status()

        total_bytes = int(response.headers.get("Content-Length", 0))
        downloaded_bytes = 0

        with open(temporary_path, "wb") as file:
            for chunk in response.iter_content(
                chunk_size=CHUNK_SIZE
            ):
                if not chunk:
                    continue

                file.write(chunk)
                downloaded_bytes += len(chunk)

                if total_bytes:
                    percent = (
                        downloaded_bytes / total_bytes
                    ) * 100

                    print(
                        f"\rDownloaded "
                        f"{downloaded_bytes / 1024 / 1024:.1f} MB "
                        f"({percent:.1f}%)",
                        end="",
                    )
                else:
                    print(
                        f"\rDownloaded "
                        f"{downloaded_bytes / 1024 / 1024:.1f} MB",
                        end="",
                    )

    temporary_path.replace(local_path)

    print("\nDownload completed.")
    print(
        f"Local file size: "
        f"{local_path.stat().st_size / 1024 / 1024:.2f} MB"
    )

    return local_path


# ------------------------------------------------------------
# INSPECT PARQUET SCHEMA AND SAMPLE RECORDS
# ------------------------------------------------------------

def inspect_parquet(parquet_path: Path) -> None:
    print("\n" + "=" * 65)
    print("PARQUET SCHEMA INSPECTION")
    print("=" * 65)

    parquet_file = pq.ParquetFile(parquet_path)
    arrow_schema = parquet_file.schema_arrow

    print(f"Rows: {parquet_file.metadata.num_rows:,}")
    print(f"Row groups: {parquet_file.num_row_groups}")
    print(f"Columns: {len(arrow_schema.names)}")

    schema_details = []

    for field in arrow_schema:
        schema_details.append(
            {
                "name": field.name,
                "type": str(field.type),
                "nullable": field.nullable,
            }
        )

        print(
            f"\n{field.name}\n"
            f"    Type: {field.type}\n"
            f"    Nullable: {field.nullable}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(SCHEMA_JSON, "w", encoding="utf-8") as file:
        json.dump(
            {
                "file": parquet_path.name,
                "rows": parquet_file.metadata.num_rows,
                "row_groups": parquet_file.num_row_groups,
                "columns": schema_details,
            },
            file,
            indent=2,
        )

    # Select likely useful fields for the sample, but only
    # when those fields actually exist in the Parquet schema.
    preferred_fields = [
        "targetId",
        "diseaseId",
        "datasourceId",
        "datatypeId",
        "score",
        "associationScore",
        "aggregationType",
        "aggregationValue",
        "evidenceCount",
        "datasourceNiceName",
    ]

    sample_columns = [
        column
        for column in preferred_fields
        if column in arrow_schema.names
    ]

    if not sample_columns:
        sample_columns = arrow_schema.names[:8]

    print("\n" + "=" * 65)
    print("SAMPLE RECORDS")
    print("=" * 65)

    sample_batch = next(
        parquet_file.iter_batches(
            batch_size=5,
            columns=sample_columns,
        ),
        None,
    )

    if sample_batch is None:
        sample_rows = []
    else:
        sample_rows = sample_batch.to_pylist()

    def make_json_safe(value):
        if isinstance(value, dict):
            return {
                str(key): make_json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                make_json_safe(item)
                for item in value[:10]
            ]

        if hasattr(value, "as_py"):
            return make_json_safe(value.as_py())

        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        return str(value)

    safe_rows = [
        make_json_safe(row)
        for row in sample_rows
    ]

    for index, row in enumerate(safe_rows, start=1):
        print(f"\nRecord {index}:")
        print(json.dumps(row, indent=2, ensure_ascii=False))

    with open(SAMPLE_JSON, "w", encoding="utf-8") as file:
        json.dump(
            safe_rows,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "=" * 65)
    print("INSPECTION FILES SAVED")
    print("=" * 65)
    print(SCHEMA_JSON)
    print(SAMPLE_JSON)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "TrustDTI-Network2-Research/1.0"
        }
    )

    try:
        first_shard_url = discover_first_shard(session)
        local_file = download_shard(session, first_shard_url)
        inspect_parquet(local_file)

        print("\nSCHEMA INSPECTION COMPLETED.")

    except requests.RequestException as error:
        print(f"\nNETWORK ERROR: {error}")
        raise

    except Exception as error:
        print(f"\nERROR: {error}")
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()