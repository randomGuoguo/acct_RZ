# Blacklist Feature Product Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the current default-history pipeline into a model-oriented blacklist feature product that outputs one stable wide table built from reusable aggregation modules.

**Architecture:** Keep the current `query_snapshot + event_fact` backbone, introduce reusable aggregation modules for lifetime, rolling-window, grouped-breakdown, and recency metrics, then assemble model-facing label families into a single `blacklist_features` product table. Keep `step1~step4` as compatibility wrappers during migration rather than as the future product boundary.

**Tech Stack:** Python 3.9, Polars, pytest

---

### Task 1: Add a shared feature-product constants module

**Files:**
- Create: `src/acct_rz/feature_product.py`
- Test: `tests/test_feature_product.py`

**Step 1: Write the failing test**

```python
from acct_rz.feature_product import BLACKLIST_WINDOWS, STABLE_ORG_TYPES, STABLE_PERF_TYPES


def test_feature_product_constants_expose_expected_defaults():
    assert BLACKLIST_WINDOWS == ("3m", "6m", "9m", "12m", "24m", "36m")
    assert STABLE_ORG_TYPES == ("bank", "rate24", "rate36")
    assert STABLE_PERF_TYPES == ("fpd", "dpd")
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_feature_product.py::test_feature_product_constants_expose_expected_defaults`
Expected: FAIL because the module does not exist yet.

**Step 3: Write minimal implementation**

```python
BLACKLIST_WINDOWS = ("3m", "6m", "9m", "12m", "24m", "36m")
STABLE_ORG_TYPES = ("bank", "rate24", "rate36")
STABLE_PERF_TYPES = ("fpd", "dpd")
BASE_FEATURE_KEY_COLUMNS = ("app_dt", "key_type", "key_value", "PID", "ID")
```

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_feature_product.py::test_feature_product_constants_expose_expected_defaults`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/feature_product.py tests/test_feature_product.py
git commit -m "feat: add blacklist feature product constants"
```

### Task 2: Create reusable lifetime aggregation

**Files:**
- Create: `src/acct_rz/agg_lifetime.py`
- Test: `tests/test_agg_lifetime.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.agg_lifetime import build_lifetime_aggregates
from acct_rz.events import build_default_event_key_fact
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_lifetime_aggregates_returns_history_metrics():
    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-01-01", "2024-06-01"],
            "target": [1, 1],
            "mob": [3, 6],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_lifetime_aggregates(query_snapshot, event_fact)

    assert result["ever_default_flag"].item() == 1
    assert result["default_cnt_lifetime"].item() == 2
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_agg_lifetime.py::test_build_lifetime_aggregates_returns_history_metrics`
Expected: FAIL because the aggregation module does not exist yet.

**Step 3: Write minimal implementation**

```python
def build_lifetime_aggregates(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    ...
```

Return at least:

- base key columns
- `ever_default_flag`
- `first_default_dt`
- `latest_default_dt`
- `default_cnt_lifetime`
- `default_month_cnt_lifetime`

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_agg_lifetime.py::test_build_lifetime_aggregates_returns_history_metrics`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/agg_lifetime.py tests/test_agg_lifetime.py
git commit -m "feat: add lifetime default aggregations"
```

### Task 3: Add reusable recency derivation helpers

**Files:**
- Create: `src/acct_rz/agg_recency.py`
- Test: `tests/test_agg_recency.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.agg_recency import add_days_since_columns


def test_add_days_since_columns_uses_app_dt_as_reference():
    df = pl.DataFrame(
        {
            "app_dt": [20250101],
            "latest_default_dt": [20241201],
            "first_default_dt": [20240101],
        }
    )

    result = add_days_since_columns(
        df,
        {
            "latest_default_dt": "days_since_latest_default",
            "first_default_dt": "days_since_first_default",
        },
    )

    assert result["days_since_latest_default"].item() > 0
    assert result["days_since_first_default"].item() > result["days_since_latest_default"].item()
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_agg_recency.py::test_add_days_since_columns_uses_app_dt_as_reference`
Expected: FAIL because the helper module does not exist yet.

**Step 3: Write minimal implementation**

```python
def add_days_since_columns(df: pl.DataFrame, mapping: dict[str, str]) -> pl.DataFrame:
    ...
```

Compute day distances from `app_dt` to each source date column while preserving nulls.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_agg_recency.py::test_add_days_since_columns_uses_app_dt_as_reference`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/agg_recency.py tests/test_agg_recency.py
git commit -m "feat: add blacklist recency derivation helpers"
```

### Task 4: Create reusable rolling-window aggregation

**Files:**
- Create: `src/acct_rz/agg_windows.py`
- Modify: `src/acct_rz/feature_product.py`
- Test: `tests/test_agg_windows.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.agg_windows import build_window_aggregates
from acct_rz.events import build_default_event_key_fact
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_window_aggregates_returns_multi_window_counts():
    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-10-01", "2024-12-01"],
            "target": [1, 1],
            "mob": [0, 0],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_window_aggregates(query_snapshot, event_fact)

    assert result["default_cnt_3m"].item() >= 1
    assert result["default_cnt_12m"].item() == 2
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_agg_windows.py::test_build_window_aggregates_returns_multi_window_counts`
Expected: FAIL because the module does not exist yet.

**Step 3: Write minimal implementation**

```python
def build_window_aggregates(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    ...
```

Return:

- `default_flag_{window}`
- `default_cnt_{window}`
- `default_month_cnt_{window}`
- `default_org_type_cnt_{window}`
- `default_perf_type_cnt_{window}`

for all configured windows.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_agg_windows.py::test_build_window_aggregates_returns_multi_window_counts`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/agg_windows.py src/acct_rz/feature_product.py tests/test_agg_windows.py
git commit -m "feat: add rolling window blacklist aggregations"
```

### Task 5: Add generalized grouped-breakdown aggregation

**Files:**
- Create: `src/acct_rz/agg_breakdown.py`
- Test: `tests/test_agg_breakdown.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.agg_breakdown import build_grouped_breakdown
from acct_rz.events import build_default_event_key_fact
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_grouped_breakdown_returns_counts_by_dimension():
    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-01-01", "2024-06-01"],
            "target": [1, 1],
            "mob": [0, 0],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_grouped_breakdown(query_snapshot, event_fact, dimension="org_type")

    assert {"bank", "rate24"} == set(result["dim_value"].to_list())
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_agg_breakdown.py::test_build_grouped_breakdown_returns_counts_by_dimension`
Expected: FAIL because the module does not exist yet.

**Step 3: Write minimal implementation**

```python
def build_grouped_breakdown(
    query_snapshot: pl.DataFrame,
    event_fact: pl.DataFrame,
    dimension: str,
) -> pl.DataFrame:
    ...
```

Return a long table with:

- base key columns
- `dim_type`
- `dim_value`
- lifetime hit and count metrics
- latest date
- configured window counts

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_agg_breakdown.py::test_build_grouped_breakdown_returns_counts_by_dimension`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/agg_breakdown.py tests/test_agg_breakdown.py
git commit -m "feat: add grouped blacklist breakdown aggregations"
```

### Task 6: Build the history label family

**Files:**
- Create: `src/acct_rz/labels_history.py`
- Modify: `src/acct_rz/agg_lifetime.py`
- Modify: `src/acct_rz/agg_recency.py`
- Test: `tests/test_labels_history.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.labels_history import build_history_labels
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_history_labels_returns_model_facing_columns():
    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["2024-01-01"],
            "target": [1],
            "mob": [0],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_history_labels(query_snapshot, event_fact)

    assert {"ever_default_flag", "days_since_latest_default", "default_cnt_lifetime"}.issubset(set(result.columns))
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_labels_history.py::test_build_history_labels_returns_model_facing_columns`
Expected: FAIL because the label-family module does not exist yet.

**Step 3: Write minimal implementation**

```python
def build_history_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    ...
```

Compose lifetime metrics and day-distance metrics into one output family.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_labels_history.py::test_build_history_labels_returns_model_facing_columns`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/labels_history.py src/acct_rz/agg_lifetime.py src/acct_rz/agg_recency.py tests/test_labels_history.py
git commit -m "feat: add blacklist history label family"
```

### Task 7: Build the rolling-window label family

**Files:**
- Create: `src/acct_rz/labels_window.py`
- Modify: `src/acct_rz/agg_windows.py`
- Test: `tests/test_labels_window.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.labels_window import build_window_labels
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_window_labels_exposes_model_window_fields():
    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["2024-12-01"],
            "target": [1],
            "mob": [0],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_window_labels(query_snapshot, event_fact)

    assert {"default_flag_3m", "default_cnt_12m", "default_org_type_cnt_36m"}.issubset(set(result.columns))
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_labels_window.py::test_build_window_labels_exposes_model_window_fields`
Expected: FAIL because the label-family module does not exist yet.

**Step 3: Write minimal implementation**

```python
def build_window_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    ...
```

Expose the configured multi-window fields unchanged from the aggregation layer.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_labels_window.py::test_build_window_labels_exposes_model_window_fields`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/labels_window.py src/acct_rz/agg_windows.py tests/test_labels_window.py
git commit -m "feat: add blacklist rolling window label family"
```

### Task 8: Build stable institution-type and performance-type label families

**Files:**
- Create: `src/acct_rz/labels_orgtype.py`
- Create: `src/acct_rz/labels_perftype.py`
- Modify: `src/acct_rz/agg_breakdown.py`
- Modify: `src/acct_rz/agg_recency.py`
- Test: `tests/test_labels_breakdown.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.labels_orgtype import build_orgtype_labels
from acct_rz.labels_perftype import build_perftype_labels
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_breakdown_labels_expand_only_stable_categories():
    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-01-01", "2024-02-01"],
            "target": [1, 1],
            "mob": [0, 0],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    org_df = build_orgtype_labels(query_snapshot, event_fact)
    perf_df = build_perftype_labels(query_snapshot, event_fact)

    assert "default_cnt_12m_bank" in org_df.columns
    assert "default_cnt_12m_rate24" in org_df.columns
    assert "default_cnt_12m_dpd" in perf_df.columns
    assert "default_cnt_12m_fpd" in perf_df.columns
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_labels_breakdown.py::test_build_breakdown_labels_expand_only_stable_categories`
Expected: FAIL because the label-family modules do not exist yet.

**Step 3: Write minimal implementation**

```python
def build_orgtype_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    ...


def build_perftype_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    ...
```

Use long breakdown aggregates and pivot only the configured stable categories.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_labels_breakdown.py::test_build_breakdown_labels_expand_only_stable_categories`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/labels_orgtype.py src/acct_rz/labels_perftype.py src/acct_rz/agg_breakdown.py src/acct_rz/agg_recency.py tests/test_labels_breakdown.py
git commit -m "feat: add stable breakdown label families"
```

### Task 9: Build the complexity label family

**Files:**
- Create: `src/acct_rz/labels_complexity.py`
- Modify: `src/acct_rz/agg_breakdown.py`
- Test: `tests/test_labels_complexity.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.events import build_default_event_key_fact
from acct_rz.labels_complexity import build_complexity_labels
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_complexity_labels_returns_multi_head_features():
    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-01-01", "2024-06-01"],
            "target": [1, 1],
            "mob": [0, 0],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))
    event_fact = build_default_event_key_fact(history_df)

    result = build_complexity_labels(query_snapshot, event_fact)

    assert {"is_multi_org_default_12m", "is_multi_perf_default_12m", "latest_default_org_type"}.issubset(set(result.columns))
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_labels_complexity.py::test_build_complexity_labels_returns_multi_head_features`
Expected: FAIL because the label-family module does not exist yet.

**Step 3: Write minimal implementation**

```python
def build_complexity_labels(query_snapshot: pl.DataFrame, event_fact: pl.DataFrame) -> pl.DataFrame:
    ...
```

Derive multi-type flags and latest-type fields from the grouped breakdown aggregates.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_labels_complexity.py::test_build_complexity_labels_returns_multi_head_features`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/labels_complexity.py src/acct_rz/agg_breakdown.py tests/test_labels_complexity.py
git commit -m "feat: add blacklist complexity label family"
```

### Task 10: Assemble the final blacklist feature product

**Files:**
- Create: `src/acct_rz/product_blacklist_features.py`
- Test: `tests/test_product_blacklist_features.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.product_blacklist_features import build_blacklist_features
from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_blacklist_features_returns_one_row_per_query_key():
    history_df = pl.DataFrame(
        {
            "PID": ["p1", "p1"],
            "ID": ["i1", "i2"],
            "app_dt": ["2024-01-01", "2024-06-01"],
            "target": [1, 1],
            "mob": [0, 0],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(
        pl.DataFrame(
            {
                "app_dt": ["2025-01-01", "2025-01-01"],
                "PID": ["p1", "p9"],
            }
        )
    )

    result = build_blacklist_features(history_df, query_snapshot)

    assert result.shape[0] == 2
    assert "ever_default_flag" in result.columns
    assert "default_cnt_12m_bank" in result.columns
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_product_blacklist_features.py::test_build_blacklist_features_returns_one_row_per_query_key`
Expected: FAIL because the product assembly module does not exist yet.

**Step 3: Write minimal implementation**

```python
def build_blacklist_features(history_df: pl.DataFrame, query_snapshot: pl.DataFrame) -> pl.DataFrame:
    ...
```

Steps:

- build event fact from `history_df`
- build each label family
- left-join families on base key columns
- assert one-row-per-query-key cardinality

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_product_blacklist_features.py::test_build_blacklist_features_returns_one_row_per_query_key`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/product_blacklist_features.py tests/test_product_blacklist_features.py
git commit -m "feat: assemble blacklist feature product"
```

### Task 11: Reimplement `step1~step4` as compatibility wrappers over the new internals

**Files:**
- Modify: `src/acct_rz/features_blacklist.py`
- Modify: `src/acct_rz/features_org_blacklist.py`
- Modify: `src/acct_rz/features_windows.py`
- Test: `tests/test_features_blacklist.py`
- Test: `tests/test_features_org_blacklist.py`
- Test: `tests/test_features_windows.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.features_blacklist import lookup_step2
from acct_rz.query_snapshot import build_external_query_snapshot


def test_lookup_step2_still_matches_compatibility_contract():
    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["2024-01-01"],
            "target": [1],
            "mob": [0],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
        }
    )
    query_snapshot = build_external_query_snapshot(pl.DataFrame({"app_dt": ["2025-01-01"], "PID": ["p1"]}))

    result = lookup_step2(history_df, query_snapshot)

    assert {"black_hit_ever", "latest_default_event_dt", "hit_event_cnt_asof_dt"}.issubset(set(result.columns))
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_features_blacklist.py::test_lookup_step2_still_matches_compatibility_contract`
Expected: FAIL if the old step contract is broken during refactor.

**Step 3: Write minimal implementation**

Preserve the current step outputs by mapping them from the new aggregation and label-family internals.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_features_blacklist.py::test_lookup_step2_still_matches_compatibility_contract`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/features_blacklist.py src/acct_rz/features_org_blacklist.py src/acct_rz/features_windows.py tests/test_features_blacklist.py tests/test_features_org_blacklist.py tests/test_features_windows.py
git commit -m "refactor: keep step compatibility over feature product internals"
```

### Task 12: Wire the product into the batch pipeline and query facade

**Files:**
- Modify: `src/acct_rz/pipeline.py`
- Modify: `src/acct_rz/query_lookup.py`
- Modify: `run_pipeline.py`
- Test: `tests/test_pipeline_smoke.py`
- Test: `tests/test_query_lookup.py`
- Test: `tests/test_run_pipeline.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

import polars as pl

from acct_rz.pipeline import run_demo_pipeline


def test_run_demo_pipeline_writes_blacklist_feature_product(tmp_path):
    out_dir = tmp_path / "result"
    run_demo_pipeline(Path("data/demo/y.csv"), out_dir)

    result = pl.read_parquet(out_dir / "blacklist_features.parquet")

    assert "ever_default_flag" in result.columns
    assert "default_cnt_36m" in result.columns
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_pipeline_smoke.py::test_run_demo_pipeline_writes_blacklist_feature_product`
Expected: FAIL because the pipeline does not yet emit the new product file.

**Step 3: Write minimal implementation**

Update batch and query orchestration so they can:

- build the new product table
- optionally continue writing legacy `step1~step4` outputs during transition

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_pipeline_smoke.py::test_run_demo_pipeline_writes_blacklist_feature_product`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/pipeline.py src/acct_rz/query_lookup.py run_pipeline.py tests/test_pipeline_smoke.py tests/test_query_lookup.py tests/test_run_pipeline.py
git commit -m "feat: wire blacklist feature product into pipeline"
```

### Task 13: Document the new feature contract

**Files:**
- Modify: `README.md`
- Modify: `TASK2.md`
- Modify: `architecture.md`
- Test: `tests/test_readme.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_readme_mentions_blacklist_features_product():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "blacklist_features.parquet" in text
    assert "ever_default_flag" in text
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_readme.py::test_readme_mentions_blacklist_features_product`
Expected: FAIL because the docs do not describe the new product yet.

**Step 3: Write minimal implementation**

Document:

- the new primary output table
- feature-family naming rules
- the role of legacy `step1~step4`
- the optional long-form detail layer

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_readme.py::test_readme_mentions_blacklist_features_product`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md TASK2.md architecture.md tests/test_readme.py
git commit -m "docs: describe blacklist feature product contract"
```

### Task 14: Run the full regression suite

**Files:**
- No file changes required unless regression defects are found.

**Step 1: Write the failing test**

No new tests. Use the full suite as the gate.

**Step 2: Run test to verify current status**

Run: `conda run -n dl_new python -m pytest -q`
Expected: Identify any breakages introduced during migration.

**Step 3: Write minimal implementation**

Fix only the smallest necessary defects uncovered by the regression suite.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q`
Expected: PASS

**Step 5: Commit**

```bash
git add .
git commit -m "test: verify blacklist feature product refactor end to end"
```

## Notes

- Keep `y.csv` strictly as the historical event source.
- Keep `sample_flag` out of the first model-facing wide-table contract.
- Preserve unmatched-query behavior: row kept, counts `0`, dates `null`.
- Avoid hard-coding future expansion into `step` semantics.
- Treat `step1~step4` as compatibility surfaces during migration, not as the target architecture.
