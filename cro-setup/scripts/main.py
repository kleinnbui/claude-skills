"""Top-level orchestrator for /cro-setup.

Subcommands:
  build-engine    Generate engine HTML from JSON config — print to stdout
  preview         Dry-run: list CREATE/UPDATE/NO_OP for GTM + GA4 artifacts
  apply           Execute sync (creates GTM version, NO publish)
  save-config     Save user-provided JSON config to configs/{slug}.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import engine
import gtm_sync
import ga4_sync
import config as cfg_module


def _out(data: dict, exit_code: int = 0):
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def _load_config_file(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = SKILL_DIR / path
    with open(p) as f:
        return json.load(f)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "site"


def _gtm_ui_url(profile_cfg: dict, workspace_id: str | None = None) -> str:
    ws = workspace_id or profile_cfg.get("gtm_workspace_id", "")
    return (
        f"https://tagmanager.google.com/#/container"
        f"/accounts/{profile_cfg['gtm_account_id']}"
        f"/containers/{profile_cfg['gtm_container_id']}"
        f"/workspaces/{ws}"
    )


def _validate_and_enrich_config(cfg: dict) -> tuple[dict, list[str]]:
    """Validate config fields; auto-set requireAttempt when forms share a thank-you URL.

    Returns (enriched_cfg, warnings[]).
    """
    warnings: list[str] = []
    forms = cfg.get("forms", [])

    # Validate thankYouPath — must not contain query string
    for form in forms:
        if form.get("triggerType") == "thank_you_url":
            path = form.get("thankYouPath", "")
            if path and "?" in path:
                warnings.append(
                    f"Form '{form['name']}': thankYouPath '{path}' chứa '?' — "
                    "phần query string nên đặt vào trường 'thankYouParam', không phải thankYouPath. "
                    "Đã tự động tách ra."
                )
                parts = path.split("?", 1)
                form["thankYouPath"] = parts[0]
                # Try to extract first param name as thankYouParam hint
                if not form.get("thankYouParam") and "=" in parts[1]:
                    form["thankYouParam"] = parts[1].split("=")[0]

    # Auto-detect shared thank-you URL → set requireAttempt on all sharing forms
    thank_you_forms = [f for f in forms if f.get("triggerType") == "thank_you_url"]
    if len(thank_you_forms) >= 2:
        path_groups: dict[str, list[str]] = defaultdict(list)
        for f in thank_you_forms:
            key = f.get("thankYouPath") or f.get("thankYouParam") or ""
            if key:
                path_groups[key].append(f["name"])

        for key, names in path_groups.items():
            if len(names) >= 2:
                for form in forms:
                    if form.get("name") in names and not form.get("requireAttempt"):
                        form["requireAttempt"] = True
                        others = [n for n in names if n != form["name"]]
                        warnings.append(
                            f"Auto-set requireAttempt=true cho form '{form['name']}' "
                            f"(dùng chung thank-you URL với {others} — tránh double-fire)."
                        )

    return cfg, warnings


def cmd_build_engine(args):
    cfg = _load_config_file(args.config)
    print(engine.build_engine_html(cfg))


def cmd_preview(args):
    try:
        wizard_cfg = _load_config_file(args.config)
        profile_cfg = cfg_module.load_config(args.profile)
        gtm_plan = gtm_sync.preview(profile_cfg)
        ga4_plan = ga4_sync.preview(profile_cfg)
    except Exception as e:
        _out({"ok": False, "error": str(e)}, exit_code=1)

    engine_html = engine.build_engine_html(wizard_cfg)
    engine_size = len(engine_html)
    preview_warnings = gtm_plan.get("warnings", [])
    if engine_size > 100_000:
        preview_warnings.append(f"Engine HTML {engine_size // 1024}KB vượt ngưỡng khuyến nghị 100KB của GTM — xem xét giảm số lượng form/conversion.")

    summary = _summarize(gtm_plan["plan"] + ga4_plan["plan"])
    _out({
        "ok": True,
        "profile": profile_cfg["_profile_name"],
        "gtm_workspace_path": gtm_plan["workspace_path"],
        "gtm_url": _gtm_ui_url(profile_cfg),
        "ga4_property_path": ga4_plan["property_path"],
        "engine_size_bytes": engine_size,
        "summary": summary,
        "warnings": preview_warnings,
        "gtm_plan": gtm_plan["plan"],
        "ga4_plan": ga4_plan["plan"],
    })


def cmd_apply(args):
    try:
        wizard_cfg = _load_config_file(args.config)
        profile_cfg = cfg_module.load_config(args.profile)
        engine_html = engine.build_engine_html(wizard_cfg)

        if args.engine_only:
            gtm_result = gtm_sync.sync_engine_only(profile_cfg, engine_html)
            ga4_result = {"actions": []}
        else:
            gtm_result = gtm_sync.sync(profile_cfg, engine_html)
            ga4_result = ga4_sync.sync(profile_cfg)
    except Exception as e:
        _out({"ok": False, "error": str(e)}, exit_code=1)

    new_ws = gtm_result.get("new_workspace_id") or profile_cfg.get("gtm_workspace_id", "")
    gtm_url = _gtm_ui_url(profile_cfg, workspace_id=new_ws)

    summary = _summarize(gtm_result["actions"] + ga4_result["actions"])
    _out({
        "ok": True,
        "profile": profile_cfg["_profile_name"],
        "engine_only": bool(args.engine_only),
        "gtm": {
            "version_name": gtm_result["version_name"],
            "version_id": gtm_result["version_id"],
            "compiler_error": gtm_result.get("compiler_error", False),
            "actions": gtm_result["actions"],
            "gtm_url": gtm_url,
        },
        "ga4": {
            "actions": ga4_result["actions"],
        },
        "summary": summary,
        "next_steps": [
            f"GTM Preview: {gtm_url}",
            "Vào GTM → Preview (Tag Assistant) → load trang test → submit form thật → verify dataLayer event conversion_success",
            "QA xong → click Submit → Publish container thủ công",
            "GA4 → DebugView → submit form lại với ?gtm_debug=1 → verify event + 13 cro_* params",
            "Đợi 24-48h → check GA4 Reports → Events → conversion_success",
        ],
    })


def cmd_save_config(args):
    cfg = json.loads(sys.stdin.read())
    cfg, warnings = _validate_and_enrich_config(cfg)

    profile_cfg = cfg_module.load_config(args.profile)
    project = cfg.get("project", {})
    client_slug = _slug(project.get("clientName") or args.profile)
    out_dir = SKILL_DIR / "configs"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{profile_cfg['_profile_name']}-{client_slug}.json"
    with open(out_path, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    _out({"ok": True, "path": str(out_path), "warnings": warnings})


def _summarize(actions: list) -> dict:
    counts: dict[str, int] = {"CREATE": 0, "UPDATE": 0, "NO_OP": 0}
    for a in actions:
        counts[a["action"]] = counts.get(a["action"], 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("build-engine", help="Generate engine HTML from config JSON")
    p1.add_argument("--config", required=True)

    p2 = sub.add_parser("preview", help="Dry-run: show planned CREATE/UPDATE/NO_OP")
    p2.add_argument("--profile", required=True)
    p2.add_argument("--config", required=True)

    p3 = sub.add_parser("apply", help="Execute GTM + GA4 sync (NO publish)")
    p3.add_argument("--profile", required=True)
    p3.add_argument("--config", required=True)
    p3.add_argument(
        "--engine-only",
        action="store_true",
        help="Update only [CRO] Journey Tracker tag (skip DLVs / trigger / GA4)",
    )

    p4 = sub.add_parser("save-config",
                        help="Save JSON config (from stdin) to configs/")
    p4.add_argument("--profile", required=True)

    args = parser.parse_args()
    {
        "build-engine": cmd_build_engine,
        "preview": cmd_preview,
        "apply": cmd_apply,
        "save-config": cmd_save_config,
    }[args.command](args)


if __name__ == "__main__":
    main()
