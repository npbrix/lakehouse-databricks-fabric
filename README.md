# lakehouse-databricks-fabric
Lakehouse Databricks Fabric demonstration in a financial industry context.

## Roadmap

> Work in progress – built step by step as a hands-on learning project.

### Part 1 – Databricks lakehouse
- [x] Project setup: local development in VS Code, Databricks Asset Bundles, Git
- [x] Unity Catalog design as code: catalogs per domain and environment (Data Mesh), tags and grants
- [ ] Synthetic data generator: customers, accounts, transactions and market prices incl. changes and data quality issues
- [ ] Bronze: incremental, metadata-driven ingestion with Auto Loader (append-only)
- [ ] Silver: cleansing, deduplication, expectations, quarantine and Change Data Feed
- [ ] Gold: Kimball star schema with SCD2 dimensions (AUTO CDC) and point-in-time joins
- [ ] SCD2 with `MERGE` and `foreachBatch` as an alternative to declarative pipelines
- [ ] Performance tuning: query plans, joins, skew and liquid clustering
- [ ] Testing with pytest and Databricks Connect
- [ ] Orchestration and deployment to dev/prod with jobs and bundles
- [ ] Governance: column masks, row filters, lineage and audit
- [ ] CI/CD with GitHub Actions

### Part 2 – Microsoft Fabric
- [ ] Gold layer from Databricks into a Fabric Lakehouse
- [ ] Direct Lake semantic model with DAX measures and row-level security
- [ ] Power BI report under version control with Fabric Git integration