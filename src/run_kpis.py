"""Run the SQL KPI scripts against the SQLite mart; save CSV outputs.

Usage:
    python -m src.run_kpis --db /tmp/pet_insurance.sqlite --out outputs/kpis
"""

from __future__ import annotations

import argparse
import glob
import os
import sqlite3

import pandas as pd


def run_kpis(db_path: str, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    sql_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql")
    paths = []
    con = sqlite3.connect(db_path)
    for sql_file in sorted(glob.glob(os.path.join(sql_dir, "kpi_*.sql"))):
        name = os.path.splitext(os.path.basename(sql_file))[0]
        with open(sql_file) as f:
            query = f.read()
        df = pd.read_sql_query(query, con)
        out = os.path.join(out_dir, f"{name}.csv")
        df.to_csv(out, index=False)
        paths.append(out)
        print(f"{name}: {len(df)} rows -> {out}")
    con.close()
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/tmp/pet_insurance.sqlite")
    ap.add_argument("--out", default="outputs/kpis")
    args = ap.parse_args()
    run_kpis(args.db, args.out)


if __name__ == "__main__":
    main()
