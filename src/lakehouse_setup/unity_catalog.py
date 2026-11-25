"""Build the Unity Catalog SQL statements (catalogs, schemas, volumes, tags, grants) from config.

All functions are pure (no connection to Databricks), so they can be unit tested with pytest.

Structure:
    catalog = <env>_<domain>                    -> who owns the data (Data Mesh domain)
    bronze  = <catalog>.bronze_<source_system>  -> where the data comes from (source lineage)
    silver  = <catalog>.silver                  -> business entities
    gold    = <catalog>.gold                    -> data products
"""

# Silver and gold are organised by business meaning, so each domain has one schema per layer.
BUSINESS_LAYERS = ["silver", "gold"]


def catalog_name(env: str, domain: str) -> str:
    """Return the catalog for a domain and environment, e.g. dev_wealth."""
    # One catalog per domain and environment (Data Mesh): ownership and access follow the domain.
    return f"{env}_{domain}"


def schema_name(env: str, domain: str, layer: str) -> str:
    """Return a silver or gold schema, e.g. dev_wealth.silver."""
    return f"{catalog_name(env, domain)}.{layer}"


def bronze_schema_name(env: str, domain: str, source_system: str) -> str:
    """Return the bronze schema for one source system, e.g. dev_wealth.bronze_core_banking."""
    # Bronze is organised by source system, so the schema name shows where the data comes from.
    return f"{catalog_name(env, domain)}.bronze_{source_system}"


def build_statements(cfg: dict, env: str) -> list[str]:
    """Return the SQL statements in execution order. Every statement is idempotent."""
    statements: list[str] = []

    # domain_cfg is the dict below each domain name in the YAML file.
    for domain, domain_cfg in cfg["domains"].items():
        statements += _catalog_statements(env, domain, domain_cfg)
        statements += _bronze_statements(env, domain, domain_cfg["source_systems"])
        statements += _business_layer_statements(env, domain)

    # Cross-domain access: give a principal read access to one layer of another domain.
    for grant in cfg.get("grants", []):
        statements += _grant_statements(env, grant)

    return statements


def _catalog_statements(env: str, domain: str, domain_cfg: dict) -> list[str]:
    catalog = catalog_name(env, domain)
    statements = [
        # IF NOT EXISTS makes the statement safe to run again (idempotent).
        f"CREATE CATALOG IF NOT EXISTS {catalog} COMMENT '{domain_cfg['description']}'",
        # Tags make the catalog searchable and show its domain and environment in the UI.
        f"ALTER CATALOG {catalog} SET TAGS ('domain' = '{domain}', 'env' = '{env}')",
    ]
    # Optional owner: hand the catalog over to the domain's team group.
    if domain_cfg.get("owner"):
        statements.append(f"ALTER CATALOG {catalog} OWNER TO `{domain_cfg['owner']}`")
    return statements


def _bronze_statements(env: str, domain: str, source_systems: dict) -> list[str]:
    """One bronze schema per source system, each with its own landing volume."""
    statements = []
    for source_system, description in source_systems.items():
        schema = bronze_schema_name(env, domain, source_system)
        statements.append(f"CREATE SCHEMA IF NOT EXISTS {schema} COMMENT '{description}'")
        statements.append(
            f"ALTER SCHEMA {schema} SET TAGS ('domain' = '{domain}', 'env' = '{env}', "
            f"'layer' = 'bronze', 'source_system' = '{source_system}')"
        )
        # The landing volume is where this system's raw files are uploaded before ingestion.
        statements.append(
            f"CREATE VOLUME IF NOT EXISTS {schema}.landing "
            f"COMMENT 'Raw files from {source_system}'"
        )
    return statements


def _business_layer_statements(env: str, domain: str) -> list[str]:
    """One silver and one gold schema per domain."""
    statements = []
    for layer in BUSINESS_LAYERS:
        schema = schema_name(env, domain, layer)
        statements.append(
            f"CREATE SCHEMA IF NOT EXISTS {schema} COMMENT '{layer} layer for {domain}'"
        )
        statements.append(
            f"ALTER SCHEMA {schema} SET TAGS "
            f"('domain' = '{domain}', 'env' = '{env}', 'layer' = '{layer}')"
        )
    return statements


def _grant_statements(env: str, grant: dict) -> list[str]:
    catalog = catalog_name(env, grant["domain"])
    schema = schema_name(env, grant["domain"], grant["layer"])
    principal = grant["principal"]
    # Reading a table requires all three: USE CATALOG, USE SCHEMA and SELECT.
    return [
        f"GRANT USE CATALOG ON CATALOG {catalog} TO `{principal}`",
        f"GRANT USE SCHEMA, SELECT ON SCHEMA {schema} TO `{principal}`",
    ]