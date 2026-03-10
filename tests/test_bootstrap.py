from pathlib import Path


def test_package_layout_exists() -> None:
    assert Path("pyproject.toml").exists()
    assert Path("src/acct_rz/__init__.py").exists()
