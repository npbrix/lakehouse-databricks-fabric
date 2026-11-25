"""Generate a batch of source data locally and optionally upload it to the landing volumes.

Usage:
    python scripts/generate_data.py --batch 1                 # write to ./data only
    python scripts/generate_data.py --batch 1 --upload        # also upload to Databricks (dev)
"""

import argparse
import logging
import subprocess
from pathlib import Path

from datagen.generator import generate_batch
from datagen.writer import write_batch

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"  # local output; ignored by Git

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("generate_data")


def upload(files: list[Path], env: str) -> None:
    """Upload only the files written for this batch to their source system's landing volume.

    Uploading file by file (instead of the whole data folder) means batches you have
    generated locally but do not want to deliver yet stay on your machine.
    """
    for f in files:
        # e.g. wealth/core_banking/customers/batch=001/customers.json
        rel = f.relative_to(DATA_DIR)
        domain = rel.parts[0]
        source_system = rel.parts[1]
        rest = Path(*rel.parts[2:])            # customers/batch=001/customers.json
        volume = f"/Volumes/{env}_{domain}/bronze_{source_system}/landing"
        folder = f"dbfs:{volume}/{rest.parent.as_posix()}"  # .../landing/customers/batch=001
        target = f"dbfs:{volume}/{rest.as_posix()}"
        log.info("Uploading %s -> %s", rel, target)
        # Copying a single file into a volume does not create missing folders, so create
        # them first. mkdir also creates parent folders and does nothing if they exist.
        subprocess.run(["databricks", "fs", "mkdir", folder], check=True)
        # --overwrite makes the upload safe to repeat (idempotent).
        subprocess.run(["databricks", "fs", "cp", "--overwrite", str(f), target], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic source data")
    parser.add_argument("--batch", type=int, required=True, help="1 = initial load, 2+ = changes")
    parser.add_argument("--env", choices=["dev", "prod"], default="dev")
    parser.add_argument("--upload", action="store_true", help="Upload to the landing volumes")
    args = parser.parse_args()

    batch = generate_batch(args.batch)
    files = write_batch(batch, args.batch, DATA_DIR)
    for f in files:
        log.info("Wrote %s", f.relative_to(ROOT))

    if args.upload:
        upload(files, args.env)


if __name__ == "__main__":
    main()
