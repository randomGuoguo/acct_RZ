# Ydata Query Lookup Status

**Date:** 2026-03-10

## Current State

The query lookup refactor is implemented and passing tests.

- `y.csv` is used only as the historical default-event source.
- External query input supports arbitrary `app_dt` plus `PID`, `ID`, or `PID+ID`.
- Offline batch output and query mode share the same lookup logic.
- All outputs retain `key_type`, `key_value`, `PID`, and `ID`.
- All final output date columns are serialized as `YYYYMMDD` `i64`.
- Query input with numeric `app_dt` such as `20251006` is parsed correctly and no longer turns into far-future dates like `574150517`.

## Main Entry Points

- Batch CLI: `conda run -n dl_new python run_pipeline.py`
- Query CLI: `conda run -n dl_new python run_pipeline.py --mode query --input data/demo/y.csv --query-input data/demo/query.csv --output data/result`
- Python facade: `acct_rz.query_lookup.lookup_all_steps`

## Key Files

- `src/acct_rz/query_snapshot.py`
- `src/acct_rz/query_lookup.py`
- `src/acct_rz/pipeline.py`
- `src/acct_rz/features_blacklist.py`
- `src/acct_rz/features_org_blacklist.py`
- `src/acct_rz/features_windows.py`
- `run_pipeline.py`

## Output Contract

Shared output columns:

- `app_dt`
- `key_type`
- `key_value`
- `PID`
- `ID`

Date-related output columns are `i64` in `YYYYMMDD` format, for example:

- `app_dt = 20251006`
- `first_default_event_dt = 20240701`

Internal calculation still uses `Date` types for comparisons and rolling-window logic. Conversion to `i64` happens only on final outputs.

## Validation Status

Last verified with:

```powershell
conda run -n dl_new python -m pytest -q
```

Result at the time of update:

- `22 passed`

## Demo Data

- Historical input: `data/demo/y.csv`
- Query example: `data/demo/query.csv`
- Default batch output dir: `data/result`

## Notes For Next Session

- If you change output schema again, update both `README.md` and this status file.
- If query parsing changes, keep coverage in `tests/test_query_snapshot.py`.
- `TASK.md` contains older project notes and some garbled text; prefer this file plus `README.md` for current runnable state.
