"""Fetch data from Google Search Console API."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config, credentials_path
from auth import load_credentials

from googleapiclient.discovery import build


def _service(profile: str | None = None):
    creds = load_credentials(credentials_path(profile))
    return build("searchconsole", "v1", credentials=creds)


def _query(body: dict, profile: str | None = None) -> list[dict]:
    cfg = load_config(profile)
    resp = _service(profile).searchanalytics().query(
        siteUrl=cfg["gsc_site_url"], body=body
    ).execute()
    return resp.get("rows", [])


def by_page(start: str, end: str, limit: int = 25000, profile: str | None = None) -> list[dict]:
    rows = _query({"startDate": start, "endDate": end, "dimensions": ["page"], "rowLimit": limit}, profile)
    return [
        {
            "page": r["keys"][0],
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"], 4),
            "position": round(r["position"], 2),
        }
        for r in rows
    ]


def by_query(start: str, end: str, limit: int = 25000, profile: str | None = None) -> list[dict]:
    rows = _query({
        "startDate": start, "endDate": end,
        "dimensions": ["query", "page"], "rowLimit": limit,
    }, profile)
    return [
        {
            "query": r["keys"][0],
            "page": r["keys"][1],
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"], 4),
            "position": round(r["position"], 2),
        }
        for r in rows
    ]


def by_date(start: str, end: str, profile: str | None = None) -> list[dict]:
    rows = _query({"startDate": start, "endDate": end, "dimensions": ["date"]}, profile)
    return sorted(
        [
            {
                "date": r["keys"][0],
                "clicks": int(r["clicks"]),
                "impressions": int(r["impressions"]),
                "ctr": round(r["ctr"], 4),
                "position": round(r["position"], 2),
            }
            for r in rows
        ],
        key=lambda x: x["date"],
    )


def by_device(start: str, end: str, profile: str | None = None) -> list[dict]:
    rows = _query({"startDate": start, "endDate": end, "dimensions": ["device"]}, profile)
    return [
        {
            "device": r["keys"][0],
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"], 4),
            "position": round(r["position"], 2),
        }
        for r in rows
    ]


def by_country(start: str, end: str, limit: int = 20, profile: str | None = None) -> list[dict]:
    rows = _query({"startDate": start, "endDate": end, "dimensions": ["country"], "rowLimit": limit}, profile)
    return sorted(
        [
            {
                "country": r["keys"][0],
                "clicks": int(r["clicks"]),
                "impressions": int(r["impressions"]),
                "ctr": round(r["ctr"], 4),
                "position": round(r["position"], 2),
            }
            for r in rows
        ],
        key=lambda x: -x["clicks"],
    )


def by_query_for_page(start: str, end: str, page_url: str, limit: int = 500, profile: str | None = None) -> list[dict]:
    """Get all queries driving traffic to a specific page URL."""
    rows = _query(
        {
            "startDate": start,
            "endDate": end,
            "dimensions": ["query"],
            "dimensionFilterGroups": [
                {
                    "filters": [
                        {
                            "dimension": "page",
                            "operator": "equals",
                            "expression": page_url,
                        }
                    ]
                }
            ],
            "rowLimit": limit,
        },
        profile,
    )
    return sorted(
        [
            {
                "query": r["keys"][0],
                "clicks": int(r["clicks"]),
                "impressions": int(r["impressions"]),
                "ctr": round(r["ctr"], 4),
                "position": round(r["position"], 2),
            }
            for r in rows
        ],
        key=lambda x: -x["clicks"],
    )


if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "30d"
    today = date.today()
    days = int(period.rstrip("d")) if period.endswith("d") else 30
    start = (today - timedelta(days=days)).isoformat()
    end = today.isoformat()
    print(json.dumps({
        "pages": by_page(start, end),
        "queries": by_query(start, end),
        "by_date": by_date(start, end),
        "by_device": by_device(start, end),
        "by_country": by_country(start, end),
    }, ensure_ascii=False))
