"""Generate realistic, deliberately dirty source data in batches

Batch 1 is the initial load.
Batch 2 contains changes:
- updated and deleted customers,
- new customers,
- duplicates,
- invalid values,
- late arriving transactions,
- schema change.

Each run produces the same data.

Keys work like in real source systems: each source has its own internal keys 
(customer_id, account_id, security_id), and the same keys appear across deliveries,
so the warehouse can connect customers, accounts, transactions, securities and prices.

"""

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

CITIES = ["Copenhagen", "Aarhus", "Odense", "Aalborg", "Esbjerg", "Malmo", "Hamburg"]
RISK_PROFILES = ["low", "medium", "high"]
ACCOUNT_TYPES = ["pension", "investment", "savings"]
TRANSACTION_TYPES = ["deposit", "withdrawal", "buy", "sell"]

BASE_DATE = date(2026, 1, 1)

# Security master as delivered by the investment system (fictional names and ISINs).

# Security master as delivered by the investment system (fictional names and ISINs).
#
# Investment hierarchy, top to bottom:
#
#   Asset class              house classification, from ASSET_CLASS_MAPPING (owned by the business)
#   └── Instrument type      vendor code on each security (LISTED_SHARE, GOV_BOND, EQUITY_FUND, ...)
#       └── Issuer           the company or state that issued the security
#           └── Security     one row per security_id (ISIN), traded and priced
#               └── Share class  funds only: a fund umbrella has one or more share classes

# The securities in this file placed in the hierarchy:
#
#   Equity
#   ├── LISTED_SHARE  SEC001 Nordic Pharma, SEC002 Baltic Shipping, SEC003 Green Energy
#   └── EQUITY_FUND   FUND01 Global Equity Fund (umbrella, Nordic Asset Management)
#                     ├── SEC006 A DKK Acc   (SHARECLASS)
#                     ├── SEC007 I EUR Dist  (SHARECLASS)
#                     └── SEC009 B DKK Dist  (SHARECLASS, launched in batch 2)

# A shareclass represnts a portfolio of stocks. 
# Different shareclasses can represent the same portfolio,
# but be distinct on the conditions investors are buying them: e.g. Currency DKK vs. EUR.
# Each shareclass has its own ISIN and NAV.
# This gives to levels:
# - customers own shareclasses (stocks and transactions),
# - the exposure and the asset classes is accumulated at fund level.

# A fund holds one portfolio of assets (shares, bonds, ...).
# A shareclass is a way to own units of that fund's portfolio.
# Shareclasses of the same fund share the portfolio, but differ in the
# terms investors buy on, e.g. currency (DKK vs EUR), dividend policy (Acc vs Dist)
# and investor type / fees (A retail vs I institutional).
# Each shareclass has its own ISIN and its own NAV (price).
# This gives two levels:
# - customers own share classes (holdings and transactions),
# - exposure and asset class are aggregated at fund level.




SECURITY_MASTER = [
    {"security_id": "SEC001", "isin": "DK0000000011", "name": "Nordic Pharma A/S",
     "instrument_type": "LISTED_SHARE", "issuer": "Nordic Pharma A/S", "parent_security_id": None,
     "currency": "DKK"},
    {"security_id": "SEC002", "isin": "DK0000000029", "name": "Baltic Shipping A/S",
     "instrument_type": "LISTED_SHARE", "issuer": "Baltic Shipping A/S", "parent_security_id": None,
     "currency": "DKK"},
    {"security_id": "SEC003", "isin": "DK0000000037", "name": "Green Energy A/S",
     "instrument_type": "LISTED_SHARE", "issuer": "Green Energy A/S", "parent_security_id": None,
     "currency": "DKK"},
    {"security_id": "SEC004", "isin": "DK0000000045", "name": "Danish Government Bond 2030",
     "instrument_type": "GOV_BOND", "issuer": "Kingdom of Denmark", "parent_security_id": None,
     "currency": "DKK"},
    {"security_id": "SEC005", "isin": "DK0000000052", "name": "Nordic Bank 3% 2028",
     "instrument_type": "CORP_BOND", "issuer": "Nordic Bank A/S", "parent_security_id": None,
     "currency": "DKK"},
    # Fund umbrellas: not traded or priced themselves; their share classes are.
    {"security_id": "FUND01", "isin": None, "name": "Global Equity Fund",
     "instrument_type": "EQUITY_FUND", "issuer": "Nordic Asset Management", "parent_security_id": None,
     "currency": None},
    {"security_id": "SEC006", "isin": "LU0000000016", "name": "Global Equity Fund - A DKK Acc",
     "instrument_type": "SHARECLASS", "issuer": "Nordic Asset Management",
     "parent_security_id": "FUND01", "currency": "DKK"},
    {"security_id": "SEC007", "isin": "LU0000000024", "name": "Global Equity Fund - I EUR Dist",
     "instrument_type": "SHARECLASS", "issuer": "Nordic Asset Management",
     "parent_security_id": "FUND01", "currency": "EUR"},
    {"security_id": "FUND02", "isin": None, "name": "Euro Bond Fund",
     "instrument_type": "BOND_FUND", "issuer": "Nordic Asset Management", "parent_security_id": None,
     "currency": None},
    {"security_id": "SEC008", "isin": "LU0000000032", "name": "Euro Bond Fund - A EUR Acc",
     "instrument_type": "SHARECLASS", "issuer": "Nordic Asset Management",
     "parent_security_id": "FUND02", "currency": "EUR"},
]

# Launched in batch 2: a new share class of an existing fund.
NEW_SHARE_CLASS = {"security_id": "SEC009", "isin": "LU0000000040",
                   "name": "Global Equity Fund - B DKK Dist", "instrument_type": "SHARECLASS",
                   "issuer": "Nordic Asset Management", "parent_security_id": "FUND01",
                   "currency": "DKK"}

# Mapping.
ASSET_CLASS_MAPPING = [
    {"instrument_type": "LISTED_SHARE", "asset_class": "Equity", "asset_sub_class": "Listed equity"},
    {"instrument_type": "GOV_BOND", "asset_class": "Fixed income", "asset_sub_class": "Government bonds"},
    {"instrument_type": "CORP_BOND", "asset_class": "Fixed income", "asset_sub_class": "Credit"},
    {"instrument_type": "COVERED_BOND", "asset_class": "Fixed income", "asset_sub_class": "Covered bonds"},
    {"instrument_type": "EQUITY_FUND", "asset_class": "Equity", "asset_sub_class": "Equity funds"},
    {"instrument_type": "BOND_FUND", "asset_class": "Fixed income", "asset_sub_class": "Bond funds"},
    {"instrument_type": "SHARECLASS", "asset_class": None, "asset_sub_class": None},
]

FUND_TYPES = {"EQUITY_FUND", "BOND_FUND"}
CURRENCY_BY_SECURITY = {s["security_id"]: s["currency"] for s in [*SECURITY_MASTER, NEW_SHARE_CLASS]}

@dataclass
class Batch:
    """All records generated for one batch, one list per source."""

    customers: list[dict]
    accounts: list[dict]
    transactions: list[dict]
    securities: list[dict]
    asset_class_mapping: list[dict]
    prices: list[dict]

def _timestamp(batch_no: int) -> datetime:
    # Each batch is "extracted" on its own day, so updated_at grows with the batch number.
    return datetime(2026, 1, 1, 6, 0) + timedelta(days=batch_no - 1)

def _customer(rng: random.Random, customer_id: int, batch_no: int) -> dict:
    return {
        "customer_id": customer_id,
        "name": f"Customer {customer_id}",
        "email": f"customer{customer_id}@example.com",
        "city": rng.choice(CITIES),
        "risk_profile": rng.choice(RISK_PROFILES),
        "is_deleted": False,
        "updated_at": _timestamp(batch_no).isoformat(),
    }

def _base_customers(seed: int, n_customers: int) -> list[dict]:
    # The base population is rebuilt from the seed, so batch 2 can change batch 1's customers.
    rng = random.Random(seed)
    return [_customer(rng, cid, 1) for cid in range(1, n_customers + 1)]


def _securities(batch_no: int) -> list[dict]:
    """Security master delivery: full list in batch 1, only changes from batch 2."""
    stamp = _timestamp(batch_no).isoformat()
    if batch_no == 1:
        return [{**s, "updated_at": stamp} for s in SECURITY_MASTER]
    if batch_no == 2:
        # Reclassification: the bond is now classified as a covered bond (-> SCD2 history later).
        reclassified = {**SECURITY_MASTER[4], "instrument_type": "COVERED_BOND", "updated_at": stamp}
        return [reclassified, {**NEW_SHARE_CLASS, "updated_at": stamp}]
    return []

def tradable_security_ids(batch_no: int) -> list[str]:
    """Securities that can be traded and priced: everything except the fund umbrellas."""
    ids = [s["security_id"] for s in SECURITY_MASTER if s["instrument_type"] not in FUND_TYPES]
    if batch_no >= 2:
        ids.append(NEW_SHARE_CLASS["security_id"])
    return ids


def generate_batch(batch_no: int, seed: int = 42, n_customers: int = 100) -> Batch:
    """Return the records for one batch. batch_no 1 = initial load, 2+ = incremental changes."""
    rng = random.Random(seed + batch_no)  # different but reproducible randomness per batch
    base = _base_customers(seed, n_customers)

    if batch_no == 1:
        customers = base
    else:
        customers = []
        # Pick distinct customers: 10 % are updated, 2 are deleted (never both in one batch).
        picked = rng.sample(base, k=n_customers // 10 + 2)
        to_update, to_delete = picked[:-2], picked[-2:]
        # Updated customers move city or change risk profile (becomes SCD2 history later).
        for c in to_update:
            changed = {**c, "updated_at": _timestamp(batch_no).isoformat()}
            changed["city"] = rng.choice([x for x in CITIES if x != c["city"]])
            changed["risk_profile"] = rng.choice(RISK_PROFILES)
            customers.append(changed)
        # A few customers are deleted in the source system (soft-delete flag in the extract).
        for c in to_delete:
            customers.append({**c, "is_deleted": True, "updated_at": _timestamp(batch_no).isoformat()})
        # New customers get ids after the existing ones.
        first_new = n_customers + (batch_no - 2) * 5 + 1
        customers += [_customer(rng, cid, batch_no) for cid in range(first_new, first_new + 5)]

    # One account per customer in this batch (new customers get new accounts).
    accounts = []
    for c in customers:
        if c["is_deleted"]:
            continue
        accounts.append(
            {
                "account_id": c["customer_id"] * 10,
                "customer_id": c["customer_id"],
                "account_type": rng.choice(ACCOUNT_TYPES),
                "opened_date": (BASE_DATE - timedelta(days=rng.randint(30, 3000))).isoformat(),
            }
        )
    # Data quality issue: an account without a customer (orphan / missing foreign key).
    accounts.append({"account_id": 999990, "customer_id": None, "account_type": "savings",
                     "opened_date": BASE_DATE.isoformat()})

    transactions = _transactions(rng, batch_no, [c["customer_id"] for c in base])
    # The mapping is reference data owned by the business: delivered once, in batch 1.
    mapping = ASSET_CLASS_MAPPING if batch_no == 1 else []
    prices = _prices(rng, batch_no)
    return Batch(customers, accounts, transactions, _securities(batch_no), mapping, prices)


def _transactions(rng: random.Random, batch_no: int, customer_ids: list[int]) -> list[dict]:
    day = BASE_DATE + timedelta(days=batch_no - 1)
    securities = tradable_security_ids(batch_no)
    rows = []
    for i in range(1, 301):
        cid = rng.choice(customer_ids)
        tx_type = rng.choice(TRANSACTION_TYPES)
        rows.append(
            {
                "transaction_id": f"T{batch_no:03d}-{i:05d}",
                "account_id": cid * 10,
                "transaction_type": tx_type,
                # Buys and sells reference the security master's key; cash movements have none.
                "security_id": rng.choice(securities) if tx_type in ("buy", "sell") else None,
                "amount": round(rng.uniform(100, 50_000), 2),
                "transaction_date": day.isoformat(),
            }
        )
    # Data quality issues: duplicates, invalid amounts and an unknown account.
    rows += [dict(r) for r in rng.sample(rows, k=5)]          # exact duplicates
    for r in rng.sample(rows, k=3):
        r["amount"] = rng.choice([0, -250.0])                   # invalid amounts
    rows.append({**rows[0], "transaction_id": f"T{batch_no:03d}-ORPHAN", "account_id": 123456789})
    if batch_no > 1:
        # Late-arriving data: transactions dated in the previous batch's day arrive now.
        late_day = (day - timedelta(days=1)).isoformat()
        rows += [{**r, "transaction_id": f"T{batch_no:03d}-LATE{j}", "transaction_date": late_day}
                 for j, r in enumerate(rng.sample(rows[:300], k=4))]
    return rows


def _prices(rng: random.Random, batch_no: int) -> list[dict]:
    day = BASE_DATE + timedelta(days=batch_no - 1)
    rows = []
    for security_id in tradable_security_ids(batch_no):
        row = {"security_id": security_id, "price_date": day.isoformat(),
               "close_price": round(rng.uniform(50, 2_000), 2)}
        if batch_no > 1:
            # Schema change: from batch 2 the partner adds the price currency as a new column.
            row["currency"] = CURRENCY_BY_SECURITY[security_id]
        if batch_no > 2:
            # Schema drift: from batch 3 the partner renames close_price to close_pricez (a typo).
            row["close_pricez"] = row.pop("close_price")
        rows.append(row)
    return rows