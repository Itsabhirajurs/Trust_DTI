
"""
TrustDTI Week 09:
Prepare validated Network 2 target IDs and inspect
Open Targets direct-association and disease downloads.

No full association dataset is downloaded in this step.
"""

from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

RELEASE = "26.09"

OUTPUT_DIR = ROOT / "outputs" / "week09_network2"

BASE_URL = (
    f"https://ftp.ebi.ac.uk/pub/databases/"
    f"opentargets/platform/{RELEASE}/output/"
)

DATASETS = [
    "association_by_datasource_direct",
    "disease",
    "evidence",
]

BRIDGE_PATH = (
    OUTPUT_DIR / "uniprot_opentargets_target_bridge.csv"
)

SUMMARY_PATH = (
    OUTPUT_DIR / "uniprot_opentargets_accession_summary.csv"
)


# ============================================================
# 2. HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "TrustDTI-Research/1.0"
})


# ============================================================
# 3. DIRECTORY PARSER
# ============================================================

class DirectoryParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):

        if tag.lower() != "a":
            return

        href = dict(attrs).get("href")

        if href:
            self.links.append(href)


# ============================================================
# 4. BUILD HIGH-CONFIDENCE TARGET BRIDGE
# ============================================================

def prepare_target_bridge():

    print("\n" + "=" * 65)
    print("PREPARING HIGH-CONFIDENCE TARGET BRIDGE")
    print("=" * 65)

    bridge = pd.read_csv(
        BRIDGE_PATH,
        dtype={
            "uniprot_accession": "string",
            "ensembl_gene_id": "string",
            "approved_gene_symbol": "string",
            "target_biotype": "string",
        },
    )

    summary = pd.read_csv(
        SUMMARY_PATH,
        dtype="string",
    )

    for column in [
        "target_present",
        "uniprot_direct_match",
    ]:
        bridge[column] = (
            bridge[column]
            .astype("string")
            .str.lower()
            .eq("true")
        )

    bridge["uniprot_accession"] = (
        bridge["uniprot_accession"]
        .str.strip()
        .str.upper()
    )

    bridge["ensembl_gene_id"] = (
        bridge["ensembl_gene_id"]
        .str.strip()
    )

    # Only candidates that are present in Open Targets and
    # have a direct UniProt protein cross-reference.
    matched = bridge.loc[
        bridge["target_present"]
        & bridge["uniprot_direct_match"]
    ].copy()

    # Count distinct directly matched Ensembl IDs per protein.
    direct_counts = (
        matched.groupby("uniprot_accession")
        ["ensembl_gene_id"]
        .nunique()
    )

    matched["direct_match_count"] = (
        matched["uniprot_accession"]
        .map(direct_counts)
    )

    # Preserve one mapping only when exactly one candidate
    # has a direct UniProt cross-reference.
    primary = matched.loc[
        matched["direct_match_count"].eq(1)
    ].copy()

    primary = primary.drop_duplicates(
        subset=["uniprot_accession"],
        keep="first",
    )

    primary["mapping_confidence"] = (
        "UNIQUE_DIRECT_UNIPROT_XREF"
    )

    primary["opentargets_release"] = RELEASE

    review = summary.copy()

    review["direct_uniprot_xref_candidate_count"] = (
        pd.to_numeric(
            review["direct_uniprot_xref_candidate_count"],
            errors="coerce",
        ).fillna(0).astype(int)
    )

    review = review.loc[
        review["direct_uniprot_xref_candidate_count"].ne(1)
    ].copy()

    primary_path = (
        OUTPUT_DIR / "uniprot_opentargets_primary_bridge.csv"
    )

    review_path = (
        OUTPUT_DIR / "uniprot_opentargets_mapping_review.csv"
    )

    primary.to_csv(
        primary_path,
        index=False,
    )

    review.to_csv(
        review_path,
        index=False,
    )

    print("Total Network 1 proteins:", len(summary))

    print("High-confidence unique target mappings:", len(primary))

    print("Proteins requiring review:", len(review))

    print(
        "Non-protein-coding target rows:",
        int(
            primary["target_biotype"]
            .ne("protein_coding")
            .sum()
        ),
    )

    print(
        "\nHigh-confidence target biotypes:"
    )

    print(
        primary["target_biotype"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nSaved:")
    print(primary_path)
    print(review_path)

    if len(primary) != 2295:
        raise ValueError(
            f"Expected 2295 unique targets; found {len(primary)}. "
            "Review mapping data before continuing."
        )

    return primary


# ============================================================
# 5. INSPECT REMOTE DATASET DIRECTORIES
# ============================================================

def inspect_dataset(dataset_name):

    print("\n" + "=" * 65)
    print("DATASET:", dataset_name)
    print("=" * 65)

    url = BASE_URL + dataset_name + "/"

    response = session.get(
        url,
        timeout=60,
    )

    print("HTTP status:", response.status_code)

    if response.status_code != 200:

        print(
            "Dataset directory could not be accessed:",
            response.text[:500],
        )

        return

    parser = DirectoryParser()
    parser.feed(response.text)

    parquet_urls = []
    source_partitions = []

    for link in parser.links:

        absolute_url = urljoin(url, link)

        path = urlparse(absolute_url).path

        if path.lower().endswith(".parquet"):

            parquet_urls.append(absolute_url)

        elif "sourceId=" in path:

            source_partitions.append(
                path.rstrip("/").split("/")[-1]
            )

    print("Parquet files discovered:", len(parquet_urls))

    if source_partitions:

        print(
            "Evidence source partitions discovered:",
            len(source_partitions),
        )

        print(
            "First 20 partitions:",
            source_partitions[:20],
        )

    total_size = 0
    known_sizes = 0

    # HEAD requests inspect file sizes without downloading
    # the actual Parquet contents.
    for index, file_url in enumerate(
        parquet_urls,
        start=1,
    ):

        filename = urlparse(file_url).path.rsplit("/", 1)[-1]

        try:

            head = session.head(
                file_url,
                timeout=30,
            )

            size = head.headers.get("Content-Length")

            if size:

                size = int(size)

                total_size += size
                known_sizes += 1

                print(
                    f"{index}. {filename}: "
                    f"{size / (1024 * 1024):.2f} MB"
                )

        except requests.RequestException as error:

            print(
                "Could not inspect size:",
                filename,
                str(error),
            )

    if known_sizes:

        print(
            "\nEstimated total Parquet size:",
            round(total_size / (1024 * 1024), 2),
            "MB",
        )

    if dataset_name == "evidence":

        print(
            "\nEvidence is partitioned by sourceId. "
            "We will selectively acquire relevant source partitions "
            "rather than blindly download the entire evidence corpus."
        )


# ============================================================
# 6. MAIN
# ============================================================

def main():

    primary = prepare_target_bridge()

    print("\n" + "=" * 65)
    print("INSPECTING NETWORK 2 DATA SOURCES")
    print("=" * 65)

    for dataset in DATASETS:

        inspect_dataset(dataset)

    print("\n" + "=" * 65)
    print("PREPARATION COMPLETED")
    print("=" * 65)

    print(
        "Targets ready for association filtering:",
        len(primary),
    )

    print(
        "Next dataset:",
        "association_by_datasource_direct",
    )


if __name__ == "__main__":
    main()
