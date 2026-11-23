"""Write a Batch to local files in the formats the sources would deliver."""

import csv
import json
from pathlib import Path

from datagen.generator import Batch

def _write_jsonl(path: Path, rows: list[dict]) -> None:
    # Json lines: one json object per line - common format.
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
    """Write one batch under root/<domain>/<source>/batch=NNN/ and return the file paths."""
    tag = f"batch={batch_no:03d}"
    files = {
        root / "wealth" / "customers" / tag / "customers.json": (_write_jsonl, batch.customers),
        root / "wealth" / "accounts" / tag / "accounts.csv": (_write_csv, batch.accounts),
        root / "wealth" / "transactions" / tag / "transactions.json": (_write_jsonl, batch.transactions),
        root / "market" / "securities" / tag / "securities.json": (_write_jsonl, batch.securities),
        root / "market" / "asset_class_mapping" / tag / "asset_class_mapping.csv":
            (_write_csv, batch.asset_class_mapping),
        root / "market" / "prices" / tag / "prices.csv": (_write_csv, batch.prices),
    }
    written = []
    for path, (write, rows) in files.items():
        if rows:  # a source with nothing to deliver in this batch sends no file
            write(path, rows)
            written.append(path)
    return written