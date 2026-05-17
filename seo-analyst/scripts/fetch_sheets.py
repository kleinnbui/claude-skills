"""Load URL grouping data from Google Sheets via gspread."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config, credentials_path
from auth import load_credentials

import gspread


def load_url_groups(profile: str | None = None) -> list[dict]:
    cfg = load_config(profile)
    creds = load_credentials(credentials_path(profile))
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(cfg["url_groups_sheet_id"]).worksheet(
        cfg.get("url_groups_worksheet", "Sheet1")
    )
    return ws.get_all_records()


if __name__ == "__main__":
    print(json.dumps(load_url_groups(), ensure_ascii=False))
