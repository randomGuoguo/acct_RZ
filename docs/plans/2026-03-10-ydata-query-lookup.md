# Ydata Query Lookup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the current offline feature pipeline so any external `PID`, `ID`, or `PID+ID` plus `app_dt` can be queried for `step1-step4` results using the same default-event logic as the batch path.

**Architecture:** Separate historical event generation from query snapshot generation. Keep `y.csv` as the historical default-event source, add a validated external query snapshot builder, then refactor `step1-step4` into lookup functions that accept a query snapshot and event fact table. Rewire the offline pipeline to build its outputs through the same lookup path.

**Tech Stack:** Python 3.9, Polars, pytest

---

### Task 1: Refactor key helpers for split-key output and selectable key construction

**Files:**
- Modify: `src/acct_rz/keys.py`
- Test: `tests/test_keys.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.keys import build_selected_key_snapshot, expand_all_key_types


def test_build_selected_key_snapshot_keeps_split_key_columns():
    df = pl.DataFrame(
        {
            "PID": ["p1", None, "p3"],
            "ID": ["i1", "i2", None],
            "app_dt": ["20240101", "20240102", "20240103"],
        }
    )

    result = build_selected_key_snapshot(df)

    assert result.select("key_type").to_series().to_list() == ["pid_id", "id", "pid"]
    assert result.select("PID").to_series().to_list() == ["p1", None, "p3"]
    assert result.select("ID").to_series().to_list() == ["i1", "i2", None]
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_keys.py::test_build_selected_key_snapshot_keeps_split_key_columns`
Expected: FAIL because the helper does not exist yet.

**Step 3: Write minimal implementation**

```python
def expand_all_key_types(df: pl.DataFrame) -> pl.DataFrame:
    ...


def build_selected_key_snapshot(df: pl.DataFrame) -> pl.DataFrame:
    ...
```

Ensure returned rows always contain:

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_keys.py::test_build_selected_key_snapshot_keeps_split_key_columns`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/keys.py tests/test_keys.py
git commit -m "refactor: split key expansion and selected key snapshots"
```

### Task 2: Add validated external query snapshot builder

**Files:**
- Create: `src/acct_rz/query_snapshot.py`
- Modify: `src/acct_rz/keys.py`
- Test: `tests/test_query_snapshot.py`

**Step 1: Write the failing test**

```python
import polars as pl
import pytest

from acct_rz.query_snapshot import build_external_query_snapshot


def test_build_external_query_snapshot_infers_key_type():
    query_df = pl.DataFrame(
        {
            "app_dt": ["20250101", "20250102", "20250103"],
            "PID": ["p1", None, "p3"],
            "ID": ["i1", "i2", None],
        }
    )

    result = build_external_query_snapshot(query_df)

    assert result["key_type"].to_list() == ["pid_id", "id", "pid"]


def test_build_external_query_snapshot_rejects_invalid_key_rows():
    query_df = pl.DataFrame({"app_dt": ["20250101"], "PID": [None], "ID": [None]})

    with pytest.raises(ValueError):
        build_external_query_snapshot(query_df)
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_query_snapshot.py`
Expected: FAIL because the module does not exist yet.

**Step 3: Write minimal implementation**

```python
def build_external_query_snapshot(query_df: pl.DataFrame) -> pl.DataFrame:
    ...
```

Required behavior:

- parse `app_dt`
- honor explicit `key_type`
- infer `key_type` when absent
- reject invalid rows
- return `app_dt`, `key_type`, `key_value`, `PID`, `ID`

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_query_snapshot.py`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/query_snapshot.py src/acct_rz/keys.py tests/test_query_snapshot.py
git commit -m "feat: add validated external query snapshots"
```

### Task 3: Refactor event fact generation to preserve split key columns

**Files:**
- Modify: `src/acct_rz/events.py`
- Modify: `src/acct_rz/keys.py`
- Test: `tests/test_events.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.events import build_default_event_key_fact


def test_build_default_event_key_fact_keeps_pid_and_id_columns():
    df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["20240101"],
            "target": [1],
            "mob": ["6"],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
            "threshold_dpd": ["30"],
            "channel_new": ["api"],
        }
    )

    result = build_default_event_key_fact(df)

    assert {"PID", "ID", "key_type", "key_value", "event_dt"}.issubset(set(result.columns))
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_events.py::test_build_default_event_key_fact_keeps_pid_and_id_columns`
Expected: FAIL because the event fact does not yet guarantee the split key columns.

**Step 3: Write minimal implementation**

```python
def build_default_event_key_fact(df: pl.DataFrame, key_types: list[str] | None = None) -> pl.DataFrame:
    ...
```

Keep `PID` and `ID` in the event fact after expansion.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_events.py::test_build_default_event_key_fact_keeps_pid_and_id_columns`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/events.py src/acct_rz/keys.py tests/test_events.py
git commit -m "refactor: preserve split keys in event facts"
```

### Task 4: Refactor step1 and step2 into query-snapshot lookup functions

**Files:**
- Modify: `src/acct_rz/features_blacklist.py`
- Modify: `src/acct_rz/query_snapshot.py`
- Test: `tests/test_features_blacklist.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.features_blacklist import lookup_step2
from acct_rz.query_snapshot import build_external_query_snapshot


def test_lookup_step2_returns_rows_for_arbitrary_query_dates():
    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["20240101"],
            "target": [1],
            "mob": ["6"],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
            "threshold_dpd": ["30"],
            "channel_new": ["api"],
        }
    )
    query_df = pl.DataFrame({"app_dt": ["20241001"], "PID": ["p1"], "ID": ["i1"]})

    result = lookup_step2(history_df, build_external_query_snapshot(query_df))

    assert result["black_hit_ever"].item() == 1
    assert result["PID"].item() == "p1"
    assert result["ID"].item() == "i1"
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_features_blacklist.py::test_lookup_step2_returns_rows_for_arbitrary_query_dates`
Expected: FAIL because lookup functions do not yet accept external query snapshots.

**Step 3: Write minimal implementation**

```python
def lookup_step1(history_df: pl.DataFrame, query_snapshot: pl.DataFrame) -> pl.DataFrame:
    ...


def lookup_step2(history_df: pl.DataFrame, query_snapshot: pl.DataFrame) -> pl.DataFrame:
    ...
```

Return:

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`
- step1/step2 metrics

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_features_blacklist.py::test_lookup_step2_returns_rows_for_arbitrary_query_dates`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/features_blacklist.py src/acct_rz/query_snapshot.py tests/test_features_blacklist.py
git commit -m "refactor: add query snapshot blacklist lookups"
```

### Task 5: Refactor step3 into query-snapshot long-form lookup

**Files:**
- Modify: `src/acct_rz/features_org_blacklist.py`
- Test: `tests/test_features_org_blacklist.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.features_org_blacklist import lookup_step3
from acct_rz.query_snapshot import build_external_query_snapshot


def test_lookup_step3_returns_long_form_org_rows_for_arbitrary_queries():
    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["20240101"],
            "target": [1],
            "mob": ["6"],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
            "threshold_dpd": ["30"],
            "channel_new": ["api"],
        }
    )
    query_df = pl.DataFrame({"app_dt": ["20241001"], "PID": ["p1"], "ID": ["i1"]})

    result = lookup_step3(history_df, build_external_query_snapshot(query_df))

    assert {"PID", "ID", "org_class", "black_hit_ever_by_org_class"}.issubset(set(result.columns))
    assert result.filter(pl.col("org_class") == "Bank")["black_hit_ever_by_org_class"].item() == 1
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_features_org_blacklist.py::test_lookup_step3_returns_long_form_org_rows_for_arbitrary_queries`
Expected: FAIL because step3 is still tied to history-derived snapshots.

**Step 3: Write minimal implementation**

```python
def lookup_step3(history_df: pl.DataFrame, query_snapshot: pl.DataFrame, output_format: str = "long") -> pl.DataFrame:
    ...
```

Keep default output in long format.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_features_org_blacklist.py::test_lookup_step3_returns_long_form_org_rows_for_arbitrary_queries`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/features_org_blacklist.py tests/test_features_org_blacklist.py
git commit -m "refactor: add query snapshot org blacklist lookups"
```

### Task 6: Refactor step4 into query-snapshot rolling-window lookup

**Files:**
- Modify: `src/acct_rz/features_windows.py`
- Test: `tests/test_features_windows.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.features_windows import lookup_step4
from acct_rz.query_snapshot import build_external_query_snapshot


def test_lookup_step4_returns_zero_rows_for_unseen_keys():
    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["20240101"],
            "target": [1],
            "mob": ["6"],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
            "threshold_dpd": ["30"],
            "channel_new": ["api"],
        }
    )
    query_df = pl.DataFrame({"app_dt": ["20241001"], "PID": ["p9"]})

    result = lookup_step4(history_df, build_external_query_snapshot(query_df))

    assert result["default_cnt_3m"].item() == 0
    assert result["default_cnt_12m"].item() == 0
    assert result["PID"].item() == "p9"
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_features_windows.py::test_lookup_step4_returns_zero_rows_for_unseen_keys`
Expected: FAIL because step4 does not yet support arbitrary external query keys.

**Step 3: Write minimal implementation**

```python
def lookup_step4(history_df: pl.DataFrame, query_snapshot: pl.DataFrame) -> pl.DataFrame:
    ...
```

Preserve one row per query key even when there are no matched historical events.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_features_windows.py::test_lookup_step4_returns_zero_rows_for_unseen_keys`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/features_windows.py tests/test_features_windows.py
git commit -m "refactor: add query snapshot window lookups"
```

### Task 7: Add a unified query facade for step1-step4

**Files:**
- Create: `src/acct_rz/query_lookup.py`
- Test: `tests/test_query_lookup.py`

**Step 1: Write the failing test**

```python
import polars as pl

from acct_rz.query_lookup import lookup_all_steps


def test_lookup_all_steps_returns_dict_of_step_outputs():
    history_df = pl.DataFrame(
        {
            "PID": ["p1"],
            "ID": ["i1"],
            "app_dt": ["20240101"],
            "target": [1],
            "mob": ["6"],
            "Org_class_new": ["Bank"],
            "Org_new": ["A"],
            "perf_type": ["dpd"],
            "threshold_dpd": ["30"],
            "channel_new": ["api"],
        }
    )
    query_df = pl.DataFrame({"app_dt": ["20241001"], "PID": ["p1"], "ID": ["i1"]})

    result = lookup_all_steps(history_df, query_df)

    assert set(result.keys()) == {"step1", "step2", "step3", "step4"}
    assert result["step1"]["black_hit_ever"].item() == 1
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_query_lookup.py`
Expected: FAIL because the facade does not exist yet.

**Step 3: Write minimal implementation**

```python
def lookup_all_steps(history_df: pl.DataFrame, query_df: pl.DataFrame, step3_format: str = "long") -> dict[str, pl.DataFrame]:
    ...
```

Use:

- `build_external_query_snapshot(query_df)`
- `lookup_step1`
- `lookup_step2`
- `lookup_step3`
- `lookup_step4`

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_query_lookup.py`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/query_lookup.py tests/test_query_lookup.py
git commit -m "feat: add unified query lookup facade"
```

### Task 8: Rewire the offline pipeline to use history-derived query snapshots

**Files:**
- Modify: `src/acct_rz/pipeline.py`
- Modify: `src/acct_rz/features_blacklist.py`
- Modify: `src/acct_rz/features_org_blacklist.py`
- Modify: `src/acct_rz/features_windows.py`
- Test: `tests/test_pipeline_smoke.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

import polars as pl

from acct_rz.pipeline import run_demo_pipeline


def test_run_demo_pipeline_outputs_split_key_columns(tmp_path):
    out_dir = tmp_path / "outputs"
    run_demo_pipeline(Path("data/demo/y.csv"), out_dir)

    step1 = pl.read_parquet(out_dir / "step1_blacklist.parquet")

    assert {"PID", "ID", "key_type", "key_value"}.issubset(set(step1.columns))
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_pipeline_smoke.py::test_run_demo_pipeline_outputs_split_key_columns`
Expected: FAIL because the current batch outputs do not guarantee split key columns.

**Step 3: Write minimal implementation**

```python
def run_demo_pipeline(input_path: Path, out_dir: Path) -> None:
    ...
```

Build:

- historical query snapshot from history data
- event fact from history data
- batch outputs through the same lookup functions used by query mode

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_pipeline_smoke.py::test_run_demo_pipeline_outputs_split_key_columns`
Expected: PASS

**Step 5: Commit**

```bash
git add src/acct_rz/pipeline.py src/acct_rz/features_blacklist.py src/acct_rz/features_org_blacklist.py src/acct_rz/features_windows.py tests/test_pipeline_smoke.py
git commit -m "refactor: route batch outputs through query lookup flow"
```

### Task 9: Update CLI and docs for arbitrary query lookup

**Files:**
- Modify: `run_pipeline.py`
- Modify: `README.md`
- Modify: `TASK.md`
- Test: `tests/test_readme.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_readme_mentions_query_lookup_entrypoint():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "lookup_all_steps" in text
    assert "run_pipeline.py" in text
```

**Step 2: Run test to verify it fails**

Run: `conda run -n dl_new python -m pytest -q tests/test_readme.py::test_readme_mentions_query_lookup_entrypoint`
Expected: FAIL because docs do not mention the new lookup entrypoint yet.

**Step 3: Write minimal implementation**

Update docs so they explain:

- batch generation command
- query lookup entrypoint
- required query input columns
- split-key output behavior

If `run_pipeline.py` gains a query mode, keep batch mode as default.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q tests/test_readme.py::test_readme_mentions_query_lookup_entrypoint`
Expected: PASS

**Step 5: Commit**

```bash
git add run_pipeline.py README.md TASK.md tests/test_readme.py
git commit -m "docs: add query lookup usage guidance"
```

### Task 10: Run full regression suite

**Files:**
- No file changes required unless a failing test exposes a defect.

**Step 1: Write the failing test**

No new test file. Use the full existing suite as the regression gate.

**Step 2: Run test to verify current status**

Run: `conda run -n dl_new python -m pytest -q`
Expected: if any tests fail, fix the minimal defect before proceeding.

**Step 3: Write minimal implementation**

Only apply the smallest code or test correction required to make the full suite pass.

**Step 4: Run test to verify it passes**

Run: `conda run -n dl_new python -m pytest -q`
Expected: PASS

**Step 5: Commit**

```bash
git add .
git commit -m "test: verify query lookup refactor end to end"
```

## Notes

- Keep `y.csv` strictly as the historical default-event source.
- External query rows do not need to exist in historical applications.
- For unmatched query keys, preserve the query row and emit zero-count/null-date results.
- Do not remove `key_value`; add `PID` and `ID` alongside it.
- Keep `step3` long-form by default.
