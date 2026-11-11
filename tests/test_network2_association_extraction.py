from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from src.network.parquet_io import close_and_remove_shard


def test_cleanup_force_closes_parquet_reader_before_deleting(tmp_path):
    parquet_path = tmp_path / "small_test.parquet"
    pq.write_table(
        pa.table({"targetId": ["ENSG1", "ENSG2"]}),
        parquet_path,
    )

    reader = pq.ParquetFile(parquet_path)
    first_batch = next(reader.iter_batches(batch_size=1))
    assert first_batch.num_rows == 1
    assert not reader.closed

    removed = close_and_remove_shard(
        reader,
        parquet_path,
        should_remove=True,
    )

    assert reader.closed
    assert removed is True
    assert not parquet_path.exists()


def test_cleanup_can_close_reader_without_deleting_reused_file(tmp_path):
    parquet_path = tmp_path / "reused_test.parquet"
    pq.write_table(pa.table({"value": [1, 2, 3]}), parquet_path)

    reader = pq.ParquetFile(parquet_path)
    removed = close_and_remove_shard(
        reader,
        parquet_path,
        should_remove=False,
    )

    assert reader.closed
    assert removed is True
    assert parquet_path.exists()
