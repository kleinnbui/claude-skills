"""Export SEO analysis results to Google Sheets.

Usage:
  python export_sheets.py result.json SHEET_ID [--profile NAME]

Or call export_to_sheet(result_dict, sheet_id, profile) from main.py.

Note: requires spreadsheets write scope. Re-auth if you get a 403.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config, credentials_path
from auth import load_credentials

import gspread


def _ws(sh, title: str, rows: int = 2000, cols: int = 26):
    try:
        ws = sh.worksheet(title)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=rows, cols=cols)
    return ws


def _write(ws, headers: list[str], data: list[dict]) -> None:
    if not data:
        ws.update("A1", [["(no data)"]])
        return
    rows = [headers]
    for item in data:
        rows.append([_fmt(item.get(h)) for h in headers])
    ws.update("A1", rows, value_input_option="USER_ENTERED")
    ws.format("1:1", {"textFormat": {"bold": True}})


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, list):
        return " | ".join(str(x) for x in v[:3])
    return v


def export_to_sheet(result: dict, sheet_id: str, profile: str | None = None) -> str:
    """Write analysis result to existing Google Sheet. Returns Sheet URL."""
    creds = load_credentials(credentials_path(profile))
    gc = gspread.authorize(creds)

    try:
        sh = gc.open_by_key(sheet_id)
    except gspread.exceptions.APIError as e:
        if "403" in str(e):
            raise PermissionError(
                "Không có quyền ghi vào Sheet. Chạy lại 'manage_accounts.py auth' "
                "để cấp phép spreadsheets write scope."
            ) from e
        raise

    period = result.get("period", "")
    prof = result.get("profile", "")
    generated = result.get("generated_at", "")[:10]

    print(f"[export] Exporting {prof} / {period} → Sheet {sheet_id}", file=sys.stderr)

    # ── Summary ────────────────────────────────────────────────────────────────
    ws = _ws(sh, "Summary")
    s = result.get("summary", {})
    c = result.get("compare") or {}
    chg = c.get("changes_pct") or {}
    prev_s = c.get("previous") or {}
    compare_type = c.get("compare_type", "period")
    cmp_label = "YoY %" if compare_type == "yoy" else "Prev period %"
    summary_rows = [
        ["SEO Report", f"{prof} — {period} — {generated}", "", ""],
        [],
        ["Metric", "Current", "Previous", cmp_label],
        ["Sessions", s.get("sessions"), prev_s.get("sessions"), chg.get("sessions")],
        ["Users", s.get("users"), prev_s.get("users"), chg.get("users")],
        ["New Users", s.get("new_users"), prev_s.get("new_users"), chg.get("new_users")],
        ["Engaged Sessions", s.get("engaged_sessions"), prev_s.get("engaged_sessions"), chg.get("engaged_sessions")],
        ["GSC Clicks", s.get("gsc_clicks"), prev_s.get("gsc_clicks"), chg.get("gsc_clicks")],
        ["GSC Impressions", s.get("gsc_impressions"), prev_s.get("gsc_impressions"), chg.get("gsc_impressions")],
        ["Avg CTR", s.get("avg_ctr"), prev_s.get("avg_ctr"), chg.get("avg_ctr")],
        ["Avg Position", s.get("avg_position"), prev_s.get("avg_position"), chg.get("avg_position")],
        ["Days in period", s.get("days_in_period")],
        [],
        ["Current period", (s.get("period") or {}).get("start"), "→", (s.get("period") or {}).get("end")],
        ["Compare period", (prev_s.get("period") or {}).get("start"), "→", (prev_s.get("period") or {}).get("end")],
    ]
    ws.update("A1", summary_rows, value_input_option="USER_ENTERED")
    ws.format("1:1", {"textFormat": {"bold": True}})
    ws.format("3:3", {"textFormat": {"bold": True}})
    print("[export] ✓ Summary", file=sys.stderr)

    # ── KPI ────────────────────────────────────────────────────────────────────
    kpi = result.get("kpi")
    if kpi:
        ws = _ws(sh, "KPI")
        kpi_rows = [
            ["KPI Tracking", "", ""],
            ["Metric", "Value", ""],
            ["Monthly target", kpi.get("monthly_target")],
            ["Current total", kpi.get("current_total")],
            ["Daily target", kpi.get("daily_target")],
            ["Current daily avg", kpi.get("current_daily_avg")],
            ["Projected total", kpi.get("projected_total")],
            ["Projected vs target %", kpi.get("projected_vs_target_pct")],
            ["On track", "YES" if kpi.get("on_track") else "NO"],
            ["Days elapsed / remaining", f"{kpi.get('days_elapsed')} / {kpi.get('days_remaining')}"],
        ]
        ws.update("A1", kpi_rows)
        ws.format("1:2", {"textFormat": {"bold": True}})
        print("[export] ✓ KPI", file=sys.stderr)

    # ── URL Changes ────────────────────────────────────────────────────────────
    url_changes = result.get("url_changes")
    if url_changes:
        hdrs = ["url", "sessions", "prev_sessions", "sessions_change_pct",
                "clicks", "impressions", "position", "ctr", "diagnosis", "advice"]
        ws = _ws(sh, "Growing URLs")
        _write(ws, hdrs, url_changes.get("growing", []))
        print("[export] ✓ Growing URLs", file=sys.stderr)

        ws = _ws(sh, "Declining URLs")
        _write(ws, hdrs, url_changes.get("declining", []))
        print("[export] ✓ Declining URLs", file=sys.stderr)

    # ── Query Analysis ─────────────────────────────────────────────────────────
    qa = result.get("query_analysis") or {}
    if qa.get("top_queries"):
        ws = _ws(sh, "Top Queries")
        _write(ws, ["query", "clicks", "impressions", "ctr", "position", "branded"],
               qa["top_queries"])
        print("[export] ✓ Top Queries", file=sys.stderr)

    if qa.get("growing_queries"):
        ws = _ws(sh, "Growing Queries")
        _write(ws, ["query", "clicks", "prev_clicks", "clicks_change_pct", "impressions", "position"],
               qa["growing_queries"])
        print("[export] ✓ Growing Queries", file=sys.stderr)

    if qa.get("declining_queries"):
        ws = _ws(sh, "Declining Queries")
        _write(ws, ["query", "clicks", "prev_clicks", "clicks_change_pct", "impressions", "position"],
               qa["declining_queries"])
        print("[export] ✓ Declining Queries", file=sys.stderr)

    if qa.get("new_queries"):
        ws = _ws(sh, "New Queries")
        _write(ws, ["query", "clicks", "impressions", "ctr", "position"],
               qa["new_queries"])
        print("[export] ✓ New Queries", file=sys.stderr)

    if qa.get("impression_only_queries"):
        ws = _ws(sh, "Impression Only")
        _write(ws, ["query", "impressions", "clicks", "ctr", "position"],
               qa["impression_only_queries"])
        print("[export] ✓ Impression Only", file=sys.stderr)

    # ── CTR Opportunities ──────────────────────────────────────────────────────
    if result.get("ctr_opportunities"):
        ws = _ws(sh, "CTR Opportunities")
        _write(ws,
               ["query", "page", "impressions", "clicks", "ctr", "expected_ctr",
                "position", "potential_extra_clicks"],
               result["ctr_opportunities"])
        print("[export] ✓ CTR Opportunities", file=sys.stderr)

    # ── Traffic Potential ──────────────────────────────────────────────────────
    if result.get("traffic_potential"):
        ws = _ws(sh, "Traffic Potential")
        _write(ws,
               ["page", "total_impressions", "total_clicks", "query_count", "avg_position", "topic"],
               result["traffic_potential"])
        print("[export] ✓ Traffic Potential", file=sys.stderr)

    # ── Content Decay ──────────────────────────────────────────────────────────
    if result.get("content_decay"):
        ws = _ws(sh, "Content Decay")
        _write(ws,
               ["url", "current_sessions", "prev_sessions", "change_pct",
                "engaged_sessions", "engagement_rate", "topic"],
               result["content_decay"])
        print("[export] ✓ Content Decay", file=sys.stderr)

    # ── Keyword Cannibalization ────────────────────────────────────────────────
    if result.get("keyword_cannibalization"):
        ws = _ws(sh, "Cannibalization")
        flat = []
        for item in result["keyword_cannibalization"]:
            flat.append({
                "query": item["query"],
                "url_count": item["url_count"],
                "total_clicks": item["total_clicks"],
                "competing_urls": " | ".join(u["page"] for u in item.get("competing_urls", [])[:4]),
            })
        _write(ws, ["query", "url_count", "total_clicks", "competing_urls"], flat)
        print("[export] ✓ Cannibalization", file=sys.stderr)

    # ── Watchlist ──────────────────────────────────────────────────────────────
    if result.get("watchlist_report"):
        ws = _ws(sh, "Watchlist")
        _write(ws,
               ["url", "note", "clicks", "prev_clicks", "clicks_change_pct",
                "impressions", "position", "prev_position", "position_change", "ctr"],
               result["watchlist_report"])
        print("[export] ✓ Watchlist", file=sys.stderr)

    # ── Daily + Weekly Trend ───────────────────────────────────────────────────
    if result.get("gsc_daily_trend"):
        ws = _ws(sh, "Daily Trend")
        _write(ws, ["date", "clicks", "impressions", "ctr", "position"],
               result["gsc_daily_trend"])
        print("[export] ✓ Daily Trend", file=sys.stderr)

    if result.get("gsc_weekly_trend"):
        ws = _ws(sh, "Weekly Trend")
        _write(ws, ["week_start", "clicks", "impressions", "avg_ctr", "avg_position"],
               result["gsc_weekly_trend"])
        print("[export] ✓ Weekly Trend", file=sys.stderr)

    # ── Position Distribution ─────────────────────────────────────────────────
    pd_ = result.get("position_distribution")
    if pd_:
        ws = _ws(sh, "Position Distribution")
        cur_d = pd_.get("current", {})
        prev_d = pd_.get("previous", {})
        chg = pd_.get("changes", {})
        pos_rows = [
            ["Tier", "Current", "Previous", "Change"],
            ["Top 3", cur_d.get("top3"), prev_d.get("top3"), chg.get("top3")],
            ["Top 10", cur_d.get("top10"), prev_d.get("top10"), chg.get("top10")],
            ["Top 20", cur_d.get("top20"), prev_d.get("top20"), chg.get("top20")],
            ["Below 20", cur_d.get("below20"), prev_d.get("below20"), chg.get("below20")],
            [],
            ["Total URLs (cur)", pd_.get("total_urls_cur"), "Total URLs (prev)", pd_.get("total_urls_prev")],
        ]
        ws.update("A1", pos_rows, value_input_option="USER_ENTERED")
        ws.format("1:1", {"textFormat": {"bold": True}})
        print("[export] ✓ Position Distribution", file=sys.stderr)

    # ── Device Breakdown ──────────────────────────────────────────────────────
    if result.get("device_breakdown_ga4"):
        ws = _ws(sh, "Device GA4")
        _write(ws, ["device", "sessions", "users", "pageviews", "engaged_sessions"],
               result["device_breakdown_ga4"])
        print("[export] ✓ Device GA4", file=sys.stderr)

    if result.get("device_breakdown_gsc"):
        ws = _ws(sh, "Device GSC")
        _write(ws, ["device", "clicks", "impressions", "ctr", "position"],
               result["device_breakdown_gsc"])
        print("[export] ✓ Device GSC", file=sys.stderr)

    # ── Country Breakdown ─────────────────────────────────────────────────────
    if result.get("country_breakdown_gsc"):
        ws = _ws(sh, "Country")
        _write(ws, ["country", "clicks", "impressions", "ctr", "position"],
               result["country_breakdown_gsc"])
        print("[export] ✓ Country", file=sys.stderr)

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    print(f"[export] Done → {url}", file=sys.stderr)
    return url


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export SEO analysis to Google Sheets")
    parser.add_argument("result_file", help="JSON output file from main.py")
    parser.add_argument("sheet_id", help="Google Sheet ID to write to")
    parser.add_argument("--profile", help="Profile name")
    args = parser.parse_args()

    with open(args.result_file) as f:
        result = json.load(f)

    url = export_to_sheet(result, args.sheet_id, args.profile)
    print(url)
