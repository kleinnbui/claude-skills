"""Top-level orchestrator for /cro-analyst (v1 MVP).

Subcommands:
  list-profiles    Print JSON of available profiles (cro-setup + standalone)
  brief            Fetch GA4 → run 5 analyzers → return top issues + opportunities
  full             Same as brief but no top-K capping
  drill            Single analyzer (with optional dimension filter)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import auth as auth_module
import config as cfg_module
import ga4_fetcher
import analyzers as A


LAST_RUN_PATH = SKILL_DIR / "last_run.json"


def _out(data: dict, exit_code: int = 0):
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    sys.exit(exit_code)


def _save_last_run(profile: str, date_preset: str | None,
                   start: str | None, end: str | None) -> None:
    try:
        LAST_RUN_PATH.write_text(json.dumps({
            "profile": profile, "date_preset": date_preset,
            "start": start, "end": end,
        }, indent=2))
    except Exception:
        pass


def cmd_list_profiles(_args):
    profiles = cfg_module.list_all_profiles()
    default = cfg_module.get_default_profile_name()
    oauth_info = cfg_module.get_oauth_client_info()
    last_run = {}
    if LAST_RUN_PATH.exists():
        try:
            last_run = json.loads(LAST_RUN_PATH.read_text())
        except Exception:
            pass
    _out({
        "ok": True,
        "default": default,
        "oauth_client": oauth_info,
        "profiles": {
            name: {k: v for k, v in p.items() if k != "credentials_path"}
            for name, p in profiles.items()
        },
        "last_run": last_run,
    })


def _fetch_data(args) -> tuple[dict, dict]:
    """Returns (profile_cfg, fetched_data)."""
    try:
        profile_cfg = cfg_module.load_profile(args.profile)
    except Exception as e:
        _out({"ok": False, "error": str(e)}, exit_code=1)

    try:
        creds = auth_module.load_credentials(profile_cfg["credentials_path"])
    except Exception as e:
        _out({"ok": False, "error": f"Auth failed: {e}"}, exit_code=1)

    property_id = profile_cfg.get("ga4_property_id", "")
    if not property_id:
        _out({"ok": False, "error": f"Profile '{args.profile}' has no ga4_property_id"}, exit_code=1)

    try:
        data = ga4_fetcher.fetch_all(
            creds, property_id,
            date_preset=args.date_range,
            start_date=args.start, end_date=args.end,
        )
    except Exception as e:
        _out({"ok": False, "error": f"GA4 fetch failed: {e}"}, exit_code=1)

    return profile_cfg, data


def _run_all_analyzers(data: dict, form_filter: str | None = None,
                       channel_filter: str | None = None) -> dict:
    return {
        "funnel_diagnostic": A.analyze_funnel(data),
        "form_triage": A.analyze_form_triage(data, form_filter=form_filter),
        "failure_postmortem": A.analyze_failures(data),
        "channel_roi": A.analyze_channel_roi(data, channel_filter=channel_filter),
        "anomaly_detector": A.analyze_anomaly(data),
    }


def cmd_brief(args):
    t0 = time.time()
    profile_cfg, data = _fetch_data(args)
    analyzer_results = _run_all_analyzers(data)
    health = A.compute_health_score(analyzer_results)
    top_issues = A.rank_top_issues(analyzer_results, k=3)
    top_opportunities = A.rank_top_opportunities(analyzer_results, k=3)

    _save_last_run(args.profile, args.date_range, args.start, args.end)

    _out({
        "ok": True,
        "profile": args.profile,
        "client_name": profile_cfg.get("client_name") or args.profile,
        "source": profile_cfg.get("_source"),
        "date_range": data["meta"]["date_range"],
        "summary": data["summary"],
        "prev_summary": data.get("prev_summary"),
        "health_score": health,
        "top_issues": top_issues,
        "top_opportunities": top_opportunities,
        "analyzer_results": analyzer_results,
        "warnings": data["meta"].get("warnings", []),
        "duration_ms": int((time.time() - t0) * 1000),
    })


def cmd_full(args):
    t0 = time.time()
    profile_cfg, data = _fetch_data(args)
    analyzer_results = _run_all_analyzers(data)
    health = A.compute_health_score(analyzer_results)
    # Full mode: no top-K cap; expose ranked lists with more items
    top_issues = A.rank_top_issues(analyzer_results, k=20)
    top_opportunities = A.rank_top_opportunities(analyzer_results, k=20)

    _save_last_run(args.profile, args.date_range, args.start, args.end)

    _out({
        "ok": True,
        "mode": "full",
        "profile": args.profile,
        "client_name": profile_cfg.get("client_name") or args.profile,
        "source": profile_cfg.get("_source"),
        "date_range": data["meta"]["date_range"],
        "summary": data["summary"],
        "prev_summary": data.get("prev_summary"),
        "health_score": health,
        "top_issues": top_issues,
        "top_opportunities": top_opportunities,
        "analyzer_results": analyzer_results,
        "warnings": data["meta"].get("warnings", []),
        "duration_ms": int((time.time() - t0) * 1000),
    })


_ANALYZER_DISPATCH = {
    "funnel_diagnostic":  lambda d, args: A.analyze_funnel(d),
    "form_triage":        lambda d, args: A.analyze_form_triage(d, form_filter=args.form),
    "failure_postmortem": lambda d, args: A.analyze_failures(d),
    "channel_roi":        lambda d, args: A.analyze_channel_roi(d, channel_filter=args.channel),
    "anomaly_detector":   lambda d, args: A.analyze_anomaly(d),
}


def cmd_drill(args):
    if args.analyzer not in _ANALYZER_DISPATCH:
        _out({"ok": False,
              "error": f"Unknown analyzer '{args.analyzer}'. Valid: {', '.join(_ANALYZER_DISPATCH.keys())}"},
             exit_code=1)
    t0 = time.time()
    profile_cfg, data = _fetch_data(args)
    result = _ANALYZER_DISPATCH[args.analyzer](data, args)
    _out({
        "ok": True,
        "analyzer": args.analyzer,
        "profile": args.profile,
        "client_name": profile_cfg.get("client_name") or args.profile,
        "date_range": data["meta"]["date_range"],
        "summary": data["summary"],
        "filter": {"form": args.form, "channel": args.channel},
        "result": result,
        "duration_ms": int((time.time() - t0) * 1000),
    })


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list-profiles", help="List all profiles (cro-setup + standalone)")

    def _add_fetch_args(parser):
        parser.add_argument("--profile", required=True)
        parser.add_argument("--date-range",
                            choices=["last_7_days", "last_30_days", "last_90_days"],
                            default="last_30_days")
        parser.add_argument("--start", help="YYYY-MM-DD (use with --end for custom range)")
        parser.add_argument("--end", help="YYYY-MM-DD")

    p_brief = sub.add_parser("brief", help="Fetch GA4 → 5 analyzers → top 3 issues + opportunities")
    _add_fetch_args(p_brief)

    p_full = sub.add_parser("full", help="Same as brief but expose all flagged codes")
    _add_fetch_args(p_full)

    p_drill = sub.add_parser("drill", help="Single analyzer (with optional dimension filter)")
    _add_fetch_args(p_drill)
    p_drill.add_argument("--analyzer", required=True,
                         choices=list(_ANALYZER_DISPATCH.keys()))
    p_drill.add_argument("--form", help="Filter to one conversion_id (form_triage only)")
    p_drill.add_argument("--channel", help="Filter to one channel_group (channel_roi only)")

    args = p.parse_args()
    {
        "list-profiles": cmd_list_profiles,
        "brief":         cmd_brief,
        "full":          cmd_full,
        "drill":         cmd_drill,
    }[args.command](args)


if __name__ == "__main__":
    main()
