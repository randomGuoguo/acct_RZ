# Ydata Default Feature Products Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an offline-first Polars pipeline that normalizes raw Ydata application rows into reusable default-event facts and derives `step1-step4` feature products from that shared event timeline.

**Architecture:** Create a small Python package under `src/acct_rz/` with pure transformation functions for normalization, key expansion, event fact generation, and feature derivation. Drive the work test-first with tiny deterministic fixtures, then add one end-to-end pipeline entrypoint that reads `data/demo/y.csv` and writes product outputs.

**Tech Stack:** Python 3, Polars, pytest

---

### Task 1: Bootstrap the project layout

**Files:**
- Create: `pyproject.toml`
- Create: `src/acct_rz/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_package_layout_exists():
    assert Path("pyproject.toml").exists()
    assert Path("src/acct_rz/__init__.py").exists()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_bootstrap.py`
Expected: FAIL because the files do not exist yet.

**Step 3: Write minimal implementation**

```toml
[project]
name = "acct-rz"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["polars>=1.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
```

```python
"""acct_rz package."""
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_bootstrap.py`
Expected: PASS

**Step 5: Commit**

Run:

```bash
git add pyproject.toml src/acct_rz/__init__.py tests/test_bootstrap.py tests/__init__.py
git commit -m "chore: bootstrap acct_rz package"
```

Expected: commit succeeds after the repository has been initialized. If this workspace is still not a git repository, run `git init` first.

### Task 2: Add raw-row normalization and effective-date logic

**Files:**
- Create: `src/acct_rz/normalize.py`
- Create: `tests/test_normalize.py`

**Step 1: Write the failing test**

```python
import polars as pl
from acct_rz.normalize import build_application_base


def test_build_application_base_applies_default_rules():
    df = pl.DataFrame(
        {
            "PID": ["p1", "p2", "p3"],
            "ID": ["i1", "i2", "i3"],
            "app_dt": ["20240310", "20240310", "20240310"],
            "target": [1, 0, -2],
            "mob": ["6", "", "9"],
            "Org_class_new": ["Bank", "Bank", "Rate24"],
            "Org_new": ["A", "B", "C"],
            "perf_type": ["dpd", "fpd", "dpd"],
            "threshold_dpd": ["30", "30", "60"],
            "channel_new": ["api", "api", "h5"],
        }
    )

    result = build_application_base(df)

    assert result["mob_filled"].to_list() == [6, 6, 9]
    assert result["is_default"].to_list() == [1, 0, 0]
    assert result["event_dt"].dt.strftime("%Y-%m-%d").to_list() == [
        "2024-09-10",
        None,
        None,
    ]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_normalize.py::test_build_application_base_applies_default_rules`
Expected: FAIL with import or function-not-found error.

**Step 3: Write minimal implementation**

```python
import polars as pl


def build_application_base(df: pl.DataFrame) -> pl.DataFrame:
    app_date = pl.col("app_dt").str.strptime(pl.Date, "%Y%m%d", strict=False)
    mob_raw = pl.col("mob").cast(pl.Utf8).str.strip_chars()
    mob_filled = (
        pl.when(mob_raw.is_null() | (mob_raw == ""))
        .then(pl.lit(6))
        .otherwise(mob_raw.cast(pl.Int64, strict=False))
        .fill_null(6)
        .alias("mob_filled")
    )
    is_default = (pl.col("target") == 1).cast(pl.Int8).alias("is_default")

    return (
        df.with_columns(app_date.alias("app_dt_date"))
        .with_columns(mob_filled, is_default)
        .with_columns(
            pl.when(pl.col("is_default") == 1)
            .then(pl.col("app_dt_date").dt.offset_by(pl.format("{}mo", pl.col("mob_filled"))))
            .otherwise(pl.lit(None, dtype=pl.Date))
            .alias("event_dt")
        )
    )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_normalize.py::test_build_application_base_applies_default_rules`
Expected: PASS

**Step 5: Commit**

Run:

```bash
git add src/acct_rz/normalize.py tests/test_normalize.py
git commit -m "feat: normalize applications and event dates"
```

### Task 3: Add key expansion and default-event fact generation

**Files:**
- Create: `src/acct_rz/keys.py`
- Create: `src/acct_rz/events.py`
- Create: `tests/test_events.py`

**Step 1: Write the failing test**

```python
import polars as pl
from acct_rz.events import build_default_event_key_fact


def test_build_default_event_key_fact_expands_only_legal_keys():
    df = pl.DataFrame(
        {
            "PID": ["p1", None],
            "ID": ["i1", "i2"],
            "app_dt": ["20240310", "20240310"],
            "target": [1, 1],
            "mob": ["6", ""],
            "Org_class_new": ["Bank", "Rate24"],
            "Org_new": ["A", "B"],
            "perf_type": ["dpd", "fpd"],
            "threshold_dpd": ["30", "60"],
            "channel_new": ["api", "h5"],
        }
    )

    result = build_default_event_key_fact(df)
    pairs = set(zip(result["key_type"].to_list(), result["key_value"].to_list()))

    assert ("pid_id", "p1|i1") in pairs
    assert ("id", "i1") in pairs
    assert ("pid", "p1") in pairs
    assert ("pid_id", "None|i2") not in pairs
    assert ("id", "i2") in pairs
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_events.py::test_build_default_event_key_fact_expands_only_legal_keys`
Expected: FAIL because the event builder does not exist yet.

**Step 3: Write minimal implementation**

```python
import polars as pl
from acct_rz.normalize import build_application_base


def expand_keys(df: pl.DataFrame) -> pl.DataFrame:
    pid_id = df.filter(pl.col("PID").is_not_null() & pl.col("ID").is_not_null()).select(
        pl.all(), pl.lit("pid_id").alias("key_type"), pl.concat_str(["PID", "ID"], separator="|").alias("key_value")
    )
    id_only = df.filter(pl.col("ID").is_not_null()).select(
        pl.all(), pl.lit("id").alias("key_type"), pl.col("ID").alias("key_value")
    )
    pid_only = df.filter(pl.col("PID").is_not_null()).select(
        pl.all(), pl.lit("pid").alias("key_type"), pl.col("PID").alias("key_value")
    )
    return pl.concat([pid_id, id_only, pid_only], how="vertical")


def build_default_event_key_fact(df: pl.DataFrame) -> pl.DataFrame:
    base = build_application_base(df)
    defaults = base.filter(pl.col("is_default") == 1)
    return expand_keys(defaults)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_events.py::test_build_default_event_key_fact_expands_only_legal_keys`
Expected: PASS

**Step 5: Commit**

Run:

```bash
git add src/acct_rz/keys.py src/acct_rz/events.py tests/test_events.py
git commit -m "feat: add key expansion and default event facts"
```

### Task 4: Implement step1 and step2 as-of-date blacklist features

**Files:**
- Create: `src/acct_rz/features_blacklist.py`
- Create: `tests/test_features_blacklist.py`

**Step 1: Write the failing test**

```python
import polars as pl
from acct_rz.features_blacklist import build_blacklist_asof_features


def test_build_blacklist_asof_features_tracks_first_and_latest_hits():
    df = pl.DataFrame(
        {
            "PID": ["p1", "p1", "p1"],
            "ID": ["i1", "i1", "i1"],
            "app_dt": ["20240310", "20241001", "20250101"],
            "target": [1, 0, 0],
            "mob": ["6", "", ""],
            "Org_class_new": ["Bank", "Bank", "Bank"],
            "Org_new": ["A", "A", "A"],
            "perf_type": ["dpd", "dpd", "dpd"],
            "threshold_dpd": ["30", "30", "30"],
            "channel_new": ["api", "api", "api"],
        }
    )

    result = build_blacklist_asof_features(df).filter(pl.col("key_type") == "pid_id").sort("app_dt")

    assert result["black_hit_ever"].to_list() == [0, 1, 1]
    assert result["hit_event_cnt_asof_dt"].to_list() == [0, 1, 1]
    assert result["first_default_event_dt"].dt.strftime("%Y-%m-%d").to_list() == [None, "2024-09-10", "2024-09-10"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_features_blacklist.py::test_build_blacklist_asof_features_tracks_first_and_latest_hits`
Expected: FAIL because the feature builder does not exist yet.

**Step 3: Write minimal implementation**

```python
import polars as pl
from acct_rz.events import build_default_event_key_fact
from acct_rz.keys import expand_keys
from acct_rz.normalize import build_application_base


def build_blacklist_asof_features(df: pl.DataFrame) -> pl.DataFrame:
    apps = expand_keys(build_application_base(df)).rename({"app_dt_date": "app_dt"})
    events = build_default_event_key_fact(df).select("key_type", "key_value", "event_dt")
    joined = apps.join(events, on=["key_type", "key_value"], how="left")
    matched = joined.filter(pl.col("event_dt").is_null() | (pl.col("event_dt") <= pl.col("app_dt")))
    return (
        matched.group_by("app_dt", "key_type", "key_value")
        .agg(
            (pl.col("event_dt").is_not_null().sum() > 0).cast(pl.Int8).alias("black_hit_ever"),
            pl.col("event_dt").drop_nulls().min().alias("first_default_event_dt"),
            pl.col("event_dt").drop_nulls().max().alias("latest_default_event_dt"),
            pl.col("event_dt").is_not_null().sum().alias("hit_event_cnt_asof_dt"),
        )
        .sort("app_dt", "key_type", "key_value")
    )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_features_blacklist.py::test_build_blacklist_asof_features_tracks_first_and_latest_hits`
Expected: PASS

**Step 5: Commit**

Run:

```bash
git add src/acct_rz/features_blacklist.py tests/test_features_blacklist.py
git commit -m "feat: add as-of blacklist features"
```

### Task 5: Implement step3 org-class blacklist features

**Files:**
- Create: `src/acct_rz/features_org_blacklist.py`
- Create: `tests/test_features_org_blacklist.py`

**Step 1: Write the failing test**

```python
import polars as pl
from acct_rz.features_org_blacklist import build_org_class_blacklist_features


def test_build_org_class_blacklist_features_keeps_org_class_separate():
    df = pl.DataFrame(
        {
            "PID": ["p1", "p1", "p1"],
            "ID": ["i1", "i1", "i1"],
            "app_dt": ["20240310", "20241001", "20241001"],
            "target": [1, 0, 0],
            "mob": ["6", "", ""],
            "Org_class_new": ["Bank", "Bank", "Rate24"],
            "Org_new": ["A", "A", "B"],
            "perf_type": ["dpd", "dpd", "dpd"],
            "threshold_dpd": ["30", "30", "30"],
            "channel_new": ["api", "api", "api"],
        }
    )

    result = build_org_class_blacklist_features(df).filter(pl.col("key_type") == "pid_id")
    bank_hit = result.filter(pl.col("org_class") == "Bank")["black_hit_ever_by_org_class"].max()
    rate24_hit = result.filter(pl.col("org_class") == "Rate24")["black_hit_ever_by_org_class"].max()

    assert bank_hit == 1
    assert rate24_hit == 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_features_org_blacklist.py::test_build_org_class_blacklist_features_keeps_org_class_separate`
Expected: FAIL because the grouped feature builder does not exist yet.

**Step 3: Write minimal implementation**

```python
import polars as pl
from acct_rz.events import build_default_event_key_fact
from acct_rz.keys import expand_keys
from acct_rz.normalize import build_application_base


def build_org_class_blacklist_features(df: pl.DataFrame) -> pl.DataFrame:
    apps = expand_keys(build_application_base(df)).rename({"app_dt_date": "app_dt"})
    events = build_default_event_key_fact(df).select("key_type", "key_value", "event_dt", pl.col("Org_class_new").alias("org_class"))
    joined = apps.join(events, on=["key_type", "key_value"], how="left")
    matched = joined.filter(pl.col("event_dt").is_null() | (pl.col("event_dt") <= pl.col("app_dt")))
    return (
        matched.group_by("app_dt", "key_type", "key_value", "org_class")
        .agg(
            (pl.col("event_dt").is_not_null().sum() > 0).cast(pl.Int8).alias("black_hit_ever_by_org_class"),
            pl.col("event_dt").drop_nulls().min().alias("first_default_event_dt_by_org_class"),
        )
    )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_features_org_blacklist.py::test_build_org_class_blacklist_features_keeps_org_class_separate`
Expected: PASS

**Step 5: Commit**

Run:

```bash
git add src/acct_rz/features_org_blacklist.py tests/test_features_org_blacklist.py
git commit -m "feat: add org-class blacklist features"
```

### Task 6: Implement step4 rolling-window default count features

**Files:**
- Create: `src/acct_rz/features_windows.py`
- Create: `tests/test_features_windows.py`

**Step 1: Write the failing test**

```python
import polars as pl
from acct_rz.features_windows import build_window_count_features


def test_build_window_count_features_uses_event_date_boundaries():
    df = pl.DataFrame(
        {
            "PID": ["p1", "p1", "p1", "p1"],
            "ID": ["i1", "i1", "i1", "i1"],
            "app_dt": ["20240101", "20240401", "20240701", "20241015"],
            "target": [1, 1, 0, 0],
            "mob": ["3", "3", "", ""],
            "Org_class_new": ["Bank", "Rate24", "Bank", "Bank"],
            "Org_new": ["A", "B", "A", "A"],
            "perf_type": ["dpd", "fpd", "dpd", "dpd"],
            "threshold_dpd": ["30", "30", "30", "30"],
            "channel_new": ["api", "api", "api", "api"],
        }
    )

    result = build_window_count_features(df).filter(
        (pl.col("key_type") == "pid_id") & (pl.col("app_dt").dt.strftime("%Y-%m-%d") == "2024-10-15")
    )

    assert result["default_cnt_3m"].item() == 1
    assert result["default_cnt_12m"].item() == 2
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_features_windows.py::test_build_window_count_features_uses_event_date_boundaries`
Expected: FAIL because the window feature builder does not exist yet.

**Step 3: Write minimal implementation**

```python
import polars as pl
from acct_rz.events import build_default_event_key_fact
from acct_rz.keys import expand_keys
from acct_rz.normalize import build_application_base


def build_window_count_features(df: pl.DataFrame) -> pl.DataFrame:
    apps = expand_keys(build_application_base(df)).rename({"app_dt_date": "app_dt"})
    events = build_default_event_key_fact(df).select("key_type", "key_value", "event_dt", "Org_class_new", "perf_type")
    joined = apps.join(events, on=["key_type", "key_value"], how="left").filter(
        pl.col("event_dt").is_null() | (pl.col("event_dt") <= pl.col("app_dt"))
    )
    return (
        joined.group_by("app_dt", "key_type", "key_value")
        .agg(
            ((pl.col("event_dt") > pl.col("app_dt").dt.offset_by("-3mo")) & pl.col("event_dt").is_not_null()).sum().alias("default_cnt_3m"),
            ((pl.col("event_dt") > pl.col("app_dt").dt.offset_by("-6mo")) & pl.col("event_dt").is_not_null()).sum().alias("default_cnt_6m"),
            ((pl.col("event_dt") > pl.col("app_dt").dt.offset_by("-12mo")) & pl.col("event_dt").is_not_null()).sum().alias("default_cnt_12m"),
        )
    )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_features_windows.py::test_build_window_count_features_uses_event_date_boundaries`
Expected: PASS

**Step 5: Commit**

Run:

```bash
git add src/acct_rz/features_windows.py tests/test_features_windows.py
git commit -m "feat: add rolling default count features"
```

### Task 7: Add a single offline pipeline entrypoint and smoke test

**Files:**
- Create: `src/acct_rz/pipeline.py`
- Create: `tests/test_pipeline_smoke.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

import polars as pl
from acct_rz.pipeline import run_demo_pipeline


def test_run_demo_pipeline_writes_outputs(tmp_path):
    out_dir = tmp_path / "outputs"
    run_demo_pipeline(Path("data/demo/y.csv"), out_dir)

    assert (out_dir / "step1_blacklist.parquet").exists()
    assert (out_dir / "step2_traceback.parquet").exists()
    assert (out_dir / "step3_org_blacklist.parquet").exists()
    assert (out_dir / "step4_window_counts.parquet").exists()

    step1 = pl.read_parquet(out_dir / "step1_blacklist.parquet")
    assert {"app_dt", "key_type", "key_value", "black_hit_ever"}.issubset(set(step1.columns))
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_pipeline_smoke.py::test_run_demo_pipeline_writes_outputs`
Expected: FAIL because the pipeline entrypoint does not exist yet.

**Step 3: Write minimal implementation**

```python
from pathlib import Path

import polars as pl

from acct_rz.features_blacklist import build_blacklist_asof_features
from acct_rz.features_org_blacklist import build_org_class_blacklist_features
from acct_rz.features_windows import build_window_count_features


def run_demo_pipeline(input_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pl.read_csv(input_path)

    blacklist = build_blacklist_asof_features(df)
    blacklist.write_parquet(out_dir / "step1_blacklist.parquet")
    blacklist.write_parquet(out_dir / "step2_traceback.parquet")
    build_org_class_blacklist_features(df).write_parquet(out_dir / "step3_org_blacklist.parquet")
    build_window_count_features(df).write_parquet(out_dir / "step4_window_counts.parquet")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_pipeline_smoke.py::test_run_demo_pipeline_writes_outputs`
Expected: PASS

**Step 5: Commit**

Run:

```bash
git add src/acct_rz/pipeline.py tests/test_pipeline_smoke.py
git commit -m "feat: add offline pipeline entrypoint"
```

### Task 8: Run the full test suite and document the execution commands

**Files:**
- Modify: `README.md`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_readme_mentions_test_and_pipeline_commands():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "python -m pytest -q" in text
    assert "run_demo_pipeline" in text
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_readme.py`
Expected: FAIL because `README.md` does not exist or lacks the required commands.

**Step 3: Write minimal implementation**

```markdown
# acct_RZ

## Test

`python -m pytest -q`

## Demo pipeline

Call `run_demo_pipeline(Path("data/demo/y.csv"), out_dir)` from `src/acct_rz/pipeline.py`.
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_readme.py`
Expected: PASS

Then run:

```bash
python -m pytest -q
```

Expected: all tests PASS.

**Step 5: Commit**

Run:

```bash
git add README.md tests/test_readme.py
git commit -m "docs: add usage and validation commands"
```

## Notes

- If the workspace is still not a git repository, initialize it before the first commit:

```bash
git init
```

- Keep functions small and pure.
- Put the business rules in docstrings, especially the `event_dt` and non-default target handling.
- Use tiny hand-built DataFrames in tests instead of sampling from the demo CSV.
