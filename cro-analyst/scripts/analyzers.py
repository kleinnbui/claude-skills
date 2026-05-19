"""5 pure-function analyzers for /cro-analyst (v1 MVP).

Each analyzer consumes the dict returned by ga4_fetcher.fetch_all() and returns
a structured insight:
    {
        "code": "<diagnosis_code>",
        "severity": "high" | "medium" | "low",
        "headline": "<short Vietnamese-ready summary>",
        "signals": {...},          # raw numbers for prose template
        "evidence": {...},          # supporting data (top N rows etc.)
        "prescriptions": [str,...]  # actionable next steps
    }

SKILL.md has a Vietnamese prose template per `code`; Claude fills placeholders
from `signals`. Python never generates user-facing prose.

Analyzer roster (v1):
  1. analyze_funnel           → funnel_diagnostic
  2. analyze_form_triage      → form_triage
  3. analyze_failures         → failure_postmortem
  4. analyze_channel_roi      → channel_roi
  5. analyze_anomaly          → anomaly_detector
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any


# ─── Helpers ───────────────────────────────────────────────────────────────

def _sum(rows: list[dict], field: str) -> int:
    return sum(int(r.get(field, 0) or 0) for r in rows)


def _safe_pct(num: float, denom: float, ndigits: int = 1) -> float:
    return round(num / denom * 100, ndigits) if denom else 0.0


def _safe_ratio(num: float, denom: float, ndigits: int = 3) -> float:
    return round(num / denom, ndigits) if denom else 0.0


def _aggregate_per_form(per_form_daily: list[dict]) -> dict[str, dict]:
    """Collapse per_form_daily rows by conversion_id."""
    out: dict[str, dict] = {}
    for r in per_form_daily:
        cid = r.get("conversion_id", "(unnamed)")
        f = out.setdefault(cid, {
            "conversion_id": cid,
            "trigger_type": "",
            "success": 0, "fail": 0, "interactions": 0,
            "elapsed_sum": 0.0, "session_ms_sum": 0.0, "pages_sum": 0.0,
        })
        if r.get("trigger_type"):
            f["trigger_type"] = r["trigger_type"]
        f["success"] += int(r.get("success", 0) or 0)
        f["fail"] += int(r.get("fail", 0) or 0)
        f["interactions"] += int(r.get("interactions", 0) or 0)
        f["elapsed_sum"] += float(r.get("elapsed_sum", 0) or 0)
        f["session_ms_sum"] += float(r.get("session_ms_sum", 0) or 0)
        f["pages_sum"] += float(r.get("pages_sum", 0) or 0)
    return out


def _date_range_days(meta: dict) -> int:
    """Number of days in fetched date range (inclusive)."""
    try:
        from datetime import datetime
        s = datetime.strptime(meta["date_range"]["start"], "%Y-%m-%d")
        e = datetime.strptime(meta["date_range"]["end"], "%Y-%m-%d")
        return max(1, (e - s).days + 1)
    except Exception:
        return 30


# ─── 1. analyze_funnel ─────────────────────────────────────────────────────

def analyze_funnel(data: dict) -> dict:
    """Diagnose drop-offs across Sessions → FunnelSteps → Interactions → Attempts → Conversions.

    Stages with 0 data are skipped (e.g. no popup_open/chat_open trigger → no FunnelStep stage).
    """
    summary = data.get("summary", {})
    sessions = int(summary.get("total_sessions", 0))
    funnel_steps = int(summary.get("total_funnel_steps", 0))
    interactions = int(summary.get("total_interactions", 0))
    attempts = int(summary.get("total_attempts", 0))
    success = int(summary.get("total_conversions", 0))

    # Build dynamic stage list
    stages = [("sessions", sessions)]
    if funnel_steps > 0:
        stages.append(("funnel_steps", funnel_steps))
    if interactions > 0:
        stages.append(("interactions", interactions))
    stages.append(("attempts", attempts))
    stages.append(("conversions", success))

    # Compute stage transitions (only meaningful ones)
    transitions = []
    for i in range(len(stages) - 1):
        a_name, a_val = stages[i]
        b_name, b_val = stages[i + 1]
        if a_val == 0:
            continue
        rate = b_val / a_val
        drop_pct = round((1 - rate) * 100, 1)
        transitions.append({
            "from": a_name, "to": b_name,
            "from_value": a_val, "to_value": b_val,
            "passthrough_pct": round(rate * 100, 2),
            "drop_pct": drop_pct,
        })

    # Identify worst stage (highest meaningful drop)
    # Skip sessions→first_step (always high — most sessions don't convert)
    # unless that's the only transition
    worst = None
    worst_score = -1.0
    for t in transitions:
        # Severity weighting: drops in later stages matter more (smaller funnels)
        weight = 1.0 if t["from"] == "sessions" else 2.0
        score = t["drop_pct"] * weight
        if score > worst_score:
            worst_score = score
            worst = t

    # Code selection
    code = "funnel_healthy"
    severity = "low"
    prescriptions: list[str] = []
    if not success and sessions > 100:
        code = "submit_failure_dominant"
        severity = "high"
        prescriptions = [
            "Site có sessions nhưng 0 conversion — kiểm tra engine snippet đã paste vào website chưa",
            "GTM container đã Publish chưa? (Save version != Publish)",
            "Test thực tế: submit 1 form, xem GA4 DebugView có conversion_success không",
        ]
    elif worst and worst["from"] == "sessions" and worst["drop_pct"] > 99 and len(transitions) > 1:
        # First stage drop > 99% but later stages exist — fine
        code = "funnel_healthy"
        severity = "low"
    elif worst and worst["from"] == "funnel_steps" and worst["drop_pct"] > 70:
        code = "popup_no_submit_spike"
        severity = "high"
        prescriptions = [
            "Tỉ lệ click popup nhưng không submit form quá cao — kiểm tra UX popup",
            "Form trong popup có quá dài, quá nhiều field? Thử simplify",
            "A/B test CTA copy + form layout",
        ]
    elif worst and worst["from"] == "interactions" and worst["drop_pct"] > 50:
        code = "form_abandonment_high"
        severity = "medium"
        prescriptions = [
            "User bắt đầu nhập form nhưng không submit — abandonment cao",
            "Check validation error: field nào hay báo lỗi?",
            "Auto-save partial data, hoặc giảm số field bắt buộc",
        ]
    elif worst and worst["from"] == "attempts" and worst["drop_pct"] > 30:
        code = "submit_failure_dominant"
        severity = "high"
        prescriptions = [
            "Nhiều attempt nhưng không thành công — check failure_postmortem chi tiết",
            "Có thể: backend lỗi, validation chặn, hoặc timeout",
        ]
    elif funnel_steps == 0 and interactions == 0 and success > 0:
        # Direct conversions only (no funnel_step/interaction tracking)
        code = "funnel_healthy"
        severity = "low"
        prescriptions = [
            "Site dùng trigger trực tiếp (url_contains/click_class) — không có funnel_step/interaction để diagnose chiều sâu",
            "Để có insight sâu hơn: thêm form có trigger dom_change để track form_interaction",
        ]
    else:
        code = "funnel_healthy"
        severity = "low"

    return {
        "code": code,
        "severity": severity,
        "headline": (
            f"Funnel drop lớn nhất: {worst['from']}→{worst['to']} mất {worst['drop_pct']}%"
            if worst and worst["from"] != "sessions" else
            f"Funnel có {success} conversion từ {sessions} sessions (CR {_safe_pct(success, sessions, 2)}%)"
        ),
        "signals": {
            "sessions": sessions,
            "funnel_steps": funnel_steps,
            "interactions": interactions,
            "attempts": attempts,
            "conversions": success,
            "site_cr_pct": _safe_pct(success, sessions, 2),
            "biggest_drop_stage": f"{worst['from']}_to_{worst['to']}" if worst else None,
            "biggest_drop_pct": worst["drop_pct"] if worst else None,
        },
        "evidence": {"transitions": transitions},
        "prescriptions": prescriptions,
    }


# ─── 2. analyze_form_triage ────────────────────────────────────────────────

def analyze_form_triage(data: dict, form_filter: str | None = None) -> dict:
    """Per-form CR ranking + leakage score (interactions ÷ attempts)."""
    forms_agg = _aggregate_per_form(data.get("per_form_daily", []))

    if form_filter:
        forms_agg = {k: v for k, v in forms_agg.items() if k == form_filter}

    forms = []
    for cid, f in forms_agg.items():
        attempts = f["success"] + f["fail"]
        cr_pct = _safe_pct(f["success"], attempts, 1)
        leakage = _safe_ratio(f["interactions"], attempts, 2) if attempts else (
            999.0 if f["interactions"] > 0 else 0.0
        )
        forms.append({
            "conversion_id": cid,
            "trigger_type": f["trigger_type"],
            "success": f["success"],
            "fail": f["fail"],
            "attempts": attempts,
            "interactions": f["interactions"],
            "cr_pct": cr_pct,
            "leakage_score": leakage,
        })

    forms.sort(key=lambda x: x["success"], reverse=True)

    # Per-form code
    crs = [f["cr_pct"] for f in forms if f["attempts"] > 0]
    cr_top_quartile = (
        statistics.quantiles(crs, n=4)[-1] if len(crs) >= 4 else (max(crs) if crs else 0)
    )

    for f in forms:
        if f["attempts"] == 0 and f["interactions"] > 0:
            f["code"] = "form_zero_attempts"
            f["severity"] = "high"
        elif f["attempts"] == 0 and f["interactions"] == 0 and f["success"] == 0:
            f["code"] = "form_no_data"
            f["severity"] = "medium"
        elif f["leakage_score"] > 3:
            f["code"] = "form_leaky"
            f["severity"] = "high"
        elif f["cr_pct"] >= cr_top_quartile and f["attempts"] > 0:
            f["code"] = "form_top_performer"
            f["severity"] = "low"
        else:
            f["code"] = "form_neutral"
            f["severity"] = "low"

    # Aggregate diagnosis
    worst = next((f for f in forms if f["severity"] == "high"), None)
    code = worst["code"] if worst else (
        "form_top_performer" if forms and forms[0]["code"] == "form_top_performer"
        else "form_no_data" if not forms else "form_neutral"
    )
    severity = worst["severity"] if worst else "low"

    prescriptions: list[str] = []
    if code == "form_leaky":
        prescriptions = [
            f"Form `{worst['conversion_id']}` có {worst['interactions']} interaction nhưng chỉ {worst['attempts']} attempt — leakage cao",
            "Check field nào hay bị bỏ giữa chừng (heatmap, session recording)",
            "Simplify form: giảm field, dùng autofill, auto-save partial",
        ]
    elif code == "form_zero_attempts":
        prescriptions = [
            f"Form `{worst['conversion_id']}` có {worst['interactions']} interaction nhưng 0 attempt — engine không bắt được submit",
            "Verify success selector match đúng element xuất hiện sau submit",
            "Test thủ công + GTM Preview: submit form, check conversion_success có fire không",
        ]
    elif code == "form_no_data":
        prescriptions = [
            "Form configured nhưng chưa có event nào — engine có thể chưa publish hoặc form chưa hoạt động",
            "Kiểm tra: GTM container đã Publish? Engine snippet đã paste vào site?",
        ]

    return {
        "code": code,
        "severity": severity,
        "headline": (
            f"{len(forms)} form(s) được track; top: `{forms[0]['conversion_id']}` ({forms[0]['success']} conv, CR {forms[0]['cr_pct']}%)"
            if forms else "Chưa có data form nào"
        ),
        "signals": {
            "form_count": len(forms),
            "top_form": forms[0]["conversion_id"] if forms else None,
            "top_form_cr_pct": forms[0]["cr_pct"] if forms else 0,
            "worst_code": code,
        },
        "evidence": {"forms": forms[:20]},
        "prescriptions": prescriptions,
    }


# ─── 3. analyze_failures ───────────────────────────────────────────────────

_FAIL_PRESCRIPTIONS = {
    "timeout": [
        "Tăng timeout threshold (default 15s) lên 30s nếu form gọi API chậm",
        "Check response time của backend (Hubspot/CF7/...)",
        "Nếu thank-you trigger: verify success element render kịp trong window",
    ],
    "stale_attempt": [
        "User mở form rồi đóng tab giữa chừng — bình thường, không nguy cấp",
        "Nếu tỉ lệ cao bất thường: check trang load chậm hoặc form bị che",
    ],
    "validation_error": [
        "User submit nhưng bị validation chặn — check field nào hay bị lỗi",
        "Improve inline validation (báo lỗi ngay khi gõ, không đợi submit)",
        "Giảm số required field, dùng smart defaults",
    ],
    "popup_no_submit": [
        "Click popup nhưng không submit — UX popup có vấn đề",
        "Form trong popup quá dài? Thử simplify hoặc step-by-step",
        "A/B test CTA + form layout",
    ],
    "chat_closed_no_message": [
        "Mở chat nhưng đóng mà không gửi tin — UX chat hoặc thời gian phản hồi",
        "Check agent response time (mở chat thấy không có ai trả lời ngay → đóng)",
        "Hiển thị status \"Đang offline\" rõ ràng nếu ngoài giờ",
    ],
    "form_abandoned": [
        "User focus vào form nhưng không submit — bỏ giữa chừng",
        "Auto-save partial data; gửi email reminder nếu có email",
        "Giảm friction: bỏ field không cần, dùng autofill",
    ],
}


def analyze_failures(data: dict) -> dict:
    """Breakdown by cro_fail_reason with prescriptive fix per dominant code."""
    failures_daily = data.get("failures_daily", [])
    if not failures_daily:
        return {
            "code": "failures_balanced",
            "severity": "low",
            "headline": "Chưa có failure nào được ghi nhận",
            "signals": {"total_failures": 0, "top_reason": None, "top_reason_pct": 0},
            "evidence": {"breakdown": []},
            "prescriptions": [],
        }

    by_reason: dict[str, int] = defaultdict(int)
    for r in failures_daily:
        by_reason[r.get("reason", "(unknown)")] += int(r.get("count", 0) or 0)

    total = sum(by_reason.values())
    breakdown = sorted(
        [{"reason": k, "count": v, "pct": _safe_pct(v, total, 1)} for k, v in by_reason.items()],
        key=lambda x: x["count"], reverse=True,
    )

    top = breakdown[0]
    if top["pct"] > 40:
        # Map reason → dominant code
        code_map = {
            "timeout": "timeout_dominant",
            "stale_attempt": "stale_attempt_dominant",
            "validation_error": "validation_dominant",
            "popup_no_submit": "popup_no_submit_dominant",
            "chat_closed_no_message": "chat_closed_no_message_dominant",
            "form_abandoned": "form_abandoned_dominant",
        }
        code = code_map.get(top["reason"], "failures_balanced")
        severity_map = {
            "timeout_dominant": "high",
            "validation_dominant": "medium",
            "stale_attempt_dominant": "medium",
            "popup_no_submit_dominant": "high",
            "chat_closed_no_message_dominant": "medium",
            "form_abandoned_dominant": "medium",
        }
        severity = severity_map.get(code, "low")
        prescriptions = _FAIL_PRESCRIPTIONS.get(top["reason"], [])
    else:
        code = "failures_balanced"
        severity = "low"
        prescriptions = []

    return {
        "code": code,
        "severity": severity,
        "headline": f"{total} failure tổng, top reason: `{top['reason']}` ({top['pct']}%)",
        "signals": {
            "total_failures": total,
            "top_reason": top["reason"],
            "top_reason_count": top["count"],
            "top_reason_pct": top["pct"],
        },
        "evidence": {"breakdown": breakdown},
        "prescriptions": prescriptions,
    }


# ─── 4. analyze_channel_roi ────────────────────────────────────────────────

def analyze_channel_roi(data: dict, channel_filter: str | None = None) -> dict:
    """CR per channel/source/medium; top + bottom 5."""
    source_daily = data.get("source_daily", [])
    channel_sessions = data.get("channel_sessions_daily", [])
    summary = data.get("summary", {})
    site_avg_cr = float(summary.get("site_conversion_rate_pct", 0)) / 100.0

    # Sum conversions per channel_group
    conv_by_channel: dict[str, int] = defaultdict(int)
    for r in source_daily:
        ch = r.get("channel_group", "(other)") or "(other)"
        conv_by_channel[ch] += int(r.get("count", 0) or 0)

    # Sum sessions per channel_group
    sess_by_channel: dict[str, int] = defaultdict(int)
    for r in channel_sessions:
        ch = r.get("channel_group", "(other)") or "(other)"
        sess_by_channel[ch] += int(r.get("sessions", 0) or 0)

    channels: dict[str, set[str]] = set(conv_by_channel.keys()) | set(sess_by_channel.keys())
    rows = []
    days = _date_range_days(data.get("meta", {}))

    for ch in channels:
        sess = sess_by_channel.get(ch, 0)
        conv = conv_by_channel.get(ch, 0)
        cr_pct = _safe_pct(conv, sess, 2)
        cr_ratio_to_site = (cr_pct / 100.0) / site_avg_cr if site_avg_cr else 0
        # Estimated lift if this channel matched site avg
        if site_avg_cr > 0 and sess > 0 and cr_pct < site_avg_cr * 100:
            estimated_lift_per_month = round(
                (site_avg_cr - cr_pct / 100.0) * sess * 30 / days
            )
        else:
            estimated_lift_per_month = 0
        rows.append({
            "channel_group": ch,
            "sessions": sess,
            "conversions": conv,
            "cr_pct": cr_pct,
            "cr_ratio_to_site_avg": round(cr_ratio_to_site, 2),
            "estimated_lift_per_month": estimated_lift_per_month,
        })

    if channel_filter:
        rows = [r for r in rows if r["channel_group"] == channel_filter]

    # Tag each channel with a code
    for r in rows:
        if r["sessions"] > 500 and r["conversions"] == 0:
            r["code"] = "channel_zero_conversions"
            r["severity"] = "high"
        elif r["sessions"] > 200 and r["cr_ratio_to_site_avg"] < 0.3 and r["sessions"] > 0:
            r["code"] = "channel_underperforming"
            r["severity"] = "high"
        elif r["sessions"] > 200 and r["cr_ratio_to_site_avg"] > 1.5:
            r["code"] = "channel_top_performer"
            r["severity"] = "low"
        else:
            r["code"] = "channel_neutral"
            r["severity"] = "low"

    rows.sort(key=lambda x: x["sessions"], reverse=True)
    top5 = rows[:5]

    # Worst channel (highest severity + estimated_lift)
    worst = max(
        (r for r in rows if r["severity"] == "high"),
        key=lambda x: x["estimated_lift_per_month"],
        default=None,
    )
    code = worst["code"] if worst else "channel_neutral"
    severity = worst["severity"] if worst else "low"
    headline = (
        f"Channel `{worst['channel_group']}`: {worst['sessions']} sessions, CR {worst['cr_pct']}% (site avg {round(site_avg_cr*100,2)}%) — lift dự kiến ~{worst['estimated_lift_per_month']} conv/tháng"
        if worst else
        f"{len(rows)} channel(s), top traffic: `{top5[0]['channel_group']}` ({top5[0]['sessions']} sessions)" if top5 else "Chưa có data channel"
    )

    prescriptions: list[str] = []
    if code == "channel_zero_conversions":
        prescriptions = [
            f"Channel `{worst['channel_group']}` có {worst['sessions']} sessions nhưng 0 conversion — landing page mismatch?",
            "Kiểm tra: landing pages của channel này có CTA rõ chưa? Match search intent chưa?",
            "Test thử campaign này: click ad → landing → form, xem chỗ nào leak",
        ]
    elif code == "channel_underperforming":
        prescriptions = [
            f"Channel `{worst['channel_group']}` CR ({worst['cr_pct']}%) thấp hơn site avg ({round(site_avg_cr*100,2)}%) nhiều",
            "Có thể: traffic quality kém (bot, click farm), hoặc landing page không match audience",
            "Audit landing page riêng cho channel này; A/B test variant",
        ]

    return {
        "code": code,
        "severity": severity,
        "headline": headline,
        "signals": {
            "channel_count": len(rows),
            "worst_channel": worst["channel_group"] if worst else None,
            "worst_cr_pct": worst["cr_pct"] if worst else None,
            "estimated_lift_per_month": worst["estimated_lift_per_month"] if worst else 0,
            "site_avg_cr_pct": round(site_avg_cr * 100, 2),
        },
        "evidence": {"top_5_by_traffic": top5, "all_channels": rows},
        "prescriptions": prescriptions,
    }


# ─── 5. analyze_anomaly ────────────────────────────────────────────────────

def analyze_anomaly(data: dict) -> dict:
    """Period-over-period delta + z-score on daily conversions."""
    timeline = data.get("timeline", [])
    summary = data.get("summary", {})
    prev = data.get("prev_summary", {})

    current_conv = int(summary.get("total_conversions", 0))
    prev_conv = int(prev.get("conversions", 0))
    pop_delta_pct = (
        round((current_conv - prev_conv) / prev_conv * 100, 1)
        if prev_conv else (None if current_conv == 0 else 9999.0)
    )

    # Z-score on daily conversion counts
    daily_conv = [int(t.get("conversion_success", 0) or 0) for t in timeline]
    daily_fail = [int(t.get("conversion_attempt_failed", 0) or 0) for t in timeline]
    daily_int = [int(t.get("form_interaction", 0) or 0) for t in timeline]

    z_anomalies = []
    if len(daily_conv) >= 7:
        mean = statistics.mean(daily_conv)
        std = statistics.stdev(daily_conv) if len(daily_conv) > 1 else 0
        if std > 0:
            for t, v in zip(timeline, daily_conv):
                z = (v - mean) / std
                if abs(z) >= 2.0:
                    z_anomalies.append({
                        "date": t.get("date"), "value": v, "z_score": round(z, 2),
                        "rolling_mean": round(mean, 2), "stddev": round(std, 2),
                    })

    # Pick top-severity anomaly
    code = "no_anomaly"
    severity = "low"
    headline = "Không phát hiện bất thường rõ rệt"
    prescriptions: list[str] = []
    signals: dict[str, Any] = {
        "current_period_conversions": current_conv,
        "prev_period_conversions": prev_conv,
        "pop_delta_pct": pop_delta_pct,
        "z_anomaly_count": len(z_anomalies),
        "z_anomalies": z_anomalies[:5],
    }

    # PoP rules
    if pop_delta_pct is not None and prev_conv > 0:
        if pop_delta_pct <= -25:
            code = "anomaly_conversion_drop"
            severity = "high"
            headline = f"Conversions tụt {abs(pop_delta_pct)}% so với kỳ trước ({prev_conv} → {current_conv})"
            prescriptions = [
                "Kiểm tra: GTM container có bị unpublish? Engine snippet còn trên site?",
                "Check daily timeline (z_anomalies) để xem tụt từ ngày nào",
                "Diff với ngày tụt: deploy/release/marketing change nào trùng thời điểm?",
            ]
        elif pop_delta_pct >= 25:
            code = "anomaly_conversion_spike"
            severity = "low"
            headline = f"Conversions tăng {pop_delta_pct}% so với kỳ trước ({prev_conv} → {current_conv})"
            prescriptions = [
                "Tăng vọt — xác minh không phải bug double-fire event",
                "Tìm driver: traffic mới? Campaign chạy? Engine fix?",
            ]

    # Z-score rules (override only if more severe)
    drops = [a for a in z_anomalies if a["z_score"] < -2]
    spikes_fail = []  # would need separate computation; skip for v1 simplicity
    if drops and code in ("no_anomaly", "anomaly_conversion_spike"):
        worst_drop = min(drops, key=lambda x: x["z_score"])
        code = "anomaly_conversion_drop"
        severity = "high"
        headline = f"Ngày {worst_drop['date']} conversions tụt mạnh (z={worst_drop['z_score']}, value {worst_drop['value']} vs avg {worst_drop['rolling_mean']})"
        prescriptions = [
            f"Ngày {worst_drop['date']} có gì khác thường? Deploy / outage / marketing pause?",
            "Check GA4 DebugView ngày đó: events có fire không?",
        ]

    return {
        "code": code,
        "severity": severity,
        "headline": headline,
        "signals": signals,
        "evidence": {
            "timeline_sample": timeline[-7:] if timeline else [],
            "z_anomalies": z_anomalies,
        },
        "prescriptions": prescriptions,
    }


# ─── Health score aggregator ───────────────────────────────────────────────

def _severity_to_score(severity: str) -> int:
    return {"high": 30, "medium": 60, "low": 90}.get(severity, 70)


def compute_health_score(analyzer_results: dict) -> dict:
    """Weighted aggregation of sub-scores derived from analyzer severities."""
    funnel = _severity_to_score(
        analyzer_results.get("funnel_diagnostic", {}).get("severity", "low")
    )
    form_quality = _severity_to_score(
        analyzer_results.get("form_triage", {}).get("severity", "low")
    )
    reliability = _severity_to_score(
        analyzer_results.get("failure_postmortem", {}).get("severity", "low")
    )
    # Trend: anomaly_drop hurts; spike doesn't help; no_anomaly = neutral
    anomaly = analyzer_results.get("anomaly_detector", {})
    if anomaly.get("code") == "anomaly_conversion_drop":
        trend = 30
    elif anomaly.get("code") == "anomaly_conversion_spike":
        trend = 90
    else:
        trend = 75

    overall = round((funnel + form_quality + reliability + trend) / 4)
    if overall >= 85:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 55:
        grade = "C"
    elif overall >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "overall": overall, "grade": grade,
        "funnel": funnel, "form_quality": form_quality,
        "reliability": reliability, "trend": trend,
    }


# ─── Ranking helpers ───────────────────────────────────────────────────────

_SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}


def rank_top_issues(analyzer_results: dict, k: int = 3) -> list[dict]:
    """Pick top-K issues across all analyzers, ranked by severity then impact."""
    items = []
    for analyzer_name, result in analyzer_results.items():
        sev = result.get("severity", "low")
        # Skip positive/low signals from "issues" list
        if sev == "low" and "positive" not in result.get("code", ""):
            # Skip purely informational "low" codes from issue list
            if result.get("code") in ("funnel_healthy", "form_neutral", "failures_balanced",
                                       "channel_neutral", "no_anomaly",
                                       "form_top_performer", "channel_top_performer",
                                       "anomaly_conversion_spike"):
                continue
        items.append({
            "analyzer": analyzer_name,
            "code": result["code"],
            "severity": sev,
            "headline": result.get("headline", ""),
            "signals": result.get("signals", {}),
            "prescriptions": result.get("prescriptions", []),
        })
    items.sort(key=lambda x: _SEVERITY_RANK.get(x["severity"], 0), reverse=True)
    return [{"rank": i + 1, **it} for i, it in enumerate(items[:k])]


def rank_top_opportunities(analyzer_results: dict, k: int = 3) -> list[dict]:
    """Pick top-K opportunities by potential lift."""
    items = []
    channel = analyzer_results.get("channel_roi", {})
    for r in channel.get("evidence", {}).get("all_channels", []):
        if r.get("estimated_lift_per_month", 0) > 0:
            items.append({
                "analyzer": "channel_roi",
                "code": "channel_underperforming" if r.get("code") == "channel_underperforming" else r.get("code", "channel_neutral"),
                "headline": f"Channel `{r['channel_group']}`: {r['sessions']} sessions, CR {r['cr_pct']}% — nâng lên site avg = +{r['estimated_lift_per_month']} conv/tháng",
                "estimated_lift_per_month": r["estimated_lift_per_month"],
                "signals": {
                    "channel_group": r["channel_group"],
                    "sessions": r["sessions"],
                    "current_cr_pct": r["cr_pct"],
                    "lift_per_month": r["estimated_lift_per_month"],
                },
            })

    # Top forms also count as "amplify what works" opportunities
    forms = analyzer_results.get("form_triage", {}).get("evidence", {}).get("forms", [])
    top_form = next((f for f in forms if f.get("code") == "form_top_performer"), None)
    if top_form:
        items.append({
            "analyzer": "form_triage",
            "code": "form_top_performer",
            "headline": f"Form `{top_form['conversion_id']}` đang chạy tốt (CR {top_form['cr_pct']}%, {top_form['success']} conv) — nhân rộng pattern này sang form khác",
            "estimated_lift_per_month": 0,
            "signals": {
                "conversion_id": top_form["conversion_id"],
                "cr_pct": top_form["cr_pct"],
                "success": top_form["success"],
            },
        })

    # Anomaly spike = opportunity to investigate driver
    anomaly = analyzer_results.get("anomaly_detector", {})
    if anomaly.get("code") == "anomaly_conversion_spike":
        items.append({
            "analyzer": "anomaly_detector",
            "code": "anomaly_conversion_spike",
            "headline": anomaly.get("headline", ""),
            "estimated_lift_per_month": 0,
            "signals": anomaly.get("signals", {}),
        })

    items.sort(key=lambda x: x.get("estimated_lift_per_month", 0), reverse=True)
    return [{"rank": i + 1, **it} for i, it in enumerate(items[:k])]
