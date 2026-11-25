"""
Bronze layer: one append-only streaming table per source dataset, generated from configuration.

A source dataset is one table or file feed from a source system, e.g. "customers" from the
core banking system. Each source system has its own bronze schema and landing volume:

    config/sources/wealth/core_banking.yml                          (configuration in the repo)
    /Volumes/dev_wealth/bronze_core_banking/landing/customers/      (files)
    dev_wealth.bronze_core_banking.customers                        (bronze table)

The pipeline settings (resources/pipelines.yml) tell this file which environment and domain it
runs for. The code loops over the configured datasets and registers one table per dataset,
so a new dataset or source system only needs new configuration, not new code.
"""

import sys

from pyspark import pipelines as dp
from pyspark.sql import SparkSession, functions as F

# Provide the active Spark session for pipeline configuration access.
spark = SparkSession.builder.getOrCreate()

# Values from the pipeline's ressources/pipelines.yml. spark is provided by the pipeline runtime.
ENV = spark.conf.get("lakehouse.env")                 # dev or prod
DOMAIN = spark.conf.get("lakehouse.domain")           # wealth or market
SRC_PATH = spark.conf.get("lakehouse.src_path")       # synced src/ folder in the workspace
SOURCES_DIR = spark.conf.get("lakehouse.sources_dir")  # synced config/sources/ folder

# Make our own package (src/ingestion) importable inside the pipeline.
sys.path.append(SRC_PATH)
from ingestion.bronze_config import load_datasets, reader_options

CATALOG = f"{ENV}_{DOMAIN}"


def define_bronze_table(dataset) -> None:
    """Register one bronze streaming table for a dataset.

    Databricks pattern: "create tables in a for loop" (metaprogramming). The table is defined
    inside this function, not directly in the loop, so each table keeps its own `dataset`.
    Pipeline functions run lazily: with a plain loop every table would read the last dataset.
    Databricks Labs' sdp-meta (formerly dlt-meta) framework is built on the same idea.

    Typical interview topic for metadata-driven ingestion: "How do you onboard 100 sources
    without writing 100 pipeline files?" Answer: configuration + one generic function like this.
    """
    # The table goes to the source system's bronze schema, e.g. bronze_core_banking.customers.
    table_name = f"{dataset.bronze_schema}.{dataset.name}"
    landing_path = f"/Volumes/{CATALOG}/{dataset.bronze_schema}/landing/{dataset.name}"

    @dp.table(
        name=table_name,
        comment=dataset.description,
        table_properties={
            "lakehouse.layer": "bronze",
            "lakehouse.source_system": dataset.source_system,
            "lakehouse.source_format": dataset.format,
        },
    )
    def bronze_table():
        return (
            # Databricks pattern: Auto Loader (format "cloudFiles") is the recommended way to ingest files incrementally.
            # The pipeline keeps a checkpoint of the files already read, so each run only reads new files.
            # Append-only: a streaming table only adds rows (via spark.readStream)
            # Updates and deletes from the source arrive as new rows (e.g. is_deleted = true) and are resolved in silver (CDC / SCD2).
            # Bronze is the raw history, so it can always be rebuilt from the landing files.
            spark.readStream.format("cloudFiles")
            .options(**reader_options(dataset))
            .schema(dataset.schema) # explicit contract, no guessing
            .load(landing_path)
            .select(
                "*", # keeps all existing source columns.
                # Addint data lineage columns: where and when each row came from (indicate by prefix "_*")
                # Databricks pattern: the hidden _metadata column replaces input_file_name(),
                # which does not work in Unity Catalog.
                F.lit(dataset.source_system).alias("_source_system"), # Creates a column "_source_system" where every row gets the same constant value.
                F.col("_metadata.file_path").alias("_source_file"), # _metadata is DB/Spark system column that is automatically attached to every row when reading files.
                F.col("_metadata.file_modification_time").alias("_file_modified_at"),
                F.regexp_extract("_metadata.file_path", r"batch=(\d+)", 1)
                .cast("int")
                .alias("_batch"), # extracts the batch id
                F.current_timestamp().alias("_ingested_at"),
            )
        )


for ds in load_datasets(SOURCES_DIR, DOMAIN):
    define_bronze_table(ds)