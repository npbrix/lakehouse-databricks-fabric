from lakehouse_setup.unity_catalog import schema_name, build_statements

CONFIG = {
    "layers": ["bronze", "silver", "gold"],
    "domains": {
        "wealth": {"description": "Customers"},
        "market": {"description": "Prices"},
    },
    "grants": [{"principal": "account users", "domain": "market", "layer": "gold"}],
}

def test_creates_one_catalog_per_domain_and_env() -> None:
    """Test that the build_statements function creates one catalog per domain and environment."""
    statements = build_statements(CONFIG, "dev")
    assert any("CREATE CATALOG IF NOT EXISTS dev_wealth" in s for s in statements)
    assert any("CREATE CATALOG IF NOT EXISTS dev_market" in s for s in statements)

def test_schema_name_is_catalog_plus_layer() -> None:
    """Test that the schema_name function returns the correct schema name."""
    assert schema_name("prod", "wealth", "gold") == "prod_wealth.gold"

def test_all_create_staetements_are_idempotent() -> None:
    """Test that all CREATE statements are idempotent (CREATE IF NOT EXISTS)."""
    statements = build_statements(CONFIG, "dev")
    creates = [s for s in statements if s.startswith("CREATE")]
    assert all("IF NOT EXISTS" in s for s in creates)

def test_grants_only_on_market_gold() -> None:
    """Test that the build_statements function creates grants only on market gold."""
    grants = [s for s in build_statements(CONFIG, "prod") if s.startswith("GRANT")]
    assert grants
    assert all("prod_market" in g for g in grants)
    assert not any("bronze" in s or "silver" in s for s in grants)

def test_owner_is_set_only_when_configured() -> None:
    assert not any ("OWNER TO" in s for s in build_statements(CONFIG, "dev"))
    cfg = {**CONFIG, "domains": {"wealth": {"description": "Customers", "owner": "data_engineers"}}}
    assert "ALTER CATALOG dev_wealth OWNER TO data_engineers" in build_statements(cfg, "dev")