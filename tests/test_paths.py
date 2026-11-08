"""Smoke test: the path helpers resolve and the repo root is correct.

Kept deliberately network-free so CI (no GENESIS/Destatis access) stays green.
"""

from etl import paths


def test_repo_root_contains_pyproject():
    assert (paths.REPO_ROOT / "pyproject.toml").is_file()


def test_key_paths_are_under_repo_root():
    for p in (paths.CONFIG_DIR, paths.DATA_DIR, paths.DASHBOARD_DIR, paths.REPORTS_DIR):
        assert paths.REPO_ROOT in p.parents or p == paths.REPO_ROOT


def test_version_exposed():
    import etl

    assert etl.__version__
