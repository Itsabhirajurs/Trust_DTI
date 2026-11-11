from __future__ import annotations

"""Build the curated Network 2 anchor table from Open Targets 26.09.

This downloads association_overall_direct (not a handmade average of
source-specific scores), filters it to the validated target bridge, joins
Open Targets disease labels and writes a separate curated edge table.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import requests

from src.network.parquet_io import close_and_remove_shard


RELEASE = "26.09"
BASE_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/opentargets/"
    f"platform/{RELEASE}/output/"
)
ASSOCIATION_URL = BASE_URL + "association_overall_direct/"
DISEASE_URL = BASE_URL + "disease/"

BRIDGE_PATH = PROJECT_ROOT / "outputs/week09_network2/uniprot_opentargets_primary_bridge.csv"
CACHE_ROOT = PROJECT_ROOT / "data/external/opentargets" / RELEASE
ASSOCIATION_CACHE = CACHE_ROOT / "_overall_direct_cache"
DISEASE_CACHE = CACHE_ROOT / "disease"
OUTPUT_DIR = PROJECT_ROOT / "data/processed"
AUDIT_DIR = PROJECT_ROOT / "outputs/week10"

OUTPUT_PARQUET = OUTPUT_DIR / "network2_overall_direct.parquet"
OUTPUT_AUDIT = AUDIT_DIR / "network2_overall_direct_audit.json"
BATCH_SIZE = 100_000
CHUNK_SIZE = 1024 * 1024


class ParquetLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value and unquote(value).lower().endswith(".parquet"):
                self.links.append(value)


def list_parquet_urls(session: requests.Session, url: str) -> list[str]:
    response = session.get(url, timeout=(30, 90))
    response.raise_for_status()
    parser = ParquetLinks()
    parser.feed(response.text)
    return [urljoin(url, link) for link in sorted(set(parser.links))]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def download(session: requests.Session, url: str, path: Path) -> tuple[Path, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 1_000_000:
        return path, sha256_file(path)

    partial = path.with_suffix(path.suffix + ".part")
    with session.get(url, stream=True, timeout=(30, 240)) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for block in response.iter_content(CHUNK_SIZE):
                if block:
                    handle.write(block)
    partial.replace(path)
    return path, sha256_file(path)


def load_bridge() -> tuple[pd.DataFrame, dict[str, dict[str, str]]]:
    if not BRIDGE_PATH.exists():
        raise FileNotFoundError(f"Missing validated bridge: {BRIDGE_PATH}")
    bridge = pd.read_csv(BRIDGE_PATH, dtype=str)
    needed = [
        "uniprot_accession", "ensembl_gene_id",
        "approved_gene_symbol", "target_biotype",
    ]
    missing = sorted(set(needed) - set(bridge.columns))
    if missing:
        raise ValueError(f"Bridge missing columns: {missing}")
    bridge = bridge[needed].dropna().copy()
    for col in needed:
        bridge[col] = bridge[col].astype(str).str.strip()
    if bridge["ensembl_gene_id"].duplicated().any():
        raise ValueError("Bridge contains duplicate Ensembl IDs.")
    target_map = {
        row.ensembl_gene_id: {
            "uniprot_accession": row.uniprot_accession,
            "approved_gene_symbol": row.approved_gene_symbol,
            "target_biotype": row.target_biotype,
        }
        for row in bridge.itertuples(index=False)
    }
    return bridge, target_map




def as_optional_string(value) -> str | None:
    """Convert scalar pandas/Arrow metadata to a nullable Python string."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def as_string_list(value) -> list[str]:
    """Convert pandas/Arrow list-like disease metadata to a Python string list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    try:
        items = list(value)
    except TypeError:
        return []
    result = []
    for item in items:
        if item is None:
            continue
        try:
            if pd.isna(item):
                continue
        except (TypeError, ValueError):
            pass
        result.append(str(item))
    return result

def load_disease_metadata(session: requests.Session) -> tuple[pd.DataFrame, dict]:
    urls = list_parquet_urls(session, DISEASE_URL)
    if not urls:
        raise RuntimeError("No Open Targets disease metadata Parquet file found.")
    frames = []
    schemas = []
    for url in urls:
        name = Path(url.split("?")[0]).name
        local, _ = download(session, url, DISEASE_CACHE / name)
        parquet = pq.ParquetFile(local)
        columns = parquet.schema_arrow.names
        if "id" not in columns or "name" not in columns:
            raise ValueError(f"Disease metadata requires id/name columns; found {columns}")
        selected = [
            col for col in (
                "id", "name", "description", "code",
                "exactSynonyms", "relatedSynonyms", "narrowSynonyms",
                "broadSynonyms", "therapeuticAreas", "version",
            ) if col in columns
        ]
        frames.append(pq.read_table(local, columns=selected).to_pandas())
        schemas.append({"file": name, "rows": parquet.metadata.num_rows, "columns": columns})
        parquet.close(force=True)

    diseases = pd.concat(frames, ignore_index=True).drop_duplicates("id")
    disease_lookup = {}
    for row in diseases.to_dict(orient="records"):
        disease_lookup[str(row["id"])] = row
    return diseases, {"files": schemas, "unique_disease_ids": len(disease_lookup)}


def run() -> dict:
    bridge, target_map = load_bridge()
    target_ids = set(target_map)
    target_set = pa.array(sorted(target_ids), type=pa.string())

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSOCIATION_CACHE.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "TrustDTI/0.1 OpenTargets bulk reader"})
    partial_output = OUTPUT_PARQUET.with_suffix(".parquet.partial")
    if partial_output.exists():
        partial_output.unlink()

    writer = None
    output_schema = None
    association_schema = None
    audit_shards = []
    total_in = total_target = total_out = 0
    matched_targets = set()
    matched_diseases = set()
    score_min = None
    score_max = None

    try:
        urls = list_parquet_urls(session, ASSOCIATION_URL)
        if not urls:
            raise RuntimeError("No association_overall_direct shards found.")
        for i, url in enumerate(urls, 1):
            filename = Path(url.split("?")[0]).name
            local, digest = download(session, url, ASSOCIATION_CACHE / filename)
            parquet = pq.ParquetFile(local)
            names = parquet.schema_arrow.names
            required = {
                "targetId", "diseaseId", "associationScore",
                "evidenceCount", "currentNovelty", "timeseries",
            }
            if not required.issubset(names):
                raise ValueError(f"{filename} schema missing {sorted(required-set(names))}")

            if association_schema is None:
                association_schema = parquet.schema_arrow
                fields = [
                    field for field in association_schema
                    if field.name in required or field.name in {"aggregationType", "aggregationValue", "version"}
                ]
                output_schema = pa.schema(fields + [
                    pa.field("uniprot_accession", pa.string()),
                    pa.field("approved_gene_symbol", pa.string()),
                    pa.field("target_biotype", pa.string()),
                    pa.field("edge_provenance", pa.string()),
                    pa.field("opentargets_release", pa.string()),
                ])
            elif not parquet.schema_arrow.equals(
                association_schema, check_metadata=False
            ):
                raise ValueError(f"Unexpected association schema change in {filename}.")

            in_rows = parquet.metadata.num_rows
            out_rows = 0
            target_rows = 0
            total_in += in_rows
            print(f"[{i}/{len(urls)}] {filename}: {in_rows:,} rows")

            for batch in parquet.iter_batches(batch_size=BATCH_SIZE):
                table = pa.Table.from_batches([batch])
                mask = pc.fill_null(pc.is_in(table["targetId"], value_set=target_set), False)
                filtered = table.filter(mask)
                if filtered.num_rows == 0:
                    continue
                target_rows += filtered.num_rows
                target_ids_batch = filtered["targetId"].to_pylist()
                disease_ids_batch = filtered["diseaseId"].to_pylist()
                scores = filtered["associationScore"].to_pylist()
                matched_targets.update(x for x in target_ids_batch if x is not None)
                matched_diseases.update(x for x in disease_ids_batch if x is not None)
                for score in scores:
                    if score is None:
                        continue
                    score = float(score)
                    score_min = score if score_min is None else min(score_min, score)
                    score_max = score if score_max is None else max(score_max, score)

                for name, getter in (
                    ("uniprot_accession", lambda x: target_map[x]["uniprot_accession"]),
                    ("approved_gene_symbol", lambda x: target_map[x]["approved_gene_symbol"]),
                    ("target_biotype", lambda x: target_map[x]["target_biotype"]),
                ):
                    filtered = filtered.append_column(
                        name, pa.array([getter(x) for x in target_ids_batch], type=pa.string())
                    )
                filtered = filtered.append_column(
                    "edge_provenance", pa.array(["curated"] * filtered.num_rows, type=pa.string())
                )
                filtered = filtered.append_column(
                    "opentargets_release", pa.array([RELEASE] * filtered.num_rows, type=pa.string())
                )
                # Normalize to the declared output schema without changing score values.
                filtered = filtered.select(output_schema.names)
                if writer is None:
                    writer = pq.ParquetWriter(partial_output, output_schema, compression="zstd")
                writer.write_table(filtered, row_group_size=50_000)
                out_rows += filtered.num_rows
                total_out += filtered.num_rows

            total_target += target_rows
            print(f"  mapped targets: {target_rows:,}; written: {out_rows:,}")
            close_and_remove_shard(parquet, local, should_remove=False)
            audit_shards.append({
                "filename": filename,
                "url": url,
                "sha256": digest,
                "input_rows": in_rows,
                "target_matched_rows": target_rows,
                "rows_written": out_rows,
                "file_bytes": local.stat().st_size,
            })

        if writer is not None:
            writer.close()
            writer = None
        if total_out == 0:
            raise RuntimeError("No overall direct association rows matched the target bridge.")
        os.replace(partial_output, OUTPUT_PARQUET)

        diseases, disease_audit = load_disease_metadata(session)
        disease_lookup = {
            str(row["id"]): row for row in diseases.to_dict(orient="records")
        }

        # Add the disease annotation columns in a second streaming pass.
        final_tmp = OUTPUT_PARQUET.with_name(OUTPUT_PARQUET.stem + ".joined.partial.parquet")
        reader = pq.ParquetFile(OUTPUT_PARQUET)
        joined_writer = None
        disease_missing = 0
        join_columns = [
            "disease_name", "disease_description", "disease_code",
            "disease_exact_synonyms", "disease_therapeutic_areas",
        ]
        schema_with_disease = reader.schema_arrow.append(pa.field("disease_name", pa.string()))
        schema_with_disease = schema_with_disease.append(pa.field("disease_description", pa.string()))
        schema_with_disease = schema_with_disease.append(pa.field("disease_code", pa.string()))
        schema_with_disease = schema_with_disease.append(pa.field("disease_exact_synonyms", pa.list_(pa.string())))
        schema_with_disease = schema_with_disease.append(pa.field("disease_therapeutic_areas", pa.list_(pa.string())))

        for batch in reader.iter_batches(batch_size=BATCH_SIZE):
            table = pa.Table.from_batches([batch])
            ids = table["diseaseId"].to_pylist()
            rows = [disease_lookup.get(str(x), {}) if x is not None else {} for x in ids]
            disease_missing += sum(not row for row in rows)
            table = table.append_column(
                "disease_name",
                pa.array([as_optional_string(row.get("name")) for row in rows], type=pa.string()),
            )
            table = table.append_column(
                "disease_description",
                pa.array([as_optional_string(row.get("description")) for row in rows], type=pa.string()),
            )
            table = table.append_column(
                "disease_code",
                pa.array([as_optional_string(row.get("code")) for row in rows], type=pa.string()),
            )
            table = table.append_column(
                "disease_exact_synonyms",
                pa.array(
                    [as_string_list(row.get("exactSynonyms")) for row in rows],
                    type=pa.list_(pa.string()),
                ),
            )
            table = table.append_column(
                "disease_therapeutic_areas",
                pa.array(
                    [as_string_list(row.get("therapeuticAreas")) for row in rows],
                    type=pa.list_(pa.string()),
                ),
            )
            if joined_writer is None:
                joined_writer = pq.ParquetWriter(final_tmp, schema_with_disease, compression="zstd")
            joined_writer.write_table(table, row_group_size=50_000)

        reader.close(force=True)
        if joined_writer:
            joined_writer.close()
        os.replace(final_tmp, OUTPUT_PARQUET)

        audit = {
            "project": "TrustDTI",
            "dataset": "Open Targets association_overall_direct",
            "release": RELEASE,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "bridge_rows": len(bridge),
            "input_shards": len(urls),
            "input_rows": total_in,
            "target_matched_rows_before_disease_join": total_target,
            "output_rows": total_out,
            "unique_target_ids_with_edges": len(matched_targets),
            "unique_disease_ids_in_edges": len(matched_diseases),
            "targets_without_edges": sorted(target_ids - matched_targets),
            "association_score_min": score_min,
            "association_score_max": score_max,
            "disease_metadata": disease_audit,
            "disease_metadata_unmatched_rows": disease_missing,
            "output_parquet": str(OUTPUT_PARQUET),
            "score_interpretation": (
                "Open Targets overall direct associationScore is a prioritisation score "
                "aggregating evidence across data sources. It is not a probability or causal proof."
            ),
            "shards": audit_shards,
        }
        OUTPUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        print(json.dumps(audit, indent=2))
        return audit

    except Exception:
        if writer is not None:
            writer.close()
        if partial_output.exists():
            partial_output.unlink()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run()
