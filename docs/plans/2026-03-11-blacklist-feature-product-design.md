# Blacklist Feature Product Design

**Date:** 2026-03-11

**Goal:** Reframe the current `step1~step4` default-history outputs into a model-oriented blacklist feature product built on one stable wide table, while keeping the existing `query_snapshot + event_fact` backbone.

## Scope

- Keep current historical event generation logic as the source of truth.
- Replace `step` as the product boundary with label families aligned to model features.
- Produce one primary wide feature table for model training and scoring.
- Reserve a secondary long-form detail layer for high-cardinality research dimensions, but keep it out of the first production contract.

## Confirmed Product Direction

- Primary consumer is model feature engineering.
- Main delivery should be a stable wide table, not multiple technical intermediate tables.
- Wide-table dimensions should be limited to stable low-cardinality categories.
- The stable first-wave dimensions are:
  - lifetime default history
  - rolling windows
  - institution type
  - performance type
- High-cardinality combinations such as `sample_flag` should not be expanded into the first wide-table contract.

## Problem Statement

The current codebase is already structurally correct at the lower level:

- [query_snapshot.py](D:/wise/acct_RZ/src/acct_rz/query_snapshot.py) defines who is being queried and as of which date.
- [events.py](D:/wise/acct_RZ/src/acct_rz/events.py) defines the shared default-event fact source.
- [features_blacklist.py](D:/wise/acct_RZ/src/acct_rz/features_blacklist.py), [features_org_blacklist.py](D:/wise/acct_RZ/src/acct_rz/features_org_blacklist.py), and [features_windows.py](D:/wise/acct_RZ/src/acct_rz/features_windows.py) already compute reusable pieces.

The mismatch is at the product layer:

- `step1~step4` are technical slices, not durable model feature families.
- `step1` and `step2` are two views over the same core aggregation.
- `step3` and `step4` encode dimension and window logic in a way that is not yet generalized for long-term expansion.

The redesign should therefore preserve the lower-level event and lookup model, while replacing the product contract.

## Product Outputs

### 1. Primary output: `blacklist_features`

One row per:

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

This is the production feature table used by model training and scoring.

### 2. Optional secondary output: `blacklist_feature_detail`

Long-form detail table for high-cardinality or exploratory dimensions such as:

- `sample_flag`
- future channel-level or institution-name-level breakdowns

This table is not part of the first model-facing contract.

## Feature Families

### 1. Lifetime history family

Purpose: describe whether the queried entity has ever defaulted and how long ago the default history begins or was last observed.

Recommended fields:

- `ever_default_flag`
- `first_default_dt`
- `latest_default_dt`
- `days_since_first_default`
- `days_since_latest_default`
- `default_cnt_lifetime`
- `default_month_cnt_lifetime`

Notes:

- `days_since_latest_default` is the highest-value recency feature.
- `days_since_first_default` is preferred over a loosely defined “farthest default distance”.
- `default_month_cnt_lifetime` reduces sensitivity to repeated events inside the same month.

### 2. Rolling-window intensity family

Purpose: describe recent default strength across multiple time horizons.

Windows:

- `3m`
- `6m`
- `9m`
- `12m`
- `24m`
- `36m`

Recommended fields for each window:

- `default_flag_{window}`
- `default_cnt_{window}`
- `default_month_cnt_{window}`
- `default_org_type_cnt_{window}`
- `default_perf_type_cnt_{window}`

Notes:

- Counts remain the core signal.
- Distinct-count fields capture multi-head and cross-type complexity without exploding dimensions.

### 3. Institution-type family

Purpose: describe historical and recent default activity by stable institution buckets.

Initial categories:

- `bank`
- `rate24`
- `rate36`

Recommended fields:

- `default_flag_{window}_{org_type}`
- `default_cnt_{window}_{org_type}`
- `days_since_latest_default_{org_type}`

Notes:

- Keep the category set configuration-driven rather than hard-coded to current demo values.
- This family should be built from a generalized dimensional breakdown path, not a dedicated `step3` concept.

### 4. Performance-type family

Purpose: distinguish default behavior by broad performance definition.

Initial categories:

- `fpd`
- `dpd`

Recommended fields:

- `default_flag_{window}_{perf_type}`
- `default_cnt_{window}_{perf_type}`
- `days_since_latest_default_{perf_type}`

Notes:

- This remains compact and stable enough for direct inclusion in the main wide table.
- Fine-grained combinations such as `mob3_dpd30` should stay out of the first wide-table contract.

### 5. Complexity family

Purpose: capture structure, not just volume.

Recommended fields:

- `is_multi_org_default_{window}`
- `is_multi_perf_default_{window}`
- `latest_default_org_type`
- `latest_default_perf_type`

Notes:

- These features often add value when raw counts saturate.
- They should be derived from the same breakdown aggregates instead of computed ad hoc.

## Architecture

The future feature product should use three layers.

### 1. Fact layer

Keep the current lower-level design intact:

- normalized application base
- shared default event fact
- shared query snapshot

This remains the only place where default semantics and event timing are interpreted.

### 2. Aggregation layer

Replace step-oriented calculations with reusable aggregation modules:

- `agg_lifetime.py`
- `agg_windows.py`
- `agg_breakdown.py`
- `agg_recency.py`

Responsibilities:

- lifetime summary metrics
- rolling-window metrics
- grouped metrics by a supplied dimension
- latest/first-date and day-distance derivations

These modules should operate on `query_snapshot + event_fact`, not raw `y.csv`.

### 3. Product assembly layer

Assemble feature families into final model-facing outputs:

- `labels_history.py`
- `labels_window.py`
- `labels_orgtype.py`
- `labels_perftype.py`
- `labels_complexity.py`
- `product_blacklist_features.py`

Responsibilities:

- define the exact output schema
- merge family tables by base key columns
- enforce naming conventions
- expose the final parquet-ready table

## Naming Rules

Use consistent model-facing names.

Base key columns:

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

Recommended suffix rules:

- flag fields end with `_flag`
- date fields end with `_dt`
- day-distance fields start with `days_since_`
- count fields use `_cnt_`
- windows use lowercase compact tokens such as `3m`, `6m`, `12m`
- dimensions use normalized lowercase names such as `bank`, `rate24`, `rate36`, `fpd`, `dpd`

## Handling `step1~step4`

Do not delete `step1~step4` immediately.

Recommended transition:

- keep existing step functions as compatibility wrappers
- internally reimplement them using the new aggregation layer
- stop using `step` names in product-level docs and feature contracts

Mapping:

- `step1 + step2` -> lifetime/history family
- `step3` -> grouped breakdown over `org_type`
- `step4` -> rolling-window metrics and partial breakdown metrics

This allows a smooth migration without breaking current CLI or tests too early.

## Error Handling

The feature product should keep current query behavior:

- unmatched keys still return a row
- count fields become `0`
- date fields become `null`

Additional product-level checks should include:

- duplicated output column detection during assembly
- unsupported configured dimension values should fail fast in assembly code
- wide-table joins must preserve row cardinality exactly

## Testing Strategy

The redesign should add tests at four levels.

1. Aggregation tests
- lifetime counts and dates
- rolling window boundaries
- grouped breakdown counts
- recency calculations

2. Label-family tests
- output schema for each family
- expected field naming
- zero/default behavior on unmatched keys

3. Product assembly tests
- one-row-per-query-key contract
- no duplicate columns
- stable merge behavior across families

4. Backward-compatibility tests
- existing `step1~step4` wrappers still behave as before during migration

## Non-Goals for V1

- scoring logic
- model training pipeline changes
- all possible fine-grained `sample_flag` expansion
- service/API deployment

## Recommended Delivery Order

1. Introduce reusable aggregation modules without removing existing steps.
2. Build lifetime and rolling-window label families first.
3. Add stable dimension families for `org_type` and `perf_type`.
4. Assemble the final `blacklist_features` wide table.
5. Convert `step1~step4` to compatibility wrappers over the new internals.
6. Optionally add a research-oriented long detail table for high-cardinality dimensions.
