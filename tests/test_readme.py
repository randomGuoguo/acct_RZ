from pathlib import Path


def test_readme_mentions_test_and_pipeline_commands() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    assert "python -m pytest -q" in text
    assert "run_demo_pipeline" in text
    assert "lookup_all_steps" in text
    assert "run_pipeline.py" in text
