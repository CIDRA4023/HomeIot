import marimo

__generated_with = "0.11.23"
app = marimo.App(width="full")


@app.cell
def _():
    # marimo cell 1
    import os
    import duckdb
    import pandas as pd
    import marimo as mo

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    default_duckdb_path = os.path.join(repo_root, "data", "duckdb", "home_energy.duckdb")
    env_duckdb_path = os.getenv("DUCKDB_PATH")
    if env_duckdb_path and os.path.exists(env_duckdb_path):
        duckdb_path = env_duckdb_path
    elif os.path.exists(default_duckdb_path):
        duckdb_path = default_duckdb_path
    else:
        duckdb_path = env_duckdb_path or default_duckdb_path
    con = duckdb.connect(duckdb_path, read_only=True)


    return con, duckdb, duckdb_path, mo, os, pd


if __name__ == "__main__":
    app.run()
