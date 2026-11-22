"""Create or update the Unity Catalog setup as code: catalogs, schemas, volumes, tags and grants built from configuration yaml.

Usage: python scripts/setup_unity_catalog.py --env dev --dry-run # print the SQL without running it
       python scripts/setup_unity_catalog.py --env dev # run the SQL statements in Databricks.

"""

import argparse
import logging
from pathlib import Path
import yaml
from lakehouse_setup.unity_catalog import build_statements

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "unity_catalog.yml"

# Log every step with its level to the console, e.g. "INFO CREATE CATALOG ..."
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("setup_unity_catalog")

def main() -> None:
    """Parse command line arguments and run the setup."""
    parser = argparse.ArgumentParser(description="Setup Unity Catalog from configuration yaml.")
    parser.add_argument("--env", choices=["dev", "prod"], default="dev")
    parser.add_argument("--dry-run", action="store_true", help="Print the SQL statements without running them.")
    args = parser.parse_args()

    # Load the configuration yaml file, i.e. read the yaml file and parse it into a Python dict.
    with CONFIG_PATH.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Turn the config into SQL statements
    statements = build_statements(cfg, args.env)

    if args.dry_run:
        # Print the SQL statements to the console.
        for s in statements:
            print(s)
        return
    # Imported here to avoid requiring Databricks Connect for dry-run mode.
    from databricks.connect import DatabricksSession

    # Connect to Databricks and run the SQL statements.
    spark = DatabricksSession.builder.serverless().getOrCreate()
    for s in statements:
        log.info(s)
        spark.sql(s)
    log.info("Done: %d statements executed for environment %s.", len(statements), args.env)

if __name__ == "__main__":
    main()