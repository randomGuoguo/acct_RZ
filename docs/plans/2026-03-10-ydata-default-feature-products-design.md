# Ydata Default Feature Products Design

**Date:** 2026-03-10

**Goal:** Design an offline-first feature/product layer that turns raw Ydata application records into four reusable default-history products: blacklist hit, as-of-date traceback blacklist, org-class blacklist, and rolling-window default counts.

## Scope

- Cover `step1-step4` in [`TASK.md`](D:\wise\acct_RZ\TASK.md).
- Stop at the feature/product layer.
- Do not design scorecard mapping, model scoring, API serving, or external delivery interfaces.
- Optimize for offline batch generation while preserving a clean upgrade path to future near-real-time lookup.

## Context

- The current workspace contains requirements docs and sample data only.
- Sample data is [`data/demo/y.csv`](D:\wise\acct_RZ\data\demo\y.csv).
- Current coding guidance in [`coding_style.md`](D:\wise\acct_RZ\coding_style.md) favors MVP, pure functions, docstring-as-source-of-truth, and pytest-backed examples.
- The workspace is not currently a git repository, so a commit could not be created during design approval.

## Confirmed Business Rules

- Only `target == 1` is treated as a default event.
- Any other current or future value such as `0`, `-2`, `0.5`, or `-1` is treated as non-default for event generation.
- Default event effective date is `event_dt = app_dt + mob_filled(months)`.
- If `mob` is missing, use `6` months.
- All blacklist hits, traceback results, and rolling-window counts use `event_dt` rather than raw `app_dt`.
- `step3` uses `Org_class_new` as the segmentation dimension.
- `step4` first version focuses on count-style features.

## Architecture

The design uses a shared event-centric pipeline instead of separate logic per step.

### 1. `raw_y`

- Direct typed representation of the input file.
- Responsibilities:
  - Parse `app_dt` into a date.
  - Preserve original fields and values.
  - Avoid business interpretation at this layer.

### 2. `application_base`

- One normalized row per raw application observation.
- Derived fields:
  - `mob_filled`
  - `is_default`
  - `event_dt`
- Purpose:
  - Freeze the core time semantics once.
  - Provide a shared source for both event facts and query snapshots.

### 3. `default_event_fact`

- Contains only rows where `is_default == 1`.
- Keeps event attributes required for later slicing:
  - `PID`
  - `ID`
  - `Org_class_new`
  - `Org_new`
  - `perf_type`
  - `threshold_dpd`
  - `channel_new`
  - `event_dt`
- This is the single source of truth for all downstream default-history features.

### 4. `feature_mart`

- Produces feature/product outputs keyed by application date and entity key view.
- All four task steps are derived here from the same event fact base.

## Entity Key Strategy

Three business key views must be supported:

- `pid_id`
- `id`
- `pid`

Instead of implementing separate pipelines for each one, both applications and events are expanded into a normalized key structure:

- `key_type`
- `key_value`

Examples:

- `key_type = "pid_id"`, `key_value = PID + "|" + ID`
- `key_type = "id"`, `key_value = ID`
- `key_type = "pid"`, `key_value = PID`

This produces a unified lookup model:

- Query grain: `(app_dt, key_type, key_value)`
- Match rule: `event_dt <= app_dt`

Trade-off:

- Row counts grow by up to 3x after key expansion.
- That storage cost is accepted to guarantee one consistent implementation path across all products.

## Data Flow

1. Load raw Ydata rows into `raw_y`.
2. Normalize rows into `application_base`.
3. Expand each application into `application_key_snapshot`.
4. Filter defaults from `application_base` into `default_event_fact`.
5. Expand each default event into `default_event_key_fact`.
6. Join or window-aggregate `application_key_snapshot` against `default_event_key_fact` by:
   - same `key_type`
   - same `key_value`
   - `event_dt <= app_dt`
7. Derive product outputs for `step1-step4`.

## Product Output Definitions

All outputs should share the same minimum key columns:

- `app_dt`
- `key_type`
- `key_value`

Optionally retain `PID` and `ID` from the application side for traceability.

### Step 1: Simple Blacklist Product

Minimum fields:

- `app_dt`
- `key_type`
- `key_value`
- `black_hit_ever`
- `first_default_event_dt`

Rule:

- `black_hit_ever = 1` if any matched event has `event_dt <= app_dt`.

### Step 2: Traceback Blacklist Product

Extends step 1 with as-of-date detail:

- `hit_event_cnt_asof_dt`
- `latest_default_event_dt`

This is not a different event rule; it is the same logic emitted for every application date snapshot.

### Step 3: Org-Class Blacklist Product

Recommended initial output shape: long table.

Fields:

- `app_dt`
- `key_type`
- `key_value`
- `org_class`
- `black_hit_ever_by_org_class`
- `first_default_event_dt_by_org_class`

Long shape is preferred because org classes may expand later.

### Step 4: Org/Class-Aware Default Record Product

First-version features should focus on rolling counts, for example:

- `default_cnt_3m`
- `default_cnt_6m`
- `default_cnt_12m`
- `default_cnt_3m_bank`
- `default_cnt_6m_bank`
- `default_cnt_3m_rate24`
- `default_cnt_3m_fpd`
- `default_cnt_3m_dpd`

Window rule:

- include event if `event_dt <= app_dt`
- and `event_dt > app_dt - window_months`

## Error Handling

The first version stays lightweight, but the following guardrails are required:

- Drop rows whose `app_dt` cannot be parsed, and record the dropped count.
- If `mob` is non-empty but invalid, treat it as missing and backfill `6`.
- Key generation rules:
  - `pid_id` requires both `PID` and `ID`
  - `id` requires non-empty `ID`
  - `pid` requires non-empty `PID`
- Do not aggressively deduplicate same-key same-date events in V1 unless a business rule is defined for that behavior.

## Testing Strategy

Tests should target business time semantics rather than implementation details.

Required minimum coverage:

1. Effective-date rule
   - `target=1`, `app_dt=2024-03-10`, `mob=6` only hits on and after `2024-09-10`.
2. Missing-`mob` rule
   - empty `mob` defaults to `6`.
3. Non-default label rule
   - values such as `0`, `-2`, `0.5`, `-1` do not create default events.
4. Key expansion rule
   - valid records expand to `pid_id`, `id`, and `pid`.
   - partial keys only emit legal key variants.
5. Traceback rule
   - the same entity changes state across different `app_dt` snapshots.
6. Rolling-window rule
   - 3/6/12 month count boundaries are correct on inclusion edges.

## Recommended Delivery Order

1. Build shared normalization and event layers.
2. Deliver `step1` and `step2` from the same as-of lookup logic.
3. Add `Org_class_new` grouping for `step3`.
4. Add rolling-window count features for `step4`.

This order matches the actual complexity gradient:

- first solve as-of historical matching,
- then grouped matching,
- then windowed aggregation.
