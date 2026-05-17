"""Fetch CRO event data from GA4 Data API v1beta.

10 queries (all include `date` so report can re-aggregate by date client-side;
queries 5-10 also include `customEvent:cro_conversion_id` so lead-type filter
re-aggregates client-side):
  1. Timeline daily counts per CRO event
  2. Per-form success    (date + conversion_id + trigger_type)
  3. Per-form fail       (date + conversion_id + fail_reason)
  4. Per-form interactions (date + conversion_id + interaction)
  5. Journey patterns    (date + conversion_id + landing + submission + pages_visited)
  6. Device              (date + conversion_id + deviceCategory + operatingSystem + screenResolution)
  7. Geography           (date + conversion_id + region + city)
  8. Traffic source      (date + conversion_id + sessionSource + sessionMedium + sessionCampaignName)
  9. Time-of-day         (date + conversion_id + dayOfWeekName + hour)
 10. User segment        (date + conversion_id + newVsReturning + browser)

Custom event-scoped dimension naming in GA4 Data API v1beta:
  - Dimension: customEvent:<param_name>      e.g. customEvent:cro_conversion_id
  - Metric:    customEvent:<param_name>      e.g. customEvent:cro_elapsed_ms

These require the custom dimension/metric to be registered in GA4 Admin
(which /cro-setup does automatically via ga4_sync.py).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone


EVENT_SUCCESS = "conversion_success"
EVENT_FAILED = "conversion_attempt_failed"
EVENT_INTERACTION = "form_interaction"
ALL_EVENTS = [EVENT_SUCCESS, EVENT_FAILED, EVENT_INTERACTION]


def _client(creds):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    return BetaAnalyticsDataClient(credentials=creds)


def _property_path(property_id: str) -> str:
    pid = property_id.strip()
    return pid if pid.startswith("properties/") else f"properties/{pid}"


def _event_in_filter(event_names: list[str]):
    from google.analytics.data_v1beta.types import Filter, FilterExpression
    return FilterExpression(
        filter=Filter(
            field_name="eventName",
            in_list_filter=Filter.InListFilter(values=event_names),
        )
    )


def _event_eq_filter(event_name: str):
    from google.analytics.data_v1beta.types import Filter, FilterExpression
    return FilterExpression(
        filter=Filter(
            field_name="eventName",
            string_filter=Filter.StringFilter(value=event_name),
        )
    )


def _short_error(e: Exception) -> str:
    msg = str(e)
    first = msg.split("[reason:", 1)[0].strip()
    import re
    url_match = re.search(r"https://console\.developers\.google\.com/apis/api/[^\s\]\"]+", msg)
    if url_match:
        return f"{first}\n  → Activate: {url_match.group(0)}"
    return first


def _run(client, property_id: str, *, dimensions: list[str], metrics: list[str],
         start_date: str, end_date: str, filter_expr=None, limit: int = 100_000) -> list[dict]:
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, RunReportRequest,
    )
    req = RunReportRequest(
        property=_property_path(property_id),
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=filter_expr,
        limit=limit,
    )
    try:
        resp = client.run_report(req)
    except Exception as e:
        return [{"_error": _short_error(e)}]

    rows = []
    for r in resp.rows:
        row = {}
        for i, dh in enumerate(resp.dimension_headers):
            row[dh.name] = r.dimension_values[i].value
        for i, mh in enumerate(resp.metric_headers):
            v = r.metric_values[i].value
            try:
                row[mh.name] = float(v) if "." in v else int(v)
            except (ValueError, TypeError):
                row[mh.name] = 0
        rows.append(row)
    return rows


def resolve_date_range(preset: str | None, start: str | None, end: str | None) -> tuple[str, str, str]:
    if start and end:
        return start, end, "custom"

    preset = preset or "last_30_days"
    today = datetime.now(timezone.utc).date()

    if preset == "last_7_days":
        from datetime import timedelta
        return str(today - timedelta(days=7)), str(today), preset
    if preset == "last_30_days":
        from datetime import timedelta
        return str(today - timedelta(days=30)), str(today), preset
    if preset == "last_90_days":
        from datetime import timedelta
        return str(today - timedelta(days=90)), str(today), preset

    raise ValueError(f"Unknown date preset: {preset}")


def _norm_date(d: str) -> str:
    """GA4 returns dates as YYYYMMDD; normalise to YYYY-MM-DD."""
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 and d.isdigit() else d


def fetch_all(creds, property_id: str, *, date_preset: str | None = None,
              start_date: str | None = None, end_date: str | None = None) -> dict:
    start, end, preset = resolve_date_range(date_preset, start_date, end_date)
    client = _client(creds)
    t0 = time.time()
    warnings: list[str] = []

    q1 = _run(client, property_id,
              dimensions=["date", "eventName"],
              metrics=["eventCount"],
              start_date=start, end_date=end,
              filter_expr=_event_in_filter(ALL_EVENTS))
    q1, q1_err = _split_errors(q1)
    if q1_err:
        warnings.append(f"Timeline query: {q1_err}")

    q2 = _run(client, property_id,
              dimensions=["date", "customEvent:cro_conversion_id", "customEvent:cro_trigger_type",
                          "customEvent:cro_detection"],
              metrics=["eventCount", "customEvent:cro_elapsed_ms", "customEvent:cro_journey_length",
                       "customEvent:cro_session_ms"],
              start_date=start, end_date=end,
              filter_expr=_event_eq_filter(EVENT_SUCCESS))
    q2, q2_err = _split_errors(q2)
    if q2_err:
        warnings.append(f"Per-form success query: {q2_err}")

    q3 = _run(client, property_id,
              dimensions=["date", "customEvent:cro_conversion_id", "customEvent:cro_fail_reason"],
              metrics=["eventCount"],
              start_date=start, end_date=end,
              filter_expr=_event_eq_filter(EVENT_FAILED))
    q3, q3_err = _split_errors(q3)
    if q3_err:
        warnings.append(f"Per-form fail query: {q3_err}")

    q4 = _run(client, property_id,
              dimensions=["date", "customEvent:cro_conversion_id", "customEvent:cro_interaction"],
              metrics=["eventCount"],
              start_date=start, end_date=end,
              filter_expr=_event_eq_filter(EVENT_INTERACTION))
    q4, q4_err = _split_errors(q4)
    if q4_err:
        warnings.append(f"Per-form interaction query: {q4_err}")

    # Query 5: journey patterns (landing + middle pages + submission, per lead type)
    q5 = _run(client, property_id,
              dimensions=[
                  "date",
                  "customEvent:cro_conversion_id",
                  "customEvent:cro_landing_page",
                  "customEvent:cro_submission_page",
                  "customEvent:cro_pages_visited",
                  "customEvent:cro_thank_you_path",
              ],
              metrics=["eventCount", "customEvent:cro_journey_length"],
              start_date=start, end_date=end,
              filter_expr=_event_eq_filter(EVENT_SUCCESS))
    q5, q5_err = _split_errors(q5)
    if q5_err:
        warnings.append(f"Journey patterns query: {q5_err}")

    # Query 6: device / OS / screen resolution
    q6 = _run(client, property_id,
              dimensions=["date", "customEvent:cro_conversion_id",
                          "deviceCategory", "operatingSystem", "screenResolution"],
              metrics=["eventCount"],
              start_date=start, end_date=end,
              filter_expr=_event_eq_filter(EVENT_SUCCESS))
    q6, q6_err = _split_errors(q6)
    if q6_err:
        warnings.append(f"Device query: {q6_err}")

    # Query 7: geography (region + city)
    q7 = _run(client, property_id,
              dimensions=["date", "customEvent:cro_conversion_id", "region", "city"],
              metrics=["eventCount"],
              start_date=start, end_date=end,
              filter_expr=_event_eq_filter(EVENT_SUCCESS))
    q7, q7_err = _split_errors(q7)
    if q7_err:
        warnings.append(f"Geo query: {q7_err}")

    # Query 8: traffic source / medium / campaign / channel group
    q8 = _run(client, property_id,
              dimensions=["date", "customEvent:cro_conversion_id",
                          "sessionDefaultChannelGroup",
                          "sessionSource", "sessionMedium", "sessionCampaignName"],
              metrics=["eventCount"],
              start_date=start, end_date=end,
              filter_expr=_event_eq_filter(EVENT_SUCCESS))
    q8, q8_err = _split_errors(q8)
    if q8_err:
        warnings.append(f"Source query: {q8_err}")

    # Query 9: time-of-day (day-of-week × hour) → for heatmap
    q9 = _run(client, property_id,
              dimensions=["date", "customEvent:cro_conversion_id",
                          "dayOfWeekName", "hour"],
              metrics=["eventCount"],
              start_date=start, end_date=end,
              filter_expr=_event_eq_filter(EVENT_SUCCESS))
    q9, q9_err = _split_errors(q9)
    if q9_err:
        warnings.append(f"Time query: {q9_err}")

    # Query 10: user segment (new vs returning + browser)
    q10 = _run(client, property_id,
               dimensions=["date", "customEvent:cro_conversion_id",
                           "newVsReturning", "browser"],
               metrics=["eventCount"],
               start_date=start, end_date=end,
               filter_expr=_event_eq_filter(EVENT_SUCCESS))
    q10, q10_err = _split_errors(q10)
    if q10_err:
        warnings.append(f"User segment query: {q10_err}")

    # Query 11: total sessions + users — no event filter (full site traffic)
    # Used as funnel top-of-funnel denominator and for Site CR KPI.
    q11 = _run(client, property_id,
               dimensions=["date"],
               metrics=["sessions", "totalUsers", "newUsers"],
               start_date=start, end_date=end)
    q11, q11_err = _split_errors(q11)
    if q11_err:
        warnings.append(f"Sessions query: {q11_err}")

    # Query 12: sessions + users per channel group — used to compute CR% per channel.
    q12 = _run(client, property_id,
               dimensions=["date", "sessionDefaultChannelGroup"],
               metrics=["sessions", "totalUsers", "engagementRate", "averageSessionDuration"],
               start_date=start, end_date=end)
    q12, q12_err = _split_errors(q12)
    if q12_err:
        warnings.append(f"Channel sessions query: {q12_err}")

    # Query 13: sessions per landing page — joined with journey_daily for landing page CR
    q13 = _run(client, property_id,
               dimensions=["date", "landingPage"],
               metrics=["sessions", "totalUsers"],
               start_date=start, end_date=end)
    q13, q13_err = _split_errors(q13)
    if q13_err:
        warnings.append(f"Landing page sessions query: {q13_err}")

    # Query 14: sessions per device category — for CR% per device
    q14 = _run(client, property_id,
               dimensions=["date", "deviceCategory"],
               metrics=["sessions"],
               start_date=start, end_date=end)
    q14, q14_err = _split_errors(q14)
    if q14_err:
        warnings.append(f"Device sessions query: {q14_err}")

    # Query 15: sessions per new vs returning — for CR% per user type
    q15 = _run(client, property_id,
               dimensions=["date", "newVsReturning"],
               metrics=["sessions"],
               start_date=start, end_date=end)
    q15, q15_err = _split_errors(q15)
    if q15_err:
        warnings.append(f"Segment sessions query: {q15_err}")

    # Queries 16a/16b: previous period summary (same duration, immediately before)
    # Used for period-over-period KPI delta (±%)
    from datetime import timedelta as _td
    _start_dt = datetime.strptime(start, "%Y-%m-%d")
    _end_dt   = datetime.strptime(end, "%Y-%m-%d")
    _period_days = (_end_dt - _start_dt).days + 1
    _prev_end   = str((_start_dt - _td(days=1)).date())
    _prev_start = str((_start_dt - _td(days=_period_days)).date())

    q16a = _run(client, property_id,
                dimensions=[],
                metrics=["sessions", "totalUsers"],
                start_date=_prev_start, end_date=_prev_end)
    q16a, q16a_err = _split_errors(q16a)
    if q16a_err:
        warnings.append(f"Prev period sessions query: {q16a_err}")

    q16b = _run(client, property_id,
                dimensions=[],
                metrics=["eventCount"],
                start_date=_prev_start, end_date=_prev_end,
                filter_expr=_event_eq_filter(EVENT_SUCCESS))
    q16b, q16b_err = _split_errors(q16b)
    if q16b_err:
        warnings.append(f"Prev period conversions query: {q16b_err}")

    duration_ms = int((time.time() - t0) * 1000)

    aggregated = _shape_daily(q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12,
                              q13, q14, q15)
    aggregated["prev_summary"] = _prev_summary(q16a, q16b, _prev_start, _prev_end)
    aggregated["meta"] = {
        "property_id": property_id,
        "date_range": {"start": start, "end": end, "preset": preset},
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_ms": duration_ms,
        "warnings": warnings,
    }
    aggregated["summary"] = _summary_from_daily(aggregated)
    return aggregated


def _split_errors(rows: list[dict]) -> tuple[list[dict], str | None]:
    if rows and "_error" in rows[0]:
        return [], rows[0]["_error"]
    return rows, None


def _prev_summary(sess_rows: list[dict], conv_rows: list[dict],
                  prev_start: str, prev_end: str) -> dict:
    """Compute previous-period aggregate for KPI delta comparisons."""
    sessions  = int(sess_rows[0].get("sessions", 0))  if sess_rows else 0
    users     = int(sess_rows[0].get("totalUsers", 0)) if sess_rows else 0
    conv      = int(conv_rows[0].get("eventCount", 0)) if conv_rows else 0
    site_cr   = round(conv / sessions * 100, 2) if sessions else 0
    return {
        "period_start": prev_start,
        "period_end":   prev_end,
        "sessions":     sessions,
        "users":        users,
        "conversions":  conv,
        "site_cr_pct":  site_cr,
    }


def _shape_daily(timeline_rows, success_rows, fail_rows, interaction_rows,
                 journey_rows, device_rows, geo_rows, source_rows, time_rows,
                 segment_rows, session_rows=None, channel_session_rows=None,
                 landing_session_rows=None, device_session_rows=None,
                 segment_session_rows=None) -> dict:
    """Normalise raw GA4 rows into daily-row JSON the template aggregates client-side."""
    timeline_map: dict[str, dict] = {}
    for r in timeline_rows:
        d = _norm_date(r.get("date", ""))
        if not d:
            continue
        evt = r.get("eventName", "")
        cnt = int(r.get("eventCount", 0) or 0)
        bucket = timeline_map.setdefault(d, {
            "date": d,
            EVENT_SUCCESS: 0,
            EVENT_FAILED: 0,
            EVENT_INTERACTION: 0,
        })
        bucket[evt] = bucket.get(evt, 0) + cnt
    timeline = sorted(timeline_map.values(), key=lambda x: x["date"])

    per_form_daily = []
    for r in success_rows:
        per_form_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "trigger_type": r.get("customEvent:cro_trigger_type") or "",
            "detection": r.get("customEvent:cro_detection") or "",
            "success": int(r.get("eventCount", 0) or 0),
            "fail": 0,
            "interactions": 0,
            "elapsed_sum": float(r.get("customEvent:cro_elapsed_ms", 0) or 0),
            "session_ms_sum": float(r.get("customEvent:cro_session_ms", 0) or 0),
            "pages_sum": float(r.get("customEvent:cro_journey_length", 0) or 0),
        })
    for r in fail_rows:
        per_form_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "trigger_type": "",
            "detection": "",
            "success": 0,
            "fail": int(r.get("eventCount", 0) or 0),
            "interactions": 0,
            "elapsed_sum": 0,
            "session_ms_sum": 0,
            "pages_sum": 0,
        })
    for r in interaction_rows:
        per_form_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "trigger_type": "",
            "detection": "",
            "success": 0,
            "fail": 0,
            "interactions": int(r.get("eventCount", 0) or 0),
            "elapsed_sum": 0,
            "session_ms_sum": 0,
            "pages_sum": 0,
        })

    failures_daily = []
    for r in fail_rows:
        cnt = int(r.get("eventCount", 0) or 0)
        if cnt <= 0:
            continue
        failures_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "reason": r.get("customEvent:cro_fail_reason") or "(unknown)",
            "count": cnt,
        })

    interactions_daily = []
    for r in interaction_rows:
        cnt = int(r.get("eventCount", 0) or 0)
        if cnt <= 0:
            continue
        interactions_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "interaction": r.get("customEvent:cro_interaction") or "(unknown)",
            "count": cnt,
        })

    journey_daily = []
    for r in journey_rows:
        cnt = int(r.get("eventCount", 0) or 0)
        if cnt <= 0:
            continue
        journey_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "landing": r.get("customEvent:cro_landing_page") or "(direct)",
            "submission": r.get("customEvent:cro_submission_page") or "(direct)",
            "thank_you_path": r.get("customEvent:cro_thank_you_path") or "",
            "pages_visited": r.get("customEvent:cro_pages_visited") or "",
            "journey_length": int(r.get("customEvent:cro_journey_length", 0) or 0),
            "count": cnt,
        })

    device_daily = []
    for r in device_rows:
        cnt = int(r.get("eventCount", 0) or 0)
        if cnt <= 0:
            continue
        device_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "device": r.get("deviceCategory") or "(unknown)",
            "os": r.get("operatingSystem") or "(unknown)",
            "screen": r.get("screenResolution") or "(unknown)",
            "count": cnt,
        })

    geo_daily = []
    for r in geo_rows:
        cnt = int(r.get("eventCount", 0) or 0)
        if cnt <= 0:
            continue
        geo_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "region": r.get("region") or "(unknown)",
            "city": r.get("city") or "(unknown)",
            "count": cnt,
        })

    source_daily = []
    for r in source_rows:
        cnt = int(r.get("eventCount", 0) or 0)
        if cnt <= 0:
            continue
        source_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "channel_group": r.get("sessionDefaultChannelGroup") or "(other)",
            "source": r.get("sessionSource") or "(direct)",
            "medium": r.get("sessionMedium") or "(none)",
            "campaign": r.get("sessionCampaignName") or "(none)",
            "count": cnt,
        })

    channel_sessions_daily = []
    for r in (channel_session_rows or []):
        d = _norm_date(r.get("date", ""))
        if not d:
            continue
        channel_sessions_daily.append({
            "date": d,
            "channel_group": r.get("sessionDefaultChannelGroup") or "(other)",
            "sessions": int(r.get("sessions", 0) or 0),
            "users": int(r.get("totalUsers", 0) or 0),
            "engagement_rate": round(float(r.get("engagementRate", 0) or 0) * 100, 1),
            "avg_session_sec": round(float(r.get("averageSessionDuration", 0) or 0), 0),
        })

    time_daily = []
    for r in time_rows:
        cnt = int(r.get("eventCount", 0) or 0)
        if cnt <= 0:
            continue
        time_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "day_of_week": r.get("dayOfWeekName") or "(unknown)",
            "hour": int(r.get("hour", 0) or 0),
            "count": cnt,
        })

    segment_daily = []
    for r in segment_rows:
        cnt = int(r.get("eventCount", 0) or 0)
        if cnt <= 0:
            continue
        segment_daily.append({
            "date": _norm_date(r.get("date", "")),
            "conversion_id": r.get("customEvent:cro_conversion_id") or "(unnamed)",
            "user_type": r.get("newVsReturning") or "(unknown)",
            "browser": r.get("browser") or "(unknown)",
            "count": cnt,
        })

    sessions_daily = []
    for r in (session_rows or []):
        d = _norm_date(r.get("date", ""))
        if not d:
            continue
        sessions_daily.append({
            "date": d,
            "sessions": int(r.get("sessions", 0) or 0),
            "users": int(r.get("totalUsers", 0) or 0),
            "new_users": int(r.get("newUsers", 0) or 0),
        })

    landing_sessions_daily = []
    for r in (landing_session_rows or []):
        d = _norm_date(r.get("date", ""))
        if not d:
            continue
        landing_sessions_daily.append({
            "date": d,
            "landing_page": r.get("landingPage") or "/",
            "sessions": int(r.get("sessions", 0) or 0),
            "users": int(r.get("totalUsers", 0) or 0),
        })

    device_sessions_daily = []
    for r in (device_session_rows or []):
        d = _norm_date(r.get("date", ""))
        if not d:
            continue
        device_sessions_daily.append({
            "date": d,
            "device": r.get("deviceCategory") or "(unknown)",
            "sessions": int(r.get("sessions", 0) or 0),
        })

    segment_sessions_daily = []
    for r in (segment_session_rows or []):
        d = _norm_date(r.get("date", ""))
        if not d:
            continue
        segment_sessions_daily.append({
            "date": d,
            "user_type": r.get("newVsReturning") or "(unknown)",
            "sessions": int(r.get("sessions", 0) or 0),
        })

    return {
        "timeline": timeline,
        "per_form_daily": per_form_daily,
        "failures_daily": failures_daily,
        "interactions_daily": interactions_daily,
        "journey_daily": journey_daily,
        "device_daily": device_daily,
        "geo_daily": geo_daily,
        "source_daily": source_daily,
        "time_daily": time_daily,
        "segment_daily": segment_daily,
        "sessions_daily": sessions_daily,
        "channel_sessions_daily": channel_sessions_daily,
        "landing_sessions_daily": landing_sessions_daily,
        "device_sessions_daily": device_sessions_daily,
        "segment_sessions_daily": segment_sessions_daily,
    }


def _summary_from_daily(d: dict) -> dict:
    """Server-side summary for the full date range (template recomputes after filter)."""
    forms: dict[str, dict] = {}
    for row in d["per_form_daily"]:
        cid = row["conversion_id"]
        f = forms.setdefault(cid, {
            "success": 0, "fail": 0, "interactions": 0,
            "elapsed_sum": 0.0, "session_ms_sum": 0.0, "pages_sum": 0.0,
        })
        f["success"] += row["success"]
        f["fail"] += row["fail"]
        f["interactions"] += row["interactions"]
        f["elapsed_sum"] += row.get("elapsed_sum", 0)
        f["session_ms_sum"] += row.get("session_ms_sum", 0)
        f["pages_sum"] += row.get("pages_sum", 0)

    total_success = sum(f["success"] for f in forms.values())
    total_fail = sum(f["fail"] for f in forms.values())
    total_interactions = sum(f["interactions"] for f in forms.values())
    total_attempts = total_success + total_fail
    conv_rate = (total_success / total_attempts * 100) if total_attempts else 0
    total_elapsed = sum(f["elapsed_sum"] for f in forms.values())
    total_pages = sum(f["pages_sum"] for f in forms.values())
    avg_pages = (total_pages / total_success) if total_success else 0

    total_sessions = sum(r["sessions"] for r in d.get("sessions_daily", []))
    total_users = sum(r["users"] for r in d.get("sessions_daily", []))
    site_cr = (total_success / total_sessions * 100) if total_sessions else 0

    avg_elapsed = (sum(f["elapsed_sum"] for f in forms.values()) / total_success) if total_success else 0
    avg_session = (sum(f["session_ms_sum"] for f in forms.values()) / total_success) if total_success else 0

    return {
        "total_sessions": total_sessions,
        "total_users": total_users,
        "total_conversions": total_success,
        "total_failed_attempts": total_fail,
        "total_interactions": total_interactions,
        "total_attempts": total_attempts,
        "site_conversion_rate_pct": round(site_cr, 2),
        "attempt_conversion_rate_pct": round(conv_rate, 1),
        "avg_session_ms": int(avg_session),
        "avg_elapsed_ms": int(avg_elapsed),
        "avg_pages_visited": round(avg_pages, 1),
    }
