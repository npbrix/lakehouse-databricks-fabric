from datagen.generator import generate_batch


def test_generation_is_deterministic() -> None:
    assert generate_batch(1) == generate_batch(1)


def test_batch_1_is_initial_load_without_deletes() -> None:
    batch = generate_batch(1)
    assert len(batch.customers) == 100
    assert not any(c["is_deleted"] for c in batch.customers)


def test_batch_2_contains_updates_deletes_and_new_customers() -> None:
    customers = generate_batch(2).customers
    assert any(c["is_deleted"] for c in customers)
    assert any(c["customer_id"] > 100 for c in customers)          # new customers
    assert any(c["customer_id"] <= 100 and not c["is_deleted"] for c in customers)  # updates


def test_transactions_contain_known_data_quality_issues() -> None:
    tx = generate_batch(2).transactions
    ids = [t["transaction_id"] for t in tx]
    assert len(ids) != len(set(ids))                                 # duplicates
    assert any(t["amount"] <= 0 for t in tx)                         # invalid amounts
    assert any("LATE" in t["transaction_id"] for t in tx)            # late-arriving rows


def test_prices_get_new_column_in_batch_2() -> None:
    assert "currency" not in generate_batch(1).prices[0]
    assert "currency" in generate_batch(2).prices[0]


def test_share_classes_point_to_an_existing_fund() -> None:
    securities = {s["security_id"]: s for s in generate_batch(1).securities}
    share_classes = [s for s in securities.values() if s["instrument_type"] == "SHARECLASS"]
    assert share_classes
    for sc in share_classes:
        parent = securities[sc["parent_security_id"]]
        assert parent["instrument_type"] in ("EQUITY_FUND", "BOND_FUND")


def test_fund_umbrellas_are_never_priced() -> None:
    priced = {p["security_id"] for p in generate_batch(1).prices}
    assert "FUND01" not in priced and "SEC006" in priced


def test_batch_2_reclassifies_a_security_and_launches_a_share_class() -> None:
    changes = {s["security_id"]: s for s in generate_batch(2).securities}
    assert changes["SEC005"]["instrument_type"] == "COVERED_BOND"
    assert changes["SEC009"]["parent_security_id"] == "FUND01"


def test_prices_column_is_renamed_in_batch_3() -> None:
    row = generate_batch(3).prices[0]
    assert "close_pricez" in row
    assert "close_price" not in row


def test_files_are_written_per_source_system(tmp_path) -> None:
    from datagen.writer import write_batch

    files = write_batch(generate_batch(1), 1, tmp_path)
    paths = {f.relative_to(tmp_path).as_posix() for f in files}
    assert "wealth/core_banking/customers/batch=001/customers.json" in paths
    assert "wealth/legacy_accounts/accounts/batch=001/accounts.csv" in paths
    assert "market/price_partner/prices/batch=001/prices.csv" in paths