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

## Unity Catalog design

- **One catalog per domain and environment** (`dev_wealth`, `prod_market`, ...): each domain owns its data and access rights (Data Mesh), and dev and prod are fully separated.
- **Bronze is organised by source system:** one schema per system (`bronze_core_banking`, `bronze_price_partner`, ...), each with its own `landing` volume, so you can always see where data comes from and grant access per source.
- **Silver and gold are organised by business meaning:** one `silver` and one `gold` schema per domain. Silver holds business entities, gold holds the domain's data products.
- **Only gold is shared across domains:** other teams get `SELECT` on the market domain's gold layer, never on bronze or silver, so consumers depend on curated, stable data products.
- **Everything is code:** `config/unity_catalog.yml` describes the design and `scripts/setup_unity_catalog.py` applies it idempotently, so the setup can be reviewed, repeated and recreated.
- **Adding a domain or a source system** means a few lines in the YAML file and a re-run of the script, with no code changes.

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
- [x] Schema evolution: from rescued data to a governed column
- [ ] Unity Catalog, access model and grants with Terraform   *(in progress)*
- [ ] CI/CD: dev → test → prod with bundles, Terraform and approvals
- [ ] Ingestion patterns per source: Oracle CDC, watermark, snapshot diff, full load
- [ ] Ingestion operations: data quality framework, quarantine, replay, SLAs and cut-over
- [ ] Silver: cleansing and data quality rules from configuration
- [ ] Gold: Kimball, SCD2 and data products with data contracts and output ports
- [ ] Governance: classification tags, ABAC masking and lineage
- [ ] Cost control and reference architecture for workspaces and networking
- [ ] Microsoft Fabric: Direct Lake semantic model and Power BI report
- [ ] AI output port: gold data products as MCP tools for Claude
- [ ] Optional, on Azure: one workspace per environment, Data Factory, MCP on Container Apps

## Decisions

| ADR | Decision |
|---|---|
| [0001](docs/decisions/0001-synthetic-data.md) | Synthetic data with deliberate errors |
| [0002](docs/decisions/0002-bronze-schema-contract.md) | Bronze: explicit schema with rescued data |
| [0003](docs/decisions/0003-unity-catalog-naming.md) | Source systems in bronze, business meaning in silver and gold |
