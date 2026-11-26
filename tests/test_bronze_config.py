from pathlib import Path

import pytest

from ingestion.bronze_config import RESCUED_DATA_COLUMN, load_datasets, reader_options

SOURCES_DIR = Path(__file__).resolve().parent.parent / "config" / "sources"


def test_each_domain_has_its_datasets_per_source_system() -> None:
    wealth = [(d.source_system, d.name) for d in load_datasets(SOURCES_DIR, "wealth")]
    assert wealth == [("core_banking", "customers"), ("core_banking", "transactions"),
                      ("legacy_accounts", "accounts")]
    market = {d.name: d.source_system for d in load_datasets(SOURCES_DIR, "market")}
    assert market == {"asset_class_mapping": "business_reference",
                      "securities": "investment_system", "prices": "price_partner"}


def test_bronze_schema_comes_from_the_source_system() -> None:
    accounts = next(d for d in load_datasets(SOURCES_DIR, "wealth") if d.name == "accounts")
    assert accounts.bronze_schema == "bronze_legacy_accounts"


def test_unknown_domain_fails_clearly() -> None:
    with pytest.raises(ValueError, match="No source system files"):
        load_datasets(SOURCES_DIR, "crypto")


def test_csv_datasets_read_the_header() -> None:
    accounts = next(d for d in load_datasets(SOURCES_DIR, "wealth") if d.name == "accounts")
    opts = reader_options(accounts)
    assert opts["cloudFiles.format"] == "csv"
    assert opts["header"] == "true"


def test_unknown_columns_are_rescued_not_lost() -> None:
    for dataset in load_datasets(SOURCES_DIR, "market"):
        assert reader_options(dataset)["rescuedDataColumn"] == RESCUED_DATA_COLUMN


def test_duplicate_names_are_rejected(tmp_path: Path) -> None:
    entry = "{name: a, description: d, format: json, schema: 'id INT'}"
    (tmp_path / "wealth").mkdir()
    (tmp_path / "wealth" / "crm.yml").write_text(
        f"datasets:\n  - {entry}\n  - {entry}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        load_datasets(tmp_path, "wealth")


def test_missing_keys_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "wealth").mkdir()
    (tmp_path / "wealth" / "crm.yml").write_text(
        "datasets:\n  - {name: a, format: json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing keys"):
        load_datasets(tmp_path, "wealth")

def test_prices_contract_includes_currency() -> None:
    prices = next(d for d in load_datasets(SOURCES_DIR, "market") if d.name == "prices")
    assert "currency STRING" in prices.schema