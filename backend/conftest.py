"""Makes `pytest tests/ -q` work from the backend/ directory.

pytest only puts each test module's own directory (tests/) on sys.path, so
without this the `app` package isn't importable unless you invoke pytest as
`python -m pytest`. An empty conftest.py at the project root is enough —
pytest prepends its directory to sys.path.
"""
