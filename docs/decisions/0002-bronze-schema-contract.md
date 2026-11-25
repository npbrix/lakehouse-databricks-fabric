# 0002 – Bronze: explicit schema with rescued data

Status: Accepted

## Context
Sources change their files without warning. The price partner source system adds a currency column in
batch 2 and renames close_price to close_pricez in batch 3. Bronze must never lose data and
must not stop because a source changed.

## Decision
Each dataset has an explicit schema in its source system's file in config/sources/ (the contract).
Auto Loader runs with schemaEvolutionMode = none and a rescued data column. Columns that are
not in the contract, and values with the wrong type, are kept as JSON in _rescued_data.

## Alternatives considered
- Schema inference with addNewColumns: the table adapts on its own, but a typo such as
  close_pricez becomes a new column without anyone deciding it.
- failOnNewColumns: safe, but stops ingestion of all good data until someone acts.

## Consequences
New columns show up in _rescued_data and are added to the contract on purpose.
Handling this is shown in subsequent sessions.