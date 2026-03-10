from pathlib import Path

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
