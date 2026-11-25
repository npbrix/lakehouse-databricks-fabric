# Lakehouse on Databricks and Microsoft Fabric

A hands-on lakehouse for a fictional wealth management company, built on Databricks with
Unity Catalog and served to Power BI through Microsoft Fabric. Design choices are documented
as Architecture Decision Records in [`docs/decisions/`](docs/decisions/).

> **Status:** work in progress. See the [roadmap](#roadmap).

## Architecture

```
Source systems ──> Landing volumes ──> Bronze ──> Silver ──> Gold ──> Fabric / Power BI
                    (one per system)   (source    (business  (data
                                        lineage)   entities)  products)
```

- Lakeflow Spark Declarative Pipelines in Python, one pipeline per domain from bronze to gold
- Metadata-driven ingestion with Auto Loader: one YAML file per source system, no new code per source
- Kimball star schema in gold, consumed by a Direct Lake semantic model in Fabric
- Declarative Automation Bundles for deployment, with dev and prod targets
- Synthetic source data with deliberate data quality issues and schema drift
- Runs on Databricks Free Edition (serverless)

## Unity Catalog design

Two business domains (Data Mesh), each with its own catalog per environment.

| Layer | Catalog | Schema | Table | Example |
|---|---|---|---|---|
| Bronze (source lineage) | domain | `bronze_<source_system>` | source dataset | `dev_wealth.bronze_core_banking.customers` |
| Silver (business model) | domain | `silver` | business entity | `dev_wealth.silver.customer` |
| Gold (data products) | domain | `gold` | data product | `dev_market.gold.prices` |

| Domain | Catalogs | Source systems |
|---|---|---|
| Wealth | `dev_wealth`, `prod_wealth` | `core_banking`, `legacy_accounts` |
| Market | `dev_market`, `prod_market` | `investment_system`, `business_reference`, `price_partner` |

- **One catalog per domain and environment:** each domain owns its data and access rights, and dev and prod are separated.
- **Bronze is organised by source system:** one schema and landing volume per system, so you always see where data comes from and can grant access per source.
- **Silver and gold are organised by business meaning:** silver holds business entities, gold holds the domain's data products.
- **Only gold is shared across domains:** other teams read the market domain's gold layer, never bronze or silver.
- **Everything is code:** catalogs, schemas, volumes, tags and grants are created from [`config/unity_catalog.yml`](config/unity_catalog.yml).

## Getting started

```powershell
pip install -r requirements.txt
pip install -e .
python -m pytest
python scripts/setup_unity_catalog.py --env dev
python scripts/generate_data.py --batch 1 --upload
databricks bundle deploy
databricks bundle run wealth_pipeline
```

## Roadmap

- [x] Project setup: bundles, Databricks Connect, tests
- [x] Unity Catalog design as code
- [x] Synthetic source data
- [x] Bronze: metadata-driven ingestion with Auto Loader
- [ ] Unity Catalog and grants with Terraform  *(in progress)*
- [ ] CI/CD with bundles and promotion from dev to prod
- [ ] Ingestion patterns per source: CDC, watermark, snapshot diff, full load
- [ ] Silver: cleansing and data quality expectations
- [ ] Gold: Kimball, SCD2 and data products with data contracts
- [ ] Governance: classification tags, ABAC masking and lineage
- [ ] Cost control and reference architecture for workspaces and networking
- [ ] Microsoft Fabric: Direct Lake semantic model and Power BI report

## Decisions

| ADR | Decision |
|---|---|
| [0001](docs/decisions/0001-synthetic-data.md) | Synthetic data with deliberate errors |
| [0002](docs/decisions/0002-bronze-schema-contract.md) | Bronze: explicit schema with rescued data |
| [0003](docs/decisions/0003-unity-catalog-naming.md) | Source systems in bronze, business meaning in silver and gold |
