# 0003 – Unity Catalog naming: source systems in bronze, business meaning in silver and gold

Status: Accepted

## Context
Each domain (Data Mesh) receives data from several source systems. In bronze we must see
where data comes from. In silver and gold we must see business meaning. Two systems can
deliver datasets with the same name, e.g. customers from both a core system and a CRM.

## Decision
- Catalog = <env>_<domain>, e.g. dev_wealth. The domain owns its data.
- Bronze = one schema per source system, bronze_<source_system>, with its own landing
  volume. Table = the source's dataset name: dev_wealth.bronze_core_banking.customers.
- Silver = one schema per domain. Tables are named after business entities.
- Gold = one schema per domain. Tables are the domain's data products, with owner,
  description, SLA and classification as Unity Catalog metadata.
- The source system name is the same everywhere: config file
  (config/sources/<domain>/<source_system>.yml), landing folder, bronze schema,
  the schema tag source_system and the _source_system column.

## Alternatives considered
- Source system in the table name (bronze.core_banking__customers, the dbt convention):
  fewer schemas, but no access control per source system and longer table names.
- One central catalog for all bronze data (hub model): fits a central data team,
  not domains that own their data from source to data product.

## Consequences
- More schemas, one per source system, all created from config by setup_unity_catalog.py.
- Access can be granted per source system at schema level.
- Silver is where data from several systems is integrated into one business entity.