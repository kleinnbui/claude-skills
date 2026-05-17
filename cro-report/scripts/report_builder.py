"""Inject CRO data JSON into HTML template → write standalone report file."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "report.html"
REPORTS_DIR = SKILL_DIR / "reports"


def _slug(s: str) -> str:
    s = (s or "report").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "report"


def build(profile_name: str, data: dict, client_name: str = "",
          output_path: str | None = None) -> Path:
    """Build single-file HTML report. Returns absolute Path.

    If output_path is given, write to exactly that file (overwrites).
    Otherwise write to reports/{slug}-{timestamp}.html.
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    fetched = data.get("meta", {}).get("fetched_at", "")
    try:
        fetched_human = datetime.fromisoformat(fetched.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        fetched_human = fetched

    dr = data.get("meta", {}).get("date_range", {})
    date_range_label = f"{dr.get('start', '?')} → {dr.get('end', '?')}"
    if dr.get("preset") and dr["preset"] != "custom":
        date_range_label += f" ({dr['preset'].replace('_', ' ')})"

    property_id = str(data.get("meta", {}).get("property_id", ""))
    client_display = client_name or profile_name

    data_json = json.dumps(data, ensure_ascii=False)
    # Escape </script> to prevent breaking the inline JSON script tag
    data_json_safe = data_json.replace("</", "<\\/")

    html = (template
            .replace("__CRO_DATA__", data_json_safe)
            .replace("__CLIENT_NAME__", _html_escape(client_display))
            .replace("__GENERATED_AT__", _html_escape(fetched_human))
            .replace("__DATE_RANGE__", _html_escape(date_range_label))
            .replace("__PROPERTY_ID__", _html_escape(property_id)))

    if output_path:
        out_path = Path(output_path).expanduser().absolute()
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        REPORTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M")
        out_path = REPORTS_DIR / f"{_slug(profile_name)}-{ts}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def _html_escape(s: str) -> str:
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))
