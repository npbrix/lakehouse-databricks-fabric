"""Write a Batch to local files in the formats the sources would deliver."""

import csv
import json
from pathlib import Path

from datagen.generator import Batch

def _write_jsonl(path: Path, rows: list[dict]) -> None:
    # JSON Lines: one JSON object per line, a common format for system extracts.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

def _write_csv(path: Path, rows: list[dict]) -> None:
    # CSV with a header; columns are taken from all rows so a new column is included.
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

def write_batch(batch: Batch, batch_no: int, root: Path) -> list[Path]:
    """Write one batch under root/<domain>/<source_system>/<dataset>/batch=NNN/.

    The folder structure mirrors Unity Catalog: each source system has its own landing volume
    (<env>_<domain>.bronze_<source_system>.landing), with one folder per dataset inside it.
    Returns the paths of the files written.
    """
    tag = f"batch={batch_no:03d}"
    wealth = root / "wealth"
    market = root / "market"
    files = {
        wealth / "core_banking" / "customers" / tag / "customers.json":
            (_write_jsonl, batch.customers),
        wealth / "core_banking" / "transactions" / tag / "transactions.json":
            (_write_jsonl, batch.transactions),
        wealth / "legacy_accounts" / "accounts" / tag / "accounts.csv":
            (_write_csv, batch.accounts),
        market / "investment_system" / "securities" / tag / "securities.json":
            (_write_jsonl, batch.securities),
        market / "business_reference" / "asset_class_mapping" / tag / "asset_class_mapping.csv":
            (_write_csv, batch.asset_class_mapping),
        market / "price_partner" / "prices" / tag / "prices.csv":
            (_write_csv, batch.prices),
    }
    written = []
    for path, (write, rows) in files.items():
        if rows:  # a dataset with nothing to deliver in this batch sends no file
            write(path, rows)
            written.append(path)
    return written
