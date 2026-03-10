# Ydata Query Lookup Design

**Date:** 2026-03-10

**Goal:** Extend the current offline default-history feature pipeline so that any externally supplied key and application date can be queried for `step1-step4` results, without requiring that the queried `app_dt` already exists in `y.csv`.

## Scope

- Add a query-oriented feature lookup path for arbitrary `PID`, `ID`, or `PID+ID` plus `app_dt`.
- Keep `y.csv` as the historical default-event source only.
- Unify offline batch output and query lookup under the same event-matching logic.
- Adjust existing outputs so they expose split key columns (`PID`, `ID`) in addition to `key_type` and `key_value`.

## Problem Statement

The current implementation uses historical application rows from `y.csv` as both:

- the event source, and
- the query snapshot set.

That means the system only returns features for application dates already present in `y.csv`. For a fixed key, if a requested `app_dt` never appeared in the historical application table, no result can be produced even though the default history is fully defined by past effective default events.

The new requirement changes this boundary:

- `y.csv` remains the only historical default-label source.
- Query keys and query dates come entirely from external input.
- For any key and any `app_dt`, the system should return the same `step1-step4` metrics that would have applied on that date.

## Confirmed Business Rules

- Only `target == 1` creates a default event.
- All other current or future values such as `0`, `-2`, `0.5`, `-1` are treated as non-default for event generation.
- Effective default date is `event_dt = app_dt + mob_filled(months)`.
- Missing `mob` is filled with `6`.
- Blacklist hits and rolling windows are evaluated against `event_dt`, not raw historical application date.
- If a queried key never appears in historical data, or has no effective default event before the queried `app_dt`, the system still returns a row for the query:
  - count and hit fields are `0`
  - date fields are `null`
- `step3` returns long-form results by default.

## Architecture

The revised design separates event generation from query snapshot generation.

### 1. Historical normalization layer

Keep `build_application_base()` as the single rule owner for:

- parsing `app_dt`
- filling `mob`
- deriving `is_default`
- deriving `event_dt`

This remains the one place where label and time semantics are defined.

### 2. Historical default event fact layer

Keep a normalized default-event fact table, but make sure it can preserve split key columns:

- `key_type`
- `key_value`
- `PID`
- `ID`
- `event_dt`
- `Org_class_new`
- `Org_new`
- `perf_type`
- `threshold_dpd`
- `channel_new`

This table remains the shared event source for both offline batch and query lookup.

### 3. Query snapshot layer

Introduce a new concept: `query_key_snapshot`.

It represents the exact keys and dates to be evaluated, with two sources:

- `history_query_snapshot`
  - built from historical application rows
  - used for the existing offline batch pipeline
- `external_query_snapshot`
  - built from user-supplied `pl.DataFrame`
  - used for arbitrary key/date lookup

Both sources must converge to the same internal schema:

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

### 4. Shared lookup layer

Refactor `step1-step4` generation into lookup-style functions that accept:

- a query snapshot
- a default event fact table

This makes offline and query flows identical except for how the query snapshot is built.

## Query Input Contract

External query input should support these columns:

- `app_dt` (required)
- `PID` (optional)
- `ID` (optional)
- `key_type` (optional)

### Key-type resolution rules

If `key_type` is present, it has priority:

- `pid` requires non-null `PID`
- `id` requires non-null `ID`
- `pid_id` requires both non-null `PID` and `ID`

If `key_type` is absent, infer it:

- only `PID` present -> `pid`
- only `ID` present -> `id`
- both `PID` and `ID` present -> `pid_id`

If neither `PID` nor `ID` is available, the query row is invalid and should raise an error.

If explicit `key_type` conflicts with available columns, the query row is invalid and should raise an error rather than silently downgrade to another key type.

## Key Representation and Output Changes

The current pipeline returns only:

- `key_type`
- `key_value`

The revised output should always keep:

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

This ensures query outputs match the requested key shape:

- querying by `pid` returns populated `PID`, null `ID`
- querying by `id` returns populated `ID`, null `PID`
- querying by `pid_id` returns both `PID` and `ID`

`key_value` remains in the output for debugging, compatibility, and unified join behavior.

## Function Responsibility Changes

### Existing behavior to split

Current `expand_keys()` always expands each record into all three key types.

That behavior should be split into two capabilities:

- full expansion for historical event generation and batch snapshot generation
- selected/single-key construction for external query lookup

### Recommended function roles

- `build_application_base(df)`
- `expand_all_key_types(df)`
- `build_history_query_snapshot(df, key_types=None)`
- `build_external_query_snapshot(query_df)`
- `build_default_event_key_fact(df, key_types=None)`
- `lookup_step1(query_snapshot, event_fact)`
- `lookup_step2(query_snapshot, event_fact)`
- `lookup_step3(query_snapshot, event_fact)`
- `lookup_step4(query_snapshot, event_fact)`

Optional facade:

- `lookup_all_steps(history_df, query_df, step3_format="long")`

## Step Output Definitions

All steps share these base columns:

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

### Step 1

One row per query key:

- `black_hit_ever`
- `first_default_event_dt`

### Step 2

One row per query key:

- `black_hit_ever`
- `first_default_event_dt`
- `latest_default_event_dt`
- `hit_event_cnt_asof_dt`

### Step 3

Default output: long table.

Columns:

- base columns
- `org_class`
- `black_hit_ever_by_org_class`
- `first_default_event_dt_by_org_class`

### Step 4

One row per query key:

- `default_cnt_3m`
- `default_cnt_6m`
- `default_cnt_12m`
- `default_cnt_3m_bank`
- `default_cnt_6m_bank`
- `default_cnt_3m_rate24`
- `default_cnt_3m_fpd`
- `default_cnt_3m_dpd`

## Return Shape Recommendation

Do not force all steps into a single DataFrame because `step3` is long-form while the others are one-row-per-query-key.

Recommended top-level return:

```python
{
    "step1": step1_df,
    "step2": step2_df,
    "step3": step3_df,
    "step4": step4_df,
}
```

This keeps shapes explicit and avoids awkward mixed-grain outputs.

## Error Handling

Query lookup should validate inputs more strictly than the offline batch path.

Required checks:

- `app_dt` must exist and be parseable
- `key_type`, if present, must be one of `pid`, `id`, `pid_id`
- required key columns must exist for the chosen `key_type`
- rows with neither `PID` nor `ID` are invalid

Do not silently skip invalid query rows in V1.

## Testing Strategy

New tests should cover:

1. explicit `key_type` queries
2. inferred `key_type` queries
3. invalid query rows and error messages
4. query rows not present in historical applications
5. query rows with no prior effective default events
6. split-key output columns in all steps
7. offline compatibility after refactor
8. `step3` long-form query output

## Delivery Order

1. Refactor key helpers so batch and query use the same internal key schema.
2. Add external query snapshot construction and validation.
3. Refactor `step1-step4` functions to accept query snapshots.
4. Rewire the offline pipeline to use history-derived query snapshots.
5. Add a query lookup facade that returns all step outputs.
6. Add tests for arbitrary key/date lookup and backward compatibility.
