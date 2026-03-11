import shutil
from pathlib import Path

import polars as pl

import run_pipeline


def test_main_uses_default_paths(monkeypatch, capsys) -> None:
    calls = []

    def fake_run_demo_pipeline(input_path: Path, output_path: Path) -> None:
        calls.append((input_path, output_path))

    monkeypatch.setattr(run_pipeline, "run_demo_pipeline", fake_run_demo_pipeline)

    result = run_pipeline.main([])
    out = capsys.readouterr().out

    assert result == 0
    assert calls == [(Path("data/demo/y.csv"), Path("data/result"))]
    assert "data/result" in out


def test_main_accepts_custom_paths(monkeypatch) -> None:
    calls = []

    def fake_run_demo_pipeline(input_path: Path, output_path: Path) -> None:
        calls.append((input_path, output_path))

    monkeypatch.setattr(run_pipeline, "run_demo_pipeline", fake_run_demo_pipeline)

    result = run_pipeline.main(["--input", "data/custom.csv", "--output", "data/out"])

    assert result == 0
    assert calls == [(Path("data/custom.csv"), Path("data/out"))]


def test_main_supports_query_mode(monkeypatch) -> None:
    calls = []

    def fake_read_csv(path: Path) -> pl.DataFrame:
        if Path(path) == Path("data/demo/y.csv"):
            return pl.DataFrame({"app_dt": ["20240101"], "PID": ["p1"], "ID": ["i1"], "target": [1], "mob": ["6"]})
        return pl.DataFrame({"app_dt": ["20241001"], "PID": ["p1"], "ID": ["i1"]})

    def fake_lookup_all_steps(history_df: pl.DataFrame, query_df: pl.DataFrame, step3_format: str = "long"):
        calls.append((history_df.shape, query_df.shape, step3_format))
        row = {"app_dt": [None], "key_type": ["pid_id"], "key_value": ["p1|i1"], "PID": ["p1"], "ID": ["i1"]}
        return {
            "blacklist_features": pl.DataFrame({**row, "ever_default_flag": [1], "default_cnt_36m": [1]}),
            "step1": pl.DataFrame({**row, "black_hit_ever": [1], "first_default_event_dt": [None]}),
            "step2": pl.DataFrame(
                {**row, "black_hit_ever": [1], "first_default_event_dt": [None], "latest_default_event_dt": [None], "hit_event_cnt_asof_dt": [1]}
            ),
            "step3": pl.DataFrame({**row, "org_class": ["Bank"], "black_hit_ever_by_org_class": [1], "first_default_event_dt_by_org_class": [None]}),
            "step4": pl.DataFrame(
                {
                    **row,
                    "default_cnt_3m": [0],
                    "default_cnt_6m": [0],
                    "default_cnt_12m": [0],
                    "default_cnt_3m_bank": [0],
                    "default_cnt_6m_bank": [0],
                    "default_cnt_3m_rate24": [0],
                    "default_cnt_3m_fpd": [0],
                    "default_cnt_3m_dpd": [0],
                }
            ),
        }

    monkeypatch.setattr(run_pipeline.pl, "read_csv", fake_read_csv)
    monkeypatch.setattr(run_pipeline, "lookup_all_steps", fake_lookup_all_steps)

    output_dir = Path("tests/.tmp_query_outputs")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    result = run_pipeline.main(
        ["--mode", "query", "--input", "data/demo/y.csv", "--query-input", "data/query.csv", "--output", str(output_dir)]
    )

    assert result == 0
    assert calls == [((1, 5), (1, 3), "long")]
    assert (output_dir / "blacklist_features.parquet").exists()
    assert (output_dir / "step1_blacklist.parquet").exists()
    shutil.rmtree(output_dir)
