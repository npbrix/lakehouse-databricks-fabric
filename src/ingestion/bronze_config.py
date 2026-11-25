"""
Read and validate the bronze source configuration (config/sources/<domain>/<source_system>.yml).

The pipeline (src/pipelines/bronze.py) uses it to generate one bronze table per dataset.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

SUPPORTED_FORMATS = {"json", "csv"}
REQUIRED_KEYS = {"name", "description", "format", "schema"}
RESCUED_DATA_COLUMN = "_rescued_data"

# Reader options that each file format always needs.
FORMAT_DEFAULTS = {
    "json": {},
    "csv": {"header": "true"},  # the first line holds the column names
}


@dataclass
class SourceDataset:
    """One dataset (a table or file feed) from a source system = one bronze table."""

    source_system: str   # e.g. core_banking (the file name of the YAML file)
    name: str            # e.g. customers (also the landing folder and the table name)
    description: str
    format: str          # json or csv
    schema: str          # DDL string, e.g. "customer_id INT, name STRING"
    options: dict        # extra Auto Loader options from the YAML (often empty)
    bronze_schema: str   # e.g. bronze_core_banking

def load_datasets(sources_dir, domain: str) -> list[SourceDataset]:
    """
    Return all datasets in one domain, one YAML file per source system.

    The file name is the source system's name: core_banking.yml -> core_banking.
    """
    domain_dir = Path(sources_dir) / domain
    files = sorted(domain_dir.glob("*.yml"))
    if not files:
        raise ValueError(f"No source system files found in {domain_dir}")

    datasets = []
    for path in files:
        source_system = path.stem  # the file name without .yml
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        seen_names = []
        for entry in cfg["datasets"]:
            dataset = _to_dataset(source_system, entry)
            # Two datasets with the same name would write to the same bronze table.
            if dataset.name in seen_names:
                raise ValueError(f"Duplicate dataset name in {source_system}: {dataset.name}")
            seen_names.append(dataset.name)
            datasets.append(dataset)

    return datasets

def _to_dataset(source_system: str, entry: dict) -> SourceDataset:
    """Check one YAML entry and turn it into a SourceDataset."""

    name = entry.get("name", "?")

    missing = []
    for key in REQUIRED_KEYS:
        if key not in entry:
            missing.append(key)
    if missing:
        raise ValueError(f"{source_system}.{name} is missing keys: {missing}")

    if entry["format"] not in SUPPORTED_FORMATS:
        raise ValueError(f"{source_system}.{name}: format must be one of {SUPPORTED_FORMATS}")

    if entry["schema"].strip() == "":
        raise ValueError(f"{source_system}.{name}: schema must not be empty")

    # Spark reader options must be text. YAML reads values such as true or 100 as bool or int,
    # so every value is converted to a string.
    options = {}
    if entry.get("options"):  # skip when there are no options
        for key, value in entry["options"].items():
            options[key] = str(value)

    return SourceDataset(
        source_system=source_system,
        name=entry["name"],
        description=entry["description"],
        format=entry["format"],
        schema=entry["schema"],
        options=options,
        bronze_schema=f"bronze_{source_system}",
    )

def reader_options(dataset: SourceDataset) -> dict:
    """Auto Loader options for a dataset: shared defaults, then format defaults, then overrides."""
    options = {
        "cloudFiles.format": dataset.format,
        # Databricks pattern: explicit schema + rescued data column.
        # With an explicit schema, Auto Loader does not evolve the schema ("none").
        # Columns that are not in the schema, or values with the wrong type, are kept as JSON
        # in the rescued data column instead of being lost or failing the pipeline.
        # Auto Loader creates the rescue column and writes to it, we only decide the column name.
        "cloudFiles.schemaEvolutionMode": "none",
        "rescuedDataColumn": RESCUED_DATA_COLUMN,
    }
    options.update(FORMAT_DEFAULTS[dataset.format])
    options.update(dataset.options)  # a dataset can override any default in the YAML
    return options