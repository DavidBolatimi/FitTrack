"""Load CSVs into a local SQLite database (data/fittrack.db)."""
import sqlite3
import pandas as pd
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

def build(db_path: Path = DATA / "fittrack.db") -> Path:
    con = sqlite3.connect(db_path)
    pd.read_csv(DATA / "users.csv").to_sql("users", con, if_exists="replace", index=False)
    pd.read_csv(DATA / "events.csv.gz").to_sql("events", con, if_exists="replace", index=False)
    pd.read_csv(DATA / "subscriptions.csv").to_sql("subscriptions", con, if_exists="replace", index=False)
    con.executescript("""
        CREATE INDEX IF NOT EXISTS ix_events_user ON events(user_id);
        CREATE INDEX IF NOT EXISTS ix_events_name ON events(event_name);
    """)
    con.close()
    return db_path

if __name__ == "__main__":
    print("Built", build())
