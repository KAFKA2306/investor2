from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.types import IntegerType, LongType, StringType, StructField, StructType

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.projection_sources import load_projection_rows


CATALOG = "research"
TABLES = {
    "input_snapshots": "research.evidence.input_snapshots",
    "hypotheses": "research.evidence.hypotheses",
    "oos_results": "research.evidence.oos_results",
    "benchmark_contracts": "research.evidence.benchmark_contracts",
}

SCHEMAS = {
    "input_snapshots": StructType(
        [
            StructField("snapshot_id", StringType(), False),
            StructField("dataset_id", StringType(), False),
            StructField("reuse_key", StringType(), False),
            StructField("artifact_path", StringType(), False),
            StructField("artifact_sha256", StringType(), False),
            StructField("record_count", LongType(), False),
            StructField("schema_version", StringType(), False),
            StructField("source", StringType(), False),
            StructField("source_kind", StringType(), False),
            StructField("observed_at", StringType(), False),
            StructField("status", StringType(), False),
            StructField("provenance_json", StringType(), False),
        ]
    ),
    "hypotheses": StructType(
        [
            StructField("hypothesis_id", StringType(), False),
            StructField("schema_version", StringType(), False),
            StructField("thesis", StringType(), False),
            StructField("falsifier_count", IntegerType(), False),
            StructField("path", StringType(), False),
            StructField("artifact_sha256", StringType(), False),
            StructField("raw_json", StringType(), False),
        ]
    ),
    "oos_results": StructType(
        [
            StructField("result_id", StringType(), False),
            StructField("path", StringType(), False),
            StructField("fragment_index", IntegerType(), False),
            StructField("verdict", StringType(), False),
            StructField("research_question", StringType(), False),
            StructField("as_of", StringType(), False),
            StructField("artifact_sha256", StringType(), False),
            StructField("raw_json", StringType(), False),
        ]
    ),
    "benchmark_contracts": StructType(
        [
            StructField("benchmark_id", StringType(), False),
            StructField("schema_version", StringType(), False),
            StructField("source_dataset", StringType(), False),
            StructField("source_revision", StringType(), False),
            StructField("row_count", LongType(), True),
            StructField("path", StringType(), False),
            StructField("artifact_sha256", StringType(), False),
            StructField("raw_json", StringType(), False),
        ]
    ),
}

KEYS = {
    "input_snapshots": "snapshot_id",
    "hypotheses": "hypothesis_id",
    "oos_results": "result_id",
    "benchmark_contracts": "benchmark_id",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="/workspace")
    return parser.parse_args()


def write_and_verify(
    spark: SparkSession,
    name: str,
    rows: list[dict[str, object]],
) -> dict[str, object]:
    table = TABLES[name]
    schema = SCHEMAS[name]
    key = KEYS[name]

    frame = spark.createDataFrame(rows, schema=schema)
    frame.writeTo(table).using("iceberg").createOrReplace()

    persisted = spark.table(table)
    expected_count = len(rows)
    actual_count = persisted.count()
    if actual_count != expected_count:
        raise RuntimeError(
            f"{table} count mismatch: expected {expected_count}, got {actual_count}"
        )

    expected_keys = sorted(str(row[key]) for row in rows)
    actual_keys = sorted(
        str(row[key]) for row in persisted.select(key).orderBy(key).collect()
    )
    if actual_keys != expected_keys:
        raise RuntimeError(f"{table} key read-back mismatch")

    iceberg_snapshots = spark.sql(
        f"SELECT snapshot_id, operation FROM {table}.snapshots"
    ).collect()
    if not iceberg_snapshots:
        raise RuntimeError(f"{table} has no Iceberg snapshot metadata")

    return {
        "table": table,
        "rows": actual_count,
        "iceberg_snapshots": len(iceberg_snapshots),
    }


def main() -> None:
    args = parse_args()
    root = Path(args.root)

    subprocess.run(
        [sys.executable, str(root / "scripts/snapshot_store.py"), "audit"],
        cwd=root,
        check=True,
    )
    rows_by_table = load_projection_rows(root)

    spark = SparkSession.builder.appName("investor2-research-projection").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS research.evidence")

    results = {
        name: write_and_verify(spark, name, rows)
        for name, rows in rows_by_table.items()
    }

    rejected_oos = spark.sql(
        """
        SELECT COUNT(*) AS count
        FROM research.evidence.oos_results
        WHERE verdict IN ('REJECT', 'REJECTED', 'NOT_CONFIRMED', 'FAIL', 'FAILED')
        """
    ).first()["count"]

    summary = {
        "status": "RESEARCH_PROJECTION_OK",
        "tables": results,
        "rejected_oos_results": int(rejected_oos),
        "canonical_writeback": False,
    }
    print("RESEARCH_PROJECTION_OK " + json.dumps(summary, sort_keys=True))
    spark.stop()


if __name__ == "__main__":
    main()
