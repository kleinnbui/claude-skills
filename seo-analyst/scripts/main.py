"""SEO Traffic Analyst - main orchestrator.

Usage:
  python main.py [period] [--no-compare] [--mode quick|full] [--profile NAME]

period options:
  7d, 14d, 28d, 30d, 60d, 90d, 6m, 12m
  this_week, this_month, last_month
"""
import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config
import fetch_ga4
import fetch_gsc
import fetch_sheets


# ── Period helpers ──────────────────────────────────────────────────────────

_PERIOD_DAYS = {
    "7d": 7, "14d": 14, "28d": 28, "30d": 30,
    "60d": 60, "90d": 90, "6m": 180, "12m": 365,
}


def parse_period(period: str) -> tuple[str, str, int]:
    today = date.today()
    if period in _PERIOD_DAYS:
        days = _PERIOD_DAYS[period]
        return (today - timedelta(days=days)).isoformat(), today.isoformat(), days
    if period == "this_week":
        start = today - timedelta(days=today.weekday())
        return start.isoformat(), today.isoformat(), (today - start).days + 1
    if period == "this_month":
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat(), (today - start).days + 1
    if period == "last_month":
        first = today.replace(day=1)
        last = first - timedelta(days=1)
        start = last.replace(day=1)
        return start.isoformat(), last.isoformat(), last.day
    raise ValueError(f"Unknown period: {period}")


def prev_period(start: str, end: str) -> tuple[str, str]:
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    days = (e - s).days + 1
    pe = s - timedelta(days=1)
    ps = pe - timedelta(days=days - 1)
    return ps.isoformat(), pe.isoformat()


def yoy_period(start: str, end: str) -> tuple[str, str]:
    """Same calendar period, 1 year ago. Handles Feb 29 leap year edge case."""
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    try:
        ys = s.replace(year=s.year - 1)
    except ValueError:
        ys = s.replace(year=s.year - 1, day=28)
    try:
        ye = e.replace(year=e.year - 1)
    except ValueError:
        ye = e.replace(year=e.year - 1, day=28)
    return ys.isoformat(), ye.isoformat()


# ── Aggregation helpers ─────────────────────────────────────────────────────

def _agg_ga4(rows: list[dict]) -> dict[str, dict]:
    agg: dict[str, dict] = defaultdict(lambda: {
        "sessions": 0, "users": 0, "new_users": 0, "pageviews": 0,
        "engaged_sessions": 0,
        "_bounce_sum": 0.0, "_eng_rate_sum": 0.0, "_dur_sum": 0.0,
    })
    for r in rows:
        a = agg[r["page"]]
        a["sessions"] += r["sessions"]
        a["users"] += r["users"]
        a["new_users"] += r.get("new_users", 0)
        a["pageviews"] += r["pageviews"]
        a["engaged_sessions"] += r.get("engaged_sessions", 0)
        a["_bounce_sum"] += r["bounce_rate"] * r["sessions"]
        a["_eng_rate_sum"] += r.get("engagement_rate", 0) * r["sessions"]
        a["_dur_sum"] += r.get("avg_session_duration", 0) * r["sessions"]
    result = {}
    for page, a in agg.items():
        s = a["sessions"]
        result[page] = {
            "sessions": s,
            "users": a["users"],
            "new_users": a["new_users"],
            "pageviews": a["pageviews"],
            "engaged_sessions": a["engaged_sessions"],
            "bounce_rate": round(a["_bounce_sum"] / s, 4) if s else 0.0,
            "engagement_rate": round(a["_eng_rate_sum"] / s, 4) if s else 0.0,
            "avg_session_duration": round(a["_dur_sum"] / s, 1) if s else 0.0,
        }
    return result


def _url_index(url_groups: list[dict]) -> dict[str, dict]:
    idx = {}
    for row in url_groups:
        url = str(row.get("url", row.get("URL", ""))).strip()
        if url:
            idx[url] = row
    return idx


def _group_cols(url_groups: list[dict]) -> list[str]:
    if not url_groups:
        return []
    skip = {"url", "URL"}
    return [k for k in url_groups[0] if k not in skip]


# ── Weekly aggregation ─────────────────────────────────────────────────────

def _weekly_aggregation(daily_rows: list[dict]) -> list[dict]:
    weeks: dict[str, dict] = defaultdict(lambda: {
        "clicks": 0, "impressions": 0, "_ctr_n": 0.0, "_pos_n": 0.0, "_cnt": 0,
    })
    for r in daily_rows:
        d = date.fromisoformat(r["date"])
        week_start = (d - timedelta(days=d.weekday())).isoformat()
        w = weeks[week_start]
        w["clicks"] += r["clicks"]
        w["impressions"] += r["impressions"]
        w["_ctr_n"] += r["ctr"] * r["impressions"]
        w["_pos_n"] += r["position"]
        w["_cnt"] += 1
    return sorted(
        [
            {
                "week_start": ws,
                "clicks": w["clicks"],
                "impressions": w["impressions"],
                "avg_ctr": round(w["_ctr_n"] / w["impressions"], 4) if w["impressions"] else 0,
                "avg_position": round(w["_pos_n"] / w["_cnt"], 2) if w["_cnt"] else 0,
            }
            for ws, w in weeks.items()
        ],
        key=lambda x: x["week_start"],
    )


# ── Slug-based auto clustering ──────────────────────────────────────────────

def auto_cluster_by_slug(urls: list[str]) -> list[dict]:
    """Cluster URLs by first meaningful path segment when no Sheet is configured."""
    clusters: dict[str, dict] = defaultdict(lambda: {"urls": [], "label": ""})
    for url in urls:
        path = urlparse(url).path if "://" in url else url
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            label = "(homepage)"
        elif len(parts) == 1:
            label = "(root)"
        else:
            label = parts[0]
        clusters[label]["urls"].append(url)
        clusters[label]["label"] = label
    return [{"group": v["label"], "urls": v["urls"], "url_count": len(v["urls"])} for v in clusters.values()]


# ── Core analysis functions ─────────────────────────────────────────────────

def analyze_by_group(
    ga4_by_page: dict, gsc_pages: list[dict], url_groups: list[dict]
) -> dict:
    idx = _url_index(url_groups)
    cols = _group_cols(url_groups)
    gsc_idx = {r["page"]: r for r in gsc_pages}

    groups: dict[str, dict] = {
        col: defaultdict(lambda: {
            "urls": set(), "sessions": 0, "users": 0, "pageviews": 0,
            "engaged_sessions": 0,
            "clicks": 0, "impressions": 0,
            "_ctr_num": 0.0, "_pos_num": 0.0, "_pos_cnt": 0,
        })
        for col in cols
    }

    for url, ga4 in ga4_by_page.items():
        meta = idx.get(url, {})
        gsc = gsc_idx.get(url, {})
        for col in cols:
            val = str(meta.get(col, "Uncategorized")).strip() or "Uncategorized"
            g = groups[col][val]
            g["urls"].add(url)
            g["sessions"] += ga4["sessions"]
            g["users"] += ga4["users"]
            g["pageviews"] += ga4["pageviews"]
            g["engaged_sessions"] += ga4.get("engaged_sessions", 0)
            if gsc:
                imp = gsc.get("impressions", 0)
                g["clicks"] += gsc.get("clicks", 0)
                g["impressions"] += imp
                g["_ctr_num"] += gsc.get("ctr", 0) * imp
                if imp:
                    g["_pos_num"] += gsc.get("position", 0)
                    g["_pos_cnt"] += 1

    result = {}
    for col, grp_data in groups.items():
        result[col] = sorted(
            [
                {
                    "group": val,
                    "url_count": len(g["urls"]),
                    "sessions": g["sessions"],
                    "users": g["users"],
                    "pageviews": g["pageviews"],
                    "engaged_sessions": g["engaged_sessions"],
                    "clicks": g["clicks"],
                    "impressions": g["impressions"],
                    "avg_ctr": round(g["_ctr_num"] / g["impressions"], 4) if g["impressions"] else 0,
                    "avg_position": round(g["_pos_num"] / g["_pos_cnt"], 2) if g["_pos_cnt"] else 0,
                }
                for val, g in grp_data.items()
            ],
            key=lambda x: -x["sessions"],
        )
    return result


def _decay_cause(gsc_cur: dict, gsc_prev: dict) -> str:
    """Classify root cause of session decay using GSC signals."""
    if not gsc_cur and not gsc_prev:
        return "non_seo"
    imp_cur = gsc_cur.get("impressions", 0)
    imp_prev = gsc_prev.get("impressions", 0) if gsc_prev else 0
    pos_cur = gsc_cur.get("position", 0)
    pos_prev = gsc_prev.get("position", 0) if gsc_prev else 0
    if imp_prev:
        imp_chg = (imp_cur - imp_prev) / imp_prev
        if pos_prev and (pos_cur - pos_prev) > 3 and imp_chg < -0.10:
            return "ranking_drop"
        if imp_chg < -0.20:
            return "query_trend"
        ctr_chg = gsc_cur.get("ctr", 0) - (gsc_prev.get("ctr", 0) if gsc_prev else 0)
        if imp_chg > -0.10 and ctr_chg < -0.02:
            return "ctr_issue"
    return "non_seo"


def analyze_decay(
    cur_rows: list[dict], prev_rows: list[dict],
    url_groups: list[dict], threshold: float = 0.30,
    full_mode: bool = False,
    gsc_pages_cur: list[dict] | None = None,
    gsc_pages_prev: list[dict] | None = None,
) -> list[dict]:
    idx = _url_index(url_groups)
    cur = _agg_ga4(cur_rows)
    prev = _agg_ga4(prev_rows)
    gsc_cur_idx = {r["page"]: r for r in (gsc_pages_cur or [])}
    gsc_prev_idx = {r["page"]: r for r in (gsc_pages_prev or [])}
    decaying = []
    for url, c in cur.items():
        p = prev.get(url)
        if not p:
            continue
        # In full mode include all declining URLs; in quick mode require min 20 prev sessions
        if not full_mode and p["sessions"] < 20:
            continue
        change = (c["sessions"] - p["sessions"]) / p["sessions"] if p["sessions"] else 0
        if change < -threshold:
            meta = idx.get(url, {})
            slug = urlparse(url).path if "://" in url else url
            cause = _decay_cause(gsc_cur_idx.get(url, {}), gsc_prev_idx.get(url))
            decaying.append({
                "url": slug,
                "current_sessions": c["sessions"],
                "prev_sessions": p["sessions"],
                "change_pct": round(change * 100, 1),
                "engaged_sessions": c.get("engaged_sessions", 0),
                "engagement_rate": c.get("engagement_rate", 0),
                "decay_cause": cause,
                "topic": meta.get("topic", meta.get("group", "")),
                "publish_date": meta.get("publish_date", ""),
            })
    return sorted(decaying, key=lambda x: x["change_pct"])


def analyze_ctr_opportunities(
    gsc_queries: list[dict], url_groups: list[dict],
    min_impressions: int = 100, max_position: float = 30,
    top_n: int | None = None,
) -> list[dict]:
    idx = _url_index(url_groups)

    pos_ctrs: dict[int, list[float]] = defaultdict(list)
    for q in gsc_queries:
        pos_ctrs[int(q["position"])].append(q["ctr"])
    avg_ctr_pos = {p: sum(ctrs) / len(ctrs) for p, ctrs in pos_ctrs.items()}

    ops = []
    for q in gsc_queries:
        if q["impressions"] < min_impressions or q["position"] > max_position:
            continue
        expected = avg_ctr_pos.get(int(q["position"]), 0.05)
        if q["ctr"] < expected * 0.70:
            meta = idx.get(q["page"], {})
            ops.append({
                "query": q["query"],
                "page": q["page"],
                "impressions": q["impressions"],
                "clicks": q["clicks"],
                "ctr": q["ctr"],
                "expected_ctr": round(expected, 4),
                "position": q["position"],
                "potential_extra_clicks": int((expected - q["ctr"]) * q["impressions"]),
                "topic": meta.get("topic", meta.get("group", "")),
            })
    result = sorted(ops, key=lambda x: -x["potential_extra_clicks"])
    return result if top_n is None else result[:top_n]


def analyze_cannibalization(
    gsc_queries: list[dict], min_clicks: int = 5, min_impressions: int = 50,
    top_n: int | None = None,
) -> list[dict]:
    by_query: dict[str, list[dict]] = defaultdict(list)
    for q in gsc_queries:
        if q["clicks"] >= min_clicks or q["impressions"] >= min_impressions:
            by_query[q["query"]].append({
                "page": q["page"],
                "clicks": q["clicks"],
                "impressions": q["impressions"],
                "position": q["position"],
            })

    result = []
    for query, pages in by_query.items():
        if len(pages) > 1:
            result.append({
                "query": query,
                "url_count": len(pages),
                "total_clicks": sum(p["clicks"] for p in pages),
                "competing_urls": sorted(pages, key=lambda x: -x["clicks"]),
            })
    result = sorted(result, key=lambda x: -x["total_clicks"])
    return result if top_n is None else result[:top_n]


def analyze_potential(
    gsc_queries: list[dict], url_groups: list[dict],
    min_impressions: int = 50,
    min_pos: float = 4.0, max_pos: float = 20.0,
    top_n: int | None = None,
) -> list[dict]:
    idx = _url_index(url_groups)
    by_page: dict[str, dict] = defaultdict(
        lambda: {"queries": [], "total_impressions": 0, "total_clicks": 0}
    )
    for q in gsc_queries:
        if min_pos <= q["position"] <= max_pos and q["impressions"] >= min_impressions:
            p = by_page[q["page"]]
            p["queries"].append(q)
            p["total_impressions"] += q["impressions"]
            p["total_clicks"] += q["clicks"]

    result = []
    for page, p in by_page.items():
        queries = p["queries"]
        avg_pos = sum(q["position"] for q in queries) / len(queries)
        meta = idx.get(page, {})
        result.append({
            "page": page,
            "total_impressions": p["total_impressions"],
            "total_clicks": p["total_clicks"],
            "query_count": len(queries),
            "avg_position": round(avg_pos, 2),
            "topic": meta.get("topic", meta.get("group", "")),
            "publish_date": meta.get("publish_date", ""),
            "top_queries": [
                {"query": q["query"], "impressions": q["impressions"],
                 "position": q["position"], "ctr": q["ctr"]}
                for q in sorted(queries, key=lambda x: -x["impressions"])[:5]
            ],
        })
    result = sorted(result, key=lambda x: -x["total_impressions"])
    return result if top_n is None else result[:top_n]


# ── New analysis functions ──────────────────────────────────────────────────

def analyze_queries(
    gsc_queries_cur: list[dict],
    gsc_queries_prev: list[dict],
    brand_keywords: list[str] | None = None,
    top_n: int = 50,
    trend_threshold_pct: int = 20,
) -> dict:
    """Comprehensive query-level analysis: top queries, trends, branded split, new queries, impression-only."""
    brand_kws = [k.lower() for k in (brand_keywords or [])]

    def is_branded(query: str) -> bool:
        q = query.lower()
        return any(kw in q for kw in brand_kws)

    # Aggregate current period by query (sum across pages)
    cur_by_query: dict[str, dict] = defaultdict(lambda: {
        "clicks": 0, "impressions": 0, "_ctr_n": 0.0,
        "_pos_n": 0.0, "_pos_cnt": 0,
    })
    for r in gsc_queries_cur:
        q = cur_by_query[r["query"]]
        q["clicks"] += r["clicks"]
        q["impressions"] += r["impressions"]
        q["_ctr_n"] += r["ctr"] * r["impressions"]
        if r["impressions"]:
            q["_pos_n"] += r["position"]
            q["_pos_cnt"] += 1

    cur_queries = {
        qry: {
            "query": qry,
            "clicks": d["clicks"],
            "impressions": d["impressions"],
            "ctr": round(d["_ctr_n"] / d["impressions"], 4) if d["impressions"] else 0,
            "position": round(d["_pos_n"] / d["_pos_cnt"], 2) if d["_pos_cnt"] else 0,
            "branded": is_branded(qry),
        }
        for qry, d in cur_by_query.items()
    }

    # Aggregate previous period
    prev_by_query: dict[str, dict] = defaultdict(lambda: {"clicks": 0, "impressions": 0})
    for r in gsc_queries_prev:
        p = prev_by_query[r["query"]]
        p["clicks"] += r["clicks"]
        p["impressions"] += r["impressions"]

    # Top queries
    top_queries = sorted(cur_queries.values(), key=lambda x: -x["clicks"])[:top_n]

    # Branded vs non-branded split
    branded_split = None
    if brand_kws:
        b_clicks = sum(q["clicks"] for q in cur_queries.values() if q["branded"])
        nb_clicks = sum(q["clicks"] for q in cur_queries.values() if not q["branded"])
        b_imp = sum(q["impressions"] for q in cur_queries.values() if q["branded"])
        nb_imp = sum(q["impressions"] for q in cur_queries.values() if not q["branded"])
        total = b_clicks + nb_clicks
        branded_split = {
            "branded_clicks": b_clicks,
            "nonbranded_clicks": nb_clicks,
            "branded_pct": round(b_clicks / total * 100, 1) if total else 0,
            "branded_impressions": b_imp,
            "nonbranded_impressions": nb_imp,
        }

    # Query trends — significant changes vs previous period
    trend_items = []
    for qry, cur in cur_queries.items():
        prev = prev_by_query.get(qry)
        if not prev or prev["clicks"] < 3:
            continue
        clicks_chg = (cur["clicks"] - prev["clicks"]) / prev["clicks"]
        imp_chg = (cur["impressions"] - prev["impressions"]) / prev["impressions"] if prev["impressions"] else 0
        if abs(clicks_chg) >= trend_threshold_pct / 100:
            trend_items.append({
                "query": qry,
                "clicks": cur["clicks"],
                "prev_clicks": prev["clicks"],
                "clicks_change_pct": round(clicks_chg * 100, 1),
                "impressions": cur["impressions"],
                "impressions_change_pct": round(imp_chg * 100, 1),
                "position": cur["position"],
                "branded": cur["branded"],
            })

    growing_queries = sorted(
        [t for t in trend_items if t["clicks_change_pct"] > 0],
        key=lambda x: -x["clicks_change_pct"]
    )[:30]
    declining_queries = sorted(
        [t for t in trend_items if t["clicks_change_pct"] < 0],
        key=lambda x: x["clicks_change_pct"]
    )[:30]

    # New queries — appeared this period, not in previous
    new_queries = sorted(
        [
            q for qry, q in cur_queries.items()
            if qry not in prev_by_query and q["impressions"] >= 30
        ],
        key=lambda x: -x["impressions"],
    )[:30]

    # Impression-only — high impressions, near-zero CTR, rank > 15
    impression_only = sorted(
        [
            q for q in cur_queries.values()
            if q["impressions"] >= 100 and q["ctr"] < 0.01 and q["position"] > 15
        ],
        key=lambda x: -x["impressions"],
    )[:30]

    return {
        "total_unique_queries": len(cur_queries),
        "top_queries": top_queries,
        "branded_split": branded_split,
        "growing_queries": growing_queries,
        "declining_queries": declining_queries,
        "new_queries": new_queries,
        "impression_only_queries": impression_only,
    }


def analyze_position_distribution(
    gsc_pages_cur: list[dict],
    gsc_pages_prev: list[dict],
) -> dict:
    """Count URLs by ranking tier and compare to previous period."""
    def bucket(pos: float) -> str:
        if pos <= 3: return "top3"
        if pos <= 10: return "top10"
        if pos <= 20: return "top20"
        return "below20"

    def dist(pages: list[dict]) -> dict:
        d: dict[str, int] = {"top3": 0, "top10": 0, "top20": 0, "below20": 0}
        for p in pages:
            d[bucket(p["position"])] += 1
        return d

    cur_dist = dist(gsc_pages_cur)
    prev_dist = dist(gsc_pages_prev)
    changes = {k: cur_dist[k] - prev_dist[k] for k in cur_dist}

    return {
        "current": cur_dist,
        "previous": prev_dist,
        "changes": changes,
        "total_urls_cur": len(gsc_pages_cur),
        "total_urls_prev": len(gsc_pages_prev),
    }


def _diagnose_url_change(
    ga4_cur: dict, ga4_prev: dict,
    gsc_cur: dict, gsc_prev: dict,
) -> tuple[str, str]:
    """Return (diagnosis_label_vi, advice_vi) based on GA4 + GSC signal combination."""
    sessions_chg = (
        (ga4_cur["sessions"] - ga4_prev["sessions"]) / ga4_prev["sessions"]
        if ga4_prev.get("sessions") else 0
    )
    pos_cur = gsc_cur.get("position", 0)
    pos_prev = gsc_prev.get("position", 0) if gsc_prev else 0
    pos_chg = pos_cur - pos_prev  # positive = ranking fell; negative = ranking improved
    imp_cur = gsc_cur.get("impressions", 0)
    imp_prev = gsc_prev.get("impressions", 0) if gsc_prev else 0
    imp_chg = (imp_cur - imp_prev) / imp_prev if imp_prev else 0
    ctr_chg = gsc_cur.get("ctr", 0) - (gsc_prev.get("ctr", 0) if gsc_prev else 0)

    growing = sessions_chg > 0.15
    declining = sessions_chg < -0.15

    if growing:
        if pos_prev and pos_chg < -2:
            return (
                "Ranking cải thiện",
                "Tiếp tục build internal link và cập nhật nội dung định kỳ để giữ vị trí."
            )
        if imp_chg > 0.20:
            return (
                "Volume query tăng (có thể do trend hoặc mùa vụ)",
                "Tận dụng momentum: bổ sung nội dung liên quan, build link khi topic đang hot."
            )
        if ctr_chg > 0.02:
            return (
                "CTR cải thiện (title/snippet tốt hơn)",
                "Scale approach này sang các trang có CTR thấp tương tự."
            )
        return ("Traffic tăng — cần xem thêm GSC query detail", "Kiểm tra query mới nào đang drive traffic trang này.")

    if declining:
        if pos_prev and pos_chg > 2:
            return (
                "Ranking tụt — cần review và cải thiện content",
                "Update nội dung theo search intent hiện tại, bổ sung E-E-A-T, kiểm tra internal links."
            )
        if imp_chg < -0.20:
            return (
                "Volume query giảm (trend hoặc mùa vụ)",
                "Kiểm tra Google Trends để xác nhận. Nếu seasonal thì chờ; nếu dài hạn cân nhắc pivot topic."
            )
        if imp_chg >= -0.10 and ctr_chg < -0.02:
            return (
                "SERP features chiếm click (featured snippet / SGE / PAA)",
                "Tối ưu title thêm CTA, hoặc chủ động target featured snippet để lấy lại vị trí."
            )
        if imp_chg > 0.10:
            return (
                "Intent mismatch — Google show nhiều hơn nhưng user không click",
                "Review lại nội dung: người dùng đang tìm gì khác với những gì trang cung cấp."
            )
        return ("Traffic giảm — cần kiểm tra thêm", "Kiểm tra GSC Coverage, Core Web Vitals, và recent Google updates.")

    return ("Ổn định", "")


def analyze_url_changes(
    ga4_cur_rows: list[dict],
    ga4_prev_rows: list[dict],
    gsc_pages_cur: list[dict],
    gsc_pages_prev: list[dict],
    url_groups: list[dict],
    min_prev_sessions: int = 10,
    full_mode: bool = False,
) -> dict:
    """Diagnose why each URL increased or decreased."""
    idx = _url_index(url_groups)
    cur = _agg_ga4(ga4_cur_rows)
    prev = _agg_ga4(ga4_prev_rows)
    gsc_cur_idx = {r["page"]: r for r in gsc_pages_cur}
    gsc_prev_idx = {r["page"]: r for r in gsc_pages_prev}

    items = []
    for url in set(cur.keys()) | set(prev.keys()):
        c = cur.get(url, {"sessions": 0, "users": 0, "pageviews": 0,
                           "engaged_sessions": 0, "engagement_rate": 0, "avg_session_duration": 0})
        p = prev.get(url, {"sessions": 0})

        if p["sessions"] < min_prev_sessions:
            continue
        if c["sessions"] == 0 and p["sessions"] < 20:
            continue

        sessions_chg = (c["sessions"] - p["sessions"]) / p["sessions"] if p["sessions"] else 0
        if abs(sessions_chg) < 0.15:
            continue

        gsc_c = gsc_cur_idx.get(url, {})
        gsc_p = gsc_prev_idx.get(url, {})
        diagnosis, advice = _diagnose_url_change(c, p, gsc_c, gsc_p)
        meta = idx.get(url, {})

        # Shorten URL to slug only
        slug = urlparse(url).path if "://" in url else url

        items.append({
            "url": slug,
            "sessions": c["sessions"],
            "prev_sessions": p["sessions"],
            "sessions_change_pct": round(sessions_chg * 100, 1),
            "engaged_sessions": c.get("engaged_sessions", 0),
            "engagement_rate": c.get("engagement_rate", 0),
            "avg_session_duration": c.get("avg_session_duration", 0),
            "clicks": gsc_c.get("clicks", 0),
            "impressions": gsc_c.get("impressions", 0),
            "position": gsc_c.get("position", 0),
            "prev_position": gsc_p.get("position", 0) if gsc_p else None,
            "position_change": round(
                gsc_c.get("position", 0) - gsc_p.get("position", 0), 2
            ) if gsc_p and gsc_c else None,
            "ctr": gsc_c.get("ctr", 0),
            "diagnosis": diagnosis,
            "advice": advice,
            "topic": meta.get("topic", meta.get("group", "")),
        })

    growing = sorted(
        [i for i in items if i["sessions_change_pct"] > 0],
        key=lambda x: -abs(x["sessions"] - x["prev_sessions"]),
    )
    declining = sorted(
        [i for i in items if i["sessions_change_pct"] < 0],
        key=lambda x: x["sessions_change_pct"],
    )

    if not full_mode:
        growing = growing[:30]
        declining = declining[:30]

    return {"growing": growing, "declining": declining}


def analyze_anomaly(gsc_daily: list[dict], threshold_pct: int = 30) -> dict:
    """Compare most recent available day vs rolling 7-day average. Detect anomalies."""
    if len(gsc_daily) < 3:
        return {"available": False, "reason": "Insufficient daily data"}

    sorted_daily = sorted(gsc_daily, key=lambda x: x["date"])
    most_recent = sorted_daily[-1]
    rolling_window = sorted_daily[-8:-1]  # 7 days before most recent

    if not rolling_window:
        return {"available": False, "reason": "Not enough history for comparison"}

    avg_clicks = sum(d["clicks"] for d in rolling_window) / len(rolling_window)
    avg_impressions = sum(d["impressions"] for d in rolling_window) / len(rolling_window)

    clicks_dev = (most_recent["clicks"] - avg_clicks) / avg_clicks if avg_clicks else 0
    imp_dev = (most_recent["impressions"] - avg_impressions) / avg_impressions if avg_impressions else 0

    threshold = threshold_pct / 100
    alerts = []

    if clicks_dev < -threshold:
        alerts.append({
            "type": "clicks_drop",
            "severity": "high" if clicks_dev < -0.50 else "medium",
            "message": (
                f"Clicks ngày {most_recent['date']} giảm {abs(clicks_dev)*100:.0f}% "
                f"so với trung bình 7 ngày trước "
                f"({most_recent['clicks']} vs avg {avg_clicks:.0f})"
            ),
        })
    elif clicks_dev > threshold:
        alerts.append({
            "type": "clicks_spike",
            "severity": "info",
            "message": (
                f"Clicks ngày {most_recent['date']} tăng đột biến {clicks_dev*100:.0f}% "
                f"so với trung bình 7 ngày ({most_recent['clicks']} vs avg {avg_clicks:.0f})"
            ),
        })

    if imp_dev < -threshold:
        alerts.append({
            "type": "impressions_drop",
            "severity": "high" if imp_dev < -0.50 else "medium",
            "message": (
                f"Impressions ngày {most_recent['date']} giảm {abs(imp_dev)*100:.0f}% — "
                f"có thể bị deindex hoặc Google algorithm update"
            ),
        })

    return {
        "available": True,
        "most_recent_date": most_recent["date"],
        "most_recent": most_recent,
        "rolling_avg_7d": {
            "clicks": round(avg_clicks, 1),
            "impressions": round(avg_impressions, 1),
            "ctr": round(sum(d["ctr"] for d in rolling_window) / len(rolling_window), 4),
        },
        "clicks_deviation_pct": round(clicks_dev * 100, 1),
        "impressions_deviation_pct": round(imp_dev * 100, 1),
        "alerts": alerts,
        "status": "anomaly" if alerts else "normal",
    }


def analyze_kpi(summary: dict, cfg: dict, period: str) -> dict | None:
    """KPI tracking — only for monthly periods."""
    kpi_cfg = cfg.get("kpi")
    if not kpi_cfg or not kpi_cfg.get("monthly_target"):
        return None

    import calendar
    today = date.today()
    source = kpi_cfg.get("source", "gsc")
    metric = kpi_cfg.get("metric", "clicks")
    monthly_target = int(kpi_cfg["monthly_target"])

    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_elapsed = today.day
    days_remaining = days_in_month - days_elapsed
    daily_target = monthly_target / days_in_month

    if source == "gsc":
        current_total = summary.get("gsc_clicks", 0)
    else:
        current_total = summary.get("sessions", 0)

    current_daily_avg = current_total / days_elapsed if days_elapsed else 0
    projected_total = round(current_daily_avg * days_in_month)
    gap_daily = daily_target - current_daily_avg

    return {
        "monthly_target": monthly_target,
        "source": source,
        "metric": metric,
        "days_in_month": days_in_month,
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "daily_target": round(daily_target, 1),
        "current_total": current_total,
        "current_daily_avg": round(current_daily_avg, 1),
        "gap_daily": round(gap_daily, 1),
        "projected_total": projected_total,
        "projected_vs_target_pct": round(projected_total / monthly_target * 100, 1),
        "on_track": current_daily_avg >= daily_target * 0.90,
        "needed_per_remaining_day": round(
            (monthly_target - current_total) / days_remaining, 1
        ) if days_remaining > 0 else 0,
    }


# ── Summary helpers ─────────────────────────────────────────────────────────

def _period_summary(ga4_rows: list[dict], gsc_date_rows: list[dict]) -> dict:
    sessions = sum(r["sessions"] for r in ga4_rows)
    users = sum(r["users"] for r in ga4_rows)
    new_users = sum(r.get("new_users", 0) for r in ga4_rows)
    pageviews = sum(r["pageviews"] for r in ga4_rows)
    engaged_sessions = sum(r.get("engaged_sessions", 0) for r in ga4_rows)
    days = len({r["date"] for r in ga4_rows}) or 1

    clicks = sum(r["clicks"] for r in gsc_date_rows)
    impressions = sum(r["impressions"] for r in gsc_date_rows)
    avg_ctr = clicks / impressions if impressions else 0
    avg_pos = (
        sum(r["position"] * r["impressions"] for r in gsc_date_rows) / impressions
        if impressions else 0
    )
    return {
        "sessions": sessions,
        "users": users,
        "new_users": new_users,
        "pageviews": pageviews,
        "engaged_sessions": engaged_sessions,
        "engagement_rate": round(engaged_sessions / sessions, 4) if sessions else 0,
        "avg_daily_sessions": round(sessions / days, 1),
        "avg_daily_users": round(users / days, 1),
        "gsc_clicks": clicks,
        "gsc_impressions": impressions,
        "avg_ctr": round(avg_ctr, 4),
        "avg_position": round(avg_pos, 2),
        "days_in_period": days,
    }


# ── Main orchestrator ───────────────────────────────────────────────────────

def run(
    period: str = "30d",
    compare: bool = True,
    compare_yoy: bool = False,
    profile: str | None = None,
    mode: str = "quick",
) -> dict:
    cfg = load_config(profile)
    start, end, _ = parse_period(period)
    full_mode = (mode == "full")
    top_n = None if full_mode else 25
    min_sessions = cfg.get("full_report_min_sessions", 10) if full_mode else 0

    pname = cfg["_profile_name"]

    def _log(msg: str) -> None:
        print(f"[{pname}] {msg}", file=sys.stderr)

    print(f"[INFO] Period: {start} → {end} | mode={mode}", file=sys.stderr)

    _log("Fetching current period data (parallel)...")
    _cur_tasks: dict = {
        "ga4_rows": (fetch_ga4.by_page, (start, end), {"profile": profile}),
        "ga4_channels": (fetch_ga4.by_channel, (start, end), {"profile": profile}),
        "ga4_devices": (fetch_ga4.by_device, (start, end), {"profile": profile}),
        "gsc_pages": (fetch_gsc.by_page, (start, end), {"profile": profile}),
        "gsc_queries": (fetch_gsc.by_query, (start, end), {"profile": profile}),
        "gsc_daily": (fetch_gsc.by_date, (start, end), {"profile": profile}),
        "gsc_devices": (fetch_gsc.by_device, (start, end), {"profile": profile}),
        "gsc_countries": (fetch_gsc.by_country, (start, end), {"profile": profile}),
    }
    if cfg.get("url_groups_sheet_id"):
        _cur_tasks["url_groups"] = (fetch_sheets.load_url_groups, (), {"profile": profile})

    with ThreadPoolExecutor(max_workers=len(_cur_tasks)) as _ex:
        _futures = {k: _ex.submit(fn, *args, **kw) for k, (fn, args, kw) in _cur_tasks.items()}
        _fetched = {k: f.result() for k, f in _futures.items()}

    ga4_rows = _fetched["ga4_rows"]
    ga4_channels = _fetched["ga4_channels"]
    ga4_devices = _fetched["ga4_devices"]
    gsc_pages = _fetched["gsc_pages"]
    gsc_queries = _fetched["gsc_queries"]
    gsc_daily = _fetched["gsc_daily"]
    gsc_devices = _fetched["gsc_devices"]
    gsc_countries = _fetched["gsc_countries"]
    url_groups = _fetched.get("url_groups", [])

    if not cfg.get("url_groups_sheet_id"):
        _log("No Sheet configured — slug clustering.")
    _log(f"✓ GA4: {len(ga4_rows)} page rows | GSC: {len(gsc_pages)} pages, {len(gsc_queries)} query rows")

    ga4_by_page = _agg_ga4(ga4_rows)
    summary = _period_summary(ga4_rows, gsc_daily)
    summary["period"] = {"start": start, "end": end}

    # Comparison period
    compare_out = None
    decay = []
    url_changes = None
    pos_distribution = None
    query_analysis = None
    prev_gsc_pages = []

    if compare:
        ps, pe = yoy_period(start, end) if compare_yoy else prev_period(start, end)
        compare_type = "yoy" if compare_yoy else "period"
        print(f"[INFO] Compare: {ps} → {pe} ({compare_type})", file=sys.stderr)

        _log(f"Fetching compare period {ps}→{pe} (parallel)...")
        with ThreadPoolExecutor(max_workers=4) as _ex:
            _p_futures = {
                "prev_ga4": _ex.submit(fetch_ga4.by_page, ps, pe, profile=profile),
                "prev_gsc_daily": _ex.submit(fetch_gsc.by_date, ps, pe, profile=profile),
                "prev_gsc_pages": _ex.submit(fetch_gsc.by_page, ps, pe, profile=profile),
                "prev_gsc_queries": _ex.submit(fetch_gsc.by_query, ps, pe, profile=profile),
            }
            _prev = {k: f.result() for k, f in _p_futures.items()}
        prev_ga4 = _prev["prev_ga4"]
        prev_gsc_daily = _prev["prev_gsc_daily"]
        prev_gsc_pages = _prev["prev_gsc_pages"]
        prev_gsc_queries = _prev["prev_gsc_queries"]
        _log(f"✓ Compare: {len(prev_ga4)} GA4 rows, {len(prev_gsc_pages)} GSC pages")

        prev_summary = _period_summary(prev_ga4, prev_gsc_daily)
        prev_summary["period"] = {"start": ps, "end": pe}

        changes = {}
        for m in ("sessions", "users", "new_users", "pageviews", "engaged_sessions",
                  "gsc_clicks", "gsc_impressions", "avg_ctr", "avg_position"):
            p = prev_summary.get(m, 0)
            changes[m] = round((summary.get(m, 0) - p) / p * 100, 1) if p else None

        compare_out = {"previous": prev_summary, "changes_pct": changes, "compare_type": compare_type}

        decay = analyze_decay(
            ga4_rows, prev_ga4, url_groups,
            threshold=cfg.get("decay_threshold_percent", 30) / 100,
            full_mode=full_mode,
            gsc_pages_cur=gsc_pages,
            gsc_pages_prev=prev_gsc_pages,
        )

        url_changes = analyze_url_changes(
            ga4_rows, prev_ga4,
            gsc_pages, prev_gsc_pages,
            url_groups,
            min_prev_sessions=cfg.get("full_report_min_sessions", 10),
            full_mode=full_mode,
        )

        pos_distribution = analyze_position_distribution(gsc_pages, prev_gsc_pages)

        _log("Analyzing queries (trends, branded split, new queries)...")
        query_analysis = analyze_queries(
            gsc_queries, prev_gsc_queries,
            brand_keywords=cfg.get("brand_keywords", []),
            top_n=100 if full_mode else 50,
            trend_threshold_pct=cfg.get("query_trend_threshold_percent", 20),
        )

    _log("Core analyses: CTR opportunities, cannibalization, potential...")
    groups = analyze_by_group(ga4_by_page, gsc_pages, url_groups)

    # Auto-cluster if no sheet configured
    slug_clusters = None
    if not url_groups:
        all_urls = list(ga4_by_page.keys())
        slug_clusters = auto_cluster_by_slug(all_urls)

    ctr_ops = analyze_ctr_opportunities(
        gsc_queries, url_groups,
        min_impressions=cfg.get("ctr_opportunity_min_impressions", 100),
        top_n=top_n,
    )
    cannib = analyze_cannibalization(
        gsc_queries,
        min_clicks=cfg.get("cannibalization_min_clicks", 5),
        min_impressions=cfg.get("cannibalization_min_impressions", 50),
        top_n=top_n,
    )
    potential = analyze_potential(
        gsc_queries, url_groups,
        min_impressions=cfg.get("potential_min_impressions", 50),
        max_pos=cfg.get("potential_max_position", 20),
        top_n=top_n,
    )

    # Top pages — in full mode filter by min sessions/clicks
    if full_mode:
        top_ga4 = sorted(
            [{"url": u, **v} for u, v in ga4_by_page.items() if v["sessions"] >= min_sessions],
            key=lambda x: -x["sessions"],
        )
        top_gsc = sorted(
            [p for p in gsc_pages if p["impressions"] >= min_sessions],
            key=lambda x: -x["clicks"],
        )
    else:
        top_ga4 = sorted(
            [{"url": u, **v} for u, v in ga4_by_page.items()],
            key=lambda x: -x["sessions"],
        )[:30]
        top_gsc = sorted(gsc_pages, key=lambda x: -x["clicks"])[:30]

    # Anomaly detection from existing daily data
    anomaly = analyze_anomaly(gsc_daily, cfg.get("anomaly_threshold_percent", 30))

    # KPI tracking
    kpi = analyze_kpi(summary, cfg, period)

    # Watchlist — look up current + previous GSC data for watched URLs
    watchlist_report = []
    watchlist_cfg = cfg.get("watchlist", [])
    if watchlist_cfg:
        gsc_cur_idx = {r["page"]: r for r in gsc_pages}
        gsc_prev_idx = {r["page"]: r for r in prev_gsc_pages}
        for item in watchlist_cfg:
            url = item["url"]
            cur = gsc_cur_idx.get(url, {})
            prev = gsc_prev_idx.get(url, {})
            entry = {
                "url": url,
                "note": item.get("note", ""),
                "added": item.get("added", ""),
                "clicks": cur.get("clicks", 0),
                "impressions": cur.get("impressions", 0),
                "position": cur.get("position", 0),
                "ctr": cur.get("ctr", 0),
                "prev_clicks": prev.get("clicks"),
                "prev_position": prev.get("position"),
                "clicks_change_pct": (
                    round((cur.get("clicks", 0) - prev["clicks"]) / prev["clicks"] * 100, 1)
                    if prev.get("clicks") else None
                ),
                "position_change": (
                    round(cur["position"] - prev["position"], 2)
                    if cur.get("position") and prev.get("position") else None
                ),
            }
            watchlist_report.append(entry)

    return {
        "generated_at": datetime.now().isoformat(),
        "profile": cfg["_profile_name"],
        "period": period,
        "mode": mode,
        "summary": summary,
        "compare": compare_out,
        "kpi": kpi,
        "anomaly": anomaly,
        "position_distribution": pos_distribution,
        "groups": groups,
        "slug_clusters": slug_clusters,
        "top_pages_ga4": top_ga4,
        "top_pages_gsc": top_gsc,
        "gsc_daily_trend": gsc_daily,
        "gsc_weekly_trend": _weekly_aggregation(gsc_daily),
        "channel_breakdown": ga4_channels,
        "device_breakdown_ga4": ga4_devices,
        "device_breakdown_gsc": gsc_devices,
        "country_breakdown_gsc": gsc_countries,
        "query_analysis": query_analysis,
        "url_changes": url_changes,
        "content_decay": decay,
        "ctr_opportunities": ctr_ops,
        "keyword_cannibalization": cannib,
        "traffic_potential": potential,
        "url_groups_loaded": len(url_groups),
        "watchlist_report": watchlist_report,
    }


# ── Quick check (anomaly only) ──────────────────────────────────────────────

def quick_check(profile: str | None = None) -> dict:
    """Fetch only 9 days of GSC daily data and run anomaly check. Completes in seconds."""
    cfg = load_config(profile)
    today = date.today()
    end = (today - timedelta(days=1)).isoformat()   # yesterday (most recent GSC data)
    start = (today - timedelta(days=9)).isoformat()  # 9 days back for 7-day rolling avg

    print(f"[1/1] [{cfg['_profile_name']}] GSC: daily data ({start} → {end})...", file=sys.stderr)
    gsc_daily = fetch_gsc.by_date(start, end, profile=profile)

    anomaly = analyze_anomaly(gsc_daily, cfg.get("anomaly_threshold_percent", 30))
    return {
        "generated_at": datetime.now().isoformat(),
        "profile": cfg["_profile_name"],
        "mode": "quick_check",
        "gsc_daily": gsc_daily,
        "anomaly": anomaly,
    }


# ── Drill-down by URL ───────────────────────────────────────────────────────

def drill_down_url(
    page_url: str,
    period: str = "30d",
    profile: str | None = None,
) -> dict:
    """Fetch all queries for a specific page URL and compare to previous period."""
    cfg = load_config(profile)
    start, end, _ = parse_period(period)
    ps, pe = prev_period(start, end)

    print(f"[1/2] [{cfg['_profile_name']}] GSC queries for {page_url}...", file=sys.stderr)
    queries_cur = fetch_gsc.by_query_for_page(start, end, page_url, profile=profile)

    print(f"[2/2] [{cfg['_profile_name']}] Previous period queries...", file=sys.stderr)
    queries_prev = fetch_gsc.by_query_for_page(ps, pe, page_url, profile=profile)

    prev_idx = {r["query"]: r for r in queries_prev}

    enriched = []
    for q in sorted(queries_cur, key=lambda x: -x["clicks"]):
        prev = prev_idx.get(q["query"], {})
        clicks_chg = None
        if prev.get("clicks"):
            clicks_chg = round((q["clicks"] - prev["clicks"]) / prev["clicks"] * 100, 1)
        enriched.append({
            **q,
            "prev_clicks": prev.get("clicks", 0),
            "prev_position": prev.get("position", 0),
            "clicks_change_pct": clicks_chg,
            "position_change": round(q["position"] - prev["position"], 2) if prev.get("position") else None,
        })

    return {
        "generated_at": datetime.now().isoformat(),
        "profile": cfg["_profile_name"],
        "page_url": page_url,
        "period": {
            "current": {"start": start, "end": end},
            "previous": {"start": ps, "end": pe},
        },
        "total_queries": len(enriched),
        "queries": enriched,
    }


# ── Batch — compare all profiles ───────────────────────────────────────────

def run_batch(period: str = "30d", profile_names: list[str] | None = None) -> dict:
    """Run quick analysis for multiple profiles and return a comparison summary."""
    from config import _load_accounts
    accounts = _load_accounts()
    all_profiles = list(accounts.get("profiles", {}).keys())
    targets = [p for p in all_profiles if not profile_names or p in profile_names]

    if not targets:
        return {"error": "No profiles found.", "period": period, "mode": "batch", "profiles": {}}

    results = {}
    for i, prof in enumerate(targets, 1):
        print(f"\n[batch {i}/{len(targets)}] Profile: {prof}", file=sys.stderr)
        try:
            r = run(period, compare=True, profile=prof, mode="quick")
            s = r["summary"]
            c = r.get("compare") or {}
            chg = c.get("changes_pct") or {}
            anomaly = r.get("anomaly") or {}
            kpi = r.get("kpi")
            results[prof] = {
                "sessions": s.get("sessions"),
                "gsc_clicks": s.get("gsc_clicks"),
                "gsc_impressions": s.get("gsc_impressions"),
                "avg_position": s.get("avg_position"),
                "avg_ctr": s.get("avg_ctr"),
                "sessions_change_pct": chg.get("sessions"),
                "clicks_change_pct": chg.get("gsc_clicks"),
                "impressions_change_pct": chg.get("gsc_impressions"),
                "anomaly_status": anomaly.get("status"),
                "anomaly_alerts": anomaly.get("alerts", []),
                "kpi_on_track": kpi.get("on_track") if kpi else None,
                "kpi_projected_pct": kpi.get("projected_vs_target_pct") if kpi else None,
            }
        except Exception as e:
            results[prof] = {"error": str(e)}

    return {
        "generated_at": datetime.now().isoformat(),
        "period": period,
        "mode": "batch",
        "profiles": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SEO Traffic Analyst")
    parser.add_argument(
        "period", nargs="?", default="30d",
        help="7d | 14d | 30d | 60d | 90d | 6m | 12m | this_week | this_month | last_month",
    )
    parser.add_argument("--no-compare", action="store_true", help="Skip comparison period")
    parser.add_argument("--mode", choices=["quick", "full"], default="quick",
                        help="quick: top 25/section | full: all URLs >= 10 sessions")
    parser.add_argument("--profile", help="Profile name from accounts.json")
    parser.add_argument("--quick-check", dest="quick_check", action="store_true",
                        help="Quick anomaly check only — fetches 9 days GSC daily, done in seconds")
    parser.add_argument("--drill-url", dest="drill_url", metavar="URL",
                        help="Drill-down: show all queries for a specific page URL")
    parser.add_argument("--compare-yoy", dest="compare_yoy", action="store_true",
                        help="Compare to same period 1 year ago instead of previous period")
    parser.add_argument("--all-profiles", dest="all_profiles", action="store_true",
                        help="Batch: run quick analysis for all configured profiles")
    parser.add_argument("--export-sheet", dest="export_sheet", metavar="SHEET_ID",
                        help="Export results to this Google Sheet ID after analysis")
    args = parser.parse_args()

    if args.quick_check:
        result = quick_check(profile=args.profile)
    elif args.drill_url:
        result = drill_down_url(args.drill_url, period=args.period, profile=args.profile)
    elif args.all_profiles:
        result = run_batch(period=args.period)
    else:
        result = run(
            args.period,
            compare=not args.no_compare,
            compare_yoy=args.compare_yoy,
            profile=args.profile,
            mode=args.mode,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.export_sheet and result.get("mode") != "batch":
        import export_sheets
        try:
            url = export_sheets.export_to_sheet(result, args.export_sheet, args.profile)
            print(f"\n[export] Sheet: {url}", file=sys.stderr)
        except PermissionError as e:
            print(f"\n[export] ERROR: {e}", file=sys.stderr)
