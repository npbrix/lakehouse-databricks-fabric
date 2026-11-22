"""
Build the Unity Catalog setup as code: catalogs, schemas, volumes, tags and grants built from configuration yaml.

All functions are pure (no conncetion to Databricks), so they can be unit tested with pytest.
"""

def catalog_name(env: str, domain: str) -> str:
    """Return the catalog name for a given environment and domain: dev_wealth (per_domain strategy)."""
    # per_domain: each domain gets its own catalog, e.g. dev + wealth = dev_wealth
    return f"{env}_{domain}"

def schema_name(env: str, domain: str, layer: str) -> str:
    """Return the full schema name, e.g. dev_wealth.bronze"""
    # The catalog already tells domain and env, so the schema name it just the medallion layer.
    catalog = catalog_name(env, domain)
    return f"{catalog}.{layer}"

def build_statements(cfg: dict, env: str) -> list[str]:
    """Return the SQL statements in execution order. Every statement is idempotent (CREATE IF NOT EXISTS)."""
    # Collect the SQL statements.
    statements: list[str] = []

    # Loop over each domain under "domains:" in the YAML config file.
    # domain_cfg is the dict below each domain name, e.g. {"description": "..."}
    for domain, domain_cfg in cfg["domains"].items():
        catalog = catalog_name(env, domain)
        statements.append(
            f"CREATE CATALOG IF NOT EXISTS {catalog} COMMENT '{domain_cfg['description']}'"
        )
        
        # Tags make the catalog searchable and show its domain and environment in the UI.
        statements.append(
            f"ALTER CATALOG {catalog} SET TAGS ('domain' = '{domain}', 'environment' = '{env}')"
        )
        # Set the catalog owner if specified in the configuration.
        if domain_cfg.get("owner"):
            statements.append(
                f"ALTER CATALOG {catalog} OWNER TO {domain_cfg['owner']}"
            )

        # One schema per medallion layer, e.g. bronze, silver, gold.
        for layer in cfg["layers"]:
            schema = schema_name(env, domain, layer)
            statements.append(
                f"CREATE SCHEMA IF NOT EXISTS {schema} COMMENT '{layer} layer for {domain} domain in {env} environment'"
            )
            statements.append(
                f"ALTER SCHEMA {schema} SET TAGS ('domain' = '{domain}', 'environment' = '{env}', 'layer' = '{layer}')"
            )

        # A volume in bronze is the landing zone where raw data is uploaded before ingestion.
        # The volume is created in the bronze schema, e.g. dev_wealth.bronze.landing
        bronze = schema_name(env, domain, "bronze")
        statements.append(
            f"CREATE VOLUME IF NOT EXISTS {bronze}.landing COMMENT 'Raw files for ingestion'"
        )

    # Grants run after all catalogs and schemas exist so the referenced objects are always present.
    # Cross-domain access: grant a principal read access to one layer of another domain's catalog. This is useful for sharing data between domains.
    # if no grant is defines, the get() method returns and empty list, so the loop is skipped and not crashed.
    for grant in cfg.get("grants", []):
        catalog = catalog_name(env, grant["domain"])
        schema = schema_name(env, grant["domain"], grant["layer"])
        principal = grant["principal"]
        # Reading a table requires all three: USE CATALOG, USE SCHEMA, and SELECT on the table.
        statements.append(
            f"GRANT USE CATALOG on CATALOG {catalog} TO `{principal}`"
        )
        statements.append(
            f"GRANT USE SCHEMA, SELECT ON SCHEMA {schema} TO `{principal}`"
        )

    return statements