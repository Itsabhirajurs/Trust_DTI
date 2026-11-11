"""Small, testable helpers for safe Parquet file lifecycle management."""

import gc
from pathlib import Path


def close_and_remove_shard(
    parquet_file,
    local_path: Path,
    should_remove: bool,
) -> bool:
    """Close a PyArrow ParquetFile before optional local-file deletion.

    PyArrow's ParquetFile.close(force=True) explicitly closes the underlying
    reader. This matters on Windows, where an open file handle prevents unlink.

    Returns False if the reader could not be closed or Windows still prevents
    deletion. In that case the downloaded file is kept for a later retry.
    """
    try:
        parquet_file.close(force=True)
    except Exception as error:
        print(f"WARNING: Could not force-close Parquet reader: {error}")
        return False

    gc.collect()

    if not should_remove or not local_path.exists():
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
