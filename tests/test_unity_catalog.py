from lakehouse_setup.unity_catalog import bronze_schema_name, build_statements, schema_name

CONFIG = {
    "domains": {
        "wealth": {
            "description": "Customers",
            "source_systems": {"core_banking": "Core banking", "legacy_accounts": "Accounts"},
        },
        "market": {
            "description": "Prices",
            "source_systems": {"price_partner": "Prices"},
        },
    },
    "grants": [{"principal": "account users", "domain": "market", "layer": "gold"}],
}


def test_creates_one_catalog_per_domain_and_env() -> None:
    statements = build_statements(CONFIG, "dev")
    assert any("CREATE CATALOG IF NOT EXISTS dev_wealth" in s for s in statements)
    assert any("CREATE CATALOG IF NOT EXISTS dev_market" in s for s in statements)


def test_bronze_has_one_schema_and_landing_volume_per_source_system() -> None:
    statements = build_statements(CONFIG, "dev")
    for system in ("core_banking", "legacy_accounts"):
        schema = f"dev_wealth.bronze_{system}"
        assert any(f"CREATE SCHEMA IF NOT EXISTS {schema} " in s for s in statements)
        assert any(f"CREATE VOLUME IF NOT EXISTS {schema}.landing" in s for s in statements)


def test_silver_and_gold_are_one_schema_per_domain() -> None:
    statements = build_statements(CONFIG, "dev")
    assert any("CREATE SCHEMA IF NOT EXISTS dev_wealth.silver " in s for s in statements)
    assert any("CREATE SCHEMA IF NOT EXISTS dev_wealth.gold " in s for s in statements)
    assert not any("dev_wealth.bronze " in s for s in statements)  # no plain bronze schema


def test_schema_names() -> None:
    assert schema_name("prod", "wealth", "gold") == "prod_wealth.gold"
    assert bronze_schema_name("prod", "wealth", "core_banking") == "prod_wealth.bronze_core_banking"


def test_all_create_statements_are_idempotent() -> None:
    creates = [s for s in build_statements(CONFIG, "dev") if s.startswith("CREATE")]
    assert all("IF NOT EXISTS" in s for s in creates)


def test_grants_only_on_market_gold() -> None:
    grants = [s for s in build_statements(CONFIG, "prod") if s.startswith("GRANT")]
    assert grants
    assert all("prod_market" in s for s in grants)
    assert not any("bronze" in s or "silver" in s for s in grants)


def test_owner_is_set_only_when_configured() -> None:
    assert not any("OWNER TO" in s for s in build_statements(CONFIG, "dev"))
    wealth = {**CONFIG["domains"]["wealth"], "owner": "wealth_team"}
    cfg = {**CONFIG, "domains": {"wealth": wealth}}
    assert "ALTER CATALOG dev_wealth OWNER TO `wealth_team`" in build_statements(cfg, "dev")

