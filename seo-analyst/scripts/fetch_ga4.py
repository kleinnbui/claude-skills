"""Fetch traffic data from GA4 Data API."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config, credentials_path
from auth import load_credentials

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest,
)


def _client(profile: str | None = None) -> BetaAnalyticsDataClient:
    creds = load_credentials(credentials_path(profile))
    return BetaAnalyticsDataClient(credentials=creds)


def _property(cfg: dict) -> str:
    return f"properties/{cfg['ga4_property_id']}"


def by_page(start: str, end: str, profile: str | None = None) -> list[dict]:
    cfg = load_config(profile)
    resp = _client(profile).run_report(RunReportRequest(
        property=_property(cfg),
        dimensions=[Dimension(name="pagePath"), Dimension(name="date")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="engagementRate"),
            Metric(name="engagedSessions"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=start, end_date=end)],
        limit=50000,
    ))
    rows = []
    for r in resp.rows:
        rows.append({
            "page": r.dimension_values[0].value,
            "date": r.dimension_values[1].value,
            "sessions": int(r.metric_values[0].value),
            "users": int(r.metric_values[1].value),
            "new_users": int(r.metric_values[2].value),
            "pageviews": int(r.metric_values[3].value),
            "bounce_rate": round(float(r.metric_values[4].value), 4),
            "engagement_rate": round(float(r.metric_values[5].value), 4),
            "engaged_sessions": int(r.metric_values[6].value),
            "avg_session_duration": round(float(r.metric_values[7].value), 1),
        })
    return rows


def by_channel(start: str, end: str, profile: str | None = None) -> list[dict]:
    cfg = load_config(profile)
    resp = _client(profile).run_report(RunReportRequest(
        property=_property(cfg),
        dimensions=[
            Dimension(name="sessionDefaultChannelGrouping"),
            Dimension(name="date"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
        ],
        date_ranges=[DateRange(start_date=start, end_date=end)],
        limit=5000,
    ))
    return [
        {
            "channel": r.dimension_values[0].value,
            "date": r.dimension_values[1].value,
            "sessions": int(r.metric_values[0].value),
            "users": int(r.metric_values[1].value),
            "new_users": int(r.metric_values[2].value),
        }
        for r in resp.rows
    ]


def by_date(start: str, end: str, profile: str | None = None) -> list[dict]:
    """Site-wide daily totals. Lightweight — for brief dashboard."""
    cfg = load_config(profile)
    resp = _client(profile).run_report(RunReportRequest(
        property=_property(cfg),
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="screenPageViews"),
            Metric(name="engagementRate"),
            Metric(name="engagedSessions"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=start, end_date=end)],
        limit=400,
    ))
    return sorted(
        [
            {
                "date": r.dimension_values[0].value,
                "sessions": int(r.metric_values[0].value),
                "users": int(r.metric_values[1].value),
                "new_users": int(r.metric_values[2].value),
                "pageviews": int(r.metric_values[3].value),
                "engagement_rate": round(float(r.metric_values[4].value), 4),
                "engaged_sessions": int(r.metric_values[5].value),
                "avg_session_duration": round(float(r.metric_values[6].value), 1),
            }
            for r in resp.rows
        ],
        key=lambda x: x["date"],
    )


def by_device(start: str, end: str, profile: str | None = None) -> list[dict]:
    cfg = load_config(profile)
    resp = _client(profile).run_report(RunReportRequest(
        property=_property(cfg),
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=start, end_date=end)],
        limit=10,
    ))
    return [
        {
            "device": r.dimension_values[0].value,
            "sessions": int(r.metric_values[0].value),
            "users": int(r.metric_values[1].value),
            "engagement_rate": round(float(r.metric_values[2].value), 4),
            "avg_session_duration": round(float(r.metric_values[3].value), 1),
        }
        for r in resp.rows
    ]


if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "30d"
    today = date.today()
    days = int(period.rstrip("d")) if period.endswith("d") else 30
    start = (today - timedelta(days=days)).isoformat()
    end = today.isoformat()
    print(json.dumps({
        "pages": by_page(start, end),
        "channels": by_channel(start, end),
        "devices": by_device(start, end),
    }, ensure_ascii=False))
