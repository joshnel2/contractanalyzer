"""Seed script — loads default_preferences.json into PostgreSQL.

Usage:
    python data/seed_preferences.py

Requires DATABASE_URL in .env or environment.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core.database import init_db
from core.models import AttorneyPreferences
from core.table_storage import StrappedTableStorage


def main() -> None:
    init_db()

    data_file = Path(__file__).parent / "default_preferences.json"
    data = json.loads(data_file.read_text())

    storage = StrappedTableStorage()

    print("Seeding firm-wide defaults ...")
    storage.upsert_firm_defaults(data["firm_defaults"])
    print("  Done.")

    for attorney in data.get("sample_attorneys", []):
        email = attorney["attorney_email"]
        print(f"Seeding preferences for {email} ...")
        prefs = AttorneyPreferences(**attorney)
        storage.upsert_preferences(prefs)
        print(f"  Done: {prefs.display_name}")

    print(f"\nSeeded {len(data.get('sample_attorneys', []))} profiles.")


if __name__ == "__main__":
    main()
