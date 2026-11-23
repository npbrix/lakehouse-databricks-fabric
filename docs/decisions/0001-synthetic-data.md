# 0001 – Synthetic, deterministic source data

## Context
The project needs realistic source data with changes and data quality issues, without using real customer data.

## Decision
A Python generator with a fixed seed writes batches in the formats each source would deliver (JSON Lines, CSV), including deliberate errors.

## Alternatives considered
Public sample datasets (no control over changes and errors); Faker (realistic values, but an extra dependency and less control).

## Consequences
Every scenario is reproducible and testable. The data is simpler than real data, so edge cases must be added deliberately.