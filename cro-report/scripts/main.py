"""Top-level orchestrator for /cro-report.

Subcommands:
  list-profiles    Print JSON of available profiles (cro-setup + standalone)
  generate         Fetch GA4 data → bake into HTML → optionally open in browser
  deploy           One-time setup: install skill + crontab on remote SSH host
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import webbrowser
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import auth as auth_module
import config as cfg_module
import ga4_fetcher
import report_builder


LAST_RUN_PATH = SKILL_DIR / "last_run.json"


def _out(data: dict, exit_code: int = 0):
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def _save_last_run(profile: str, date_preset: str | None,
                   start: str | None, end: str | None) -> None:
    LAST_RUN_PATH.write_text(json.dumps({
        "profile": profile,
        "date_preset": date_preset,
        "start": start,
        "end": end,
    }, indent=2))


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


def cmd_generate(args):
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
            start_date=args.start,
            end_date=args.end,
        )
    except Exception as e:
        _out({"ok": False, "error": f"GA4 fetch failed: {e}"}, exit_code=1)

    client_name = profile_cfg.get("client_name") or args.profile

    try:
        out_path = report_builder.build(
            profile_name=args.profile,
            data=data,
            client_name=client_name,
            output_path=args.output,
        )
    except Exception as e:
        _out({"ok": False, "error": f"Report build failed: {e}"}, exit_code=1)

    if not args.output:
        # Don't overwrite last_run when called from cron with --output (would
        # spam last_run with the same entry every cron tick).
        _save_last_run(args.profile, args.date_range, args.start, args.end)

    opened = False
    if args.open and not args.output:
        try:
            webbrowser.open(f"file://{out_path.absolute()}")
            opened = True
        except Exception:
            pass

    warnings = _dedup_warnings(data["meta"].get("warnings", []))

    _out({
        "ok": True,
        "profile": args.profile,
        "client_name": client_name,
        "report_path": str(out_path),
        "file_url": f"file://{out_path.absolute()}",
        "opened": opened,
        "date_range": data["meta"]["date_range"],
        "summary": data["summary"],
        "warnings": warnings,
        "source": profile_cfg.get("_source"),
    })


def _slug(s: str) -> str:
    import re
    s = (s or "report").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "report"


def _ssh(host: str, cmd: str, *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", host, cmd], capture_output=True, text=True, check=check)


def _rsync(src: str, dest: str, *, extra: list[str] | None = None) -> subprocess.CompletedProcess:
    args = ["rsync", "-az", "--delete"] + (extra or []) + [src, dest]
    return subprocess.run(args, capture_output=True, text=True, check=True)


def cmd_deploy(args):
    """Push skill + credentials to remote, install crontab.

    Layout on remote:
      ~/cro-report-server/              ← skill copy
        scripts/, templates/, install.py, requirements.txt
        accounts.json                   ← scoped to single profile
        credentials/<profile>.json      ← OAuth refresh token
        .venv/                          ← created on first install
    Crontab entry:
      <CRON_SCHEDULE>  cd ~/cro-report-server && .venv/bin/python scripts/main.py generate --profile X --date-range X --output WEBROOT/REPORT.html --no-open >> ~/cro-report-server/cron.log 2>&1
    """
    try:
        profile_cfg = cfg_module.load_profile(args.profile)
    except Exception as e:
        _out({"ok": False, "error": str(e)}, exit_code=1)

    creds_path = Path(profile_cfg["credentials_path"])
    if not creds_path.exists():
        _out({"ok": False,
              "error": f"Credentials missing: {creds_path}. "
                       f"Run a local 'generate' first to refresh the token."},
             exit_code=1)

    report_name = args.report_name or f"{_slug(args.profile)}.html"
    remote_dir = "~/cro-report-server"
    remote_creds_dir = f"{remote_dir}/credentials"
    remote_report = f"{args.webroot.rstrip('/')}/{report_name}"

    cron_cmd = (
        f"cd {remote_dir} && .venv/bin/python scripts/main.py generate "
        f"--profile {shlex.quote(args.profile)} "
        f"--date-range {args.date_range} "
        f"--output {shlex.quote(remote_report)} --no-open "
        f"> {remote_dir}/cron.log 2>&1"
    )
    crontab_line = f"{args.cron}  {cron_cmd}"

    plan = {
        "ssh_host": args.ssh_host,
        "remote_skill_dir": remote_dir,
        "remote_webroot": args.webroot,
        "remote_report_path": remote_report,
        "public_url": (f"{args.public_url.rstrip('/')}/{report_name}"
                       if args.public_url else None),
        "cron_schedule": args.cron,
        "crontab_line": crontab_line,
        "profile": args.profile,
    }

    if args.dry_run:
        _out({"ok": True, "dry_run": True, "plan": plan})

    steps_log: list[dict] = []

    def _step(name: str, fn):
        try:
            result = fn()
            steps_log.append({"step": name, "ok": True})
            return result
        except subprocess.CalledProcessError as e:
            steps_log.append({"step": name, "ok": False,
                              "stderr": (e.stderr or "")[-500:],
                              "stdout": (e.stdout or "")[-200:]})
            _out({"ok": False, "error": f"Step '{name}' failed",
                  "steps": steps_log, "plan": plan}, exit_code=1)
        except Exception as e:
            steps_log.append({"step": name, "ok": False, "error": str(e)})
            _out({"ok": False, "error": f"Step '{name}' failed: {e}",
                  "steps": steps_log, "plan": plan}, exit_code=1)

    # 1. Ensure remote dirs exist
    _step("create_remote_dirs",
          lambda: _ssh(args.ssh_host,
                       f"mkdir -p {remote_dir}/credentials "
                       f"{remote_dir}/reports {args.webroot}"))

    # 2. rsync skill files (exclude local-only artifacts)
    src = str(SKILL_DIR) + "/"
    excludes = ["--exclude=.venv", "--exclude=reports/",
                "--exclude=credentials/", "--exclude=accounts.json",
                "--exclude=last_run.json", "--exclude=oauth_client.json",
                "--exclude=__pycache__"]
    _step("rsync_skill_files",
          lambda: _rsync(src, f"{args.ssh_host}:{remote_dir}/", extra=excludes))

    # 3. Build a single-profile accounts.json on the remote (so server-side
    #    list_all_profiles returns just this profile)
    accounts_payload = {
        "default": args.profile,
        "profiles": {
            args.profile: {
                "client_name": profile_cfg.get("client_name", ""),
                "ga4_property_id": profile_cfg.get("ga4_property_id", ""),
                "ga4_measurement_id": profile_cfg.get("ga4_measurement_id", ""),
                "credentials_path": f"credentials/{args.profile}.json",
            }
        }
    }
    payload_str = json.dumps(accounts_payload)
    _step("write_remote_accounts",
          lambda: _ssh(args.ssh_host,
                       f"cat > {remote_dir}/accounts.json << 'JSON_EOF'\n"
                       f"{payload_str}\nJSON_EOF"))

    # 4. Upload OAuth credentials (refresh token)
    _step("upload_credentials",
          lambda: _rsync(str(creds_path),
                         f"{args.ssh_host}:{remote_creds_dir}/{args.profile}.json"))

    # 5. Upload oauth_client.json if available (needed for refresh)
    oauth_client_local = SKILL_DIR / "oauth_client.json"
    cro_setup_oauth = Path.home() / ".claude/skills/cro-setup/oauth_client.json"
    src_oauth = oauth_client_local if oauth_client_local.exists() else cro_setup_oauth
    if src_oauth.exists():
        _step("upload_oauth_client",
              lambda: _rsync(str(src_oauth),
                             f"{args.ssh_host}:{remote_dir}/oauth_client.json"))

    # 6. Install Python venv on remote
    _step("install_remote_venv",
          lambda: _ssh(args.ssh_host,
                       f"cd {remote_dir} && (python3 install.py || python install.py)",
                       check=False))

    # 7. Smoke-test: run generate once on remote
    _step("smoke_generate",
          lambda: _ssh(args.ssh_host,
                       f"cd {remote_dir} && .venv/bin/python scripts/main.py generate "
                       f"--profile {shlex.quote(args.profile)} "
                       f"--date-range {args.date_range} "
                       f"--output {shlex.quote(remote_report)} --no-open"))

    # 8. Install crontab entry (idempotent — replace any existing line with same OUTPUT path)
    marker = f"# cro-report:{report_name}"
    install_cron = (
        f"(crontab -l 2>/dev/null | grep -v '{marker}' ; "
        f"echo '{crontab_line}  {marker}') | crontab -"
    )
    _step("install_crontab",
          lambda: _ssh(args.ssh_host, install_cron))

    _out({"ok": True, "plan": plan, "steps": steps_log,
          "next": "Mở URL public để xem report. Cron sẽ tự update mỗi "
                  f"{args.cron}. Log: {remote_dir}/cron.log"})


def _dedup_warnings(warnings: list[str]) -> list[str]:
    """Collapse identical errors across multiple queries into a single warning."""
    if not warnings:
        return []
    bodies: dict[str, list[str]] = {}
    for w in warnings:
        prefix, _, body = w.partition(":")
        body = body.strip()
        bodies.setdefault(body, []).append(prefix.strip())
    out = []
    for body, prefixes in bodies.items():
        if len(prefixes) > 1:
            out.append(f"[{len(prefixes)} queries failed] {body}")
        else:
            out.append(f"{prefixes[0]}: {body}")
    return out


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-profiles", help="List all profiles (cro-setup + standalone)")

    p_gen = sub.add_parser("generate", help="Fetch GA4 → build HTML report")
    p_gen.add_argument("--profile", required=True)
    p_gen.add_argument("--date-range",
                       choices=["last_7_days", "last_30_days", "last_90_days"],
                       default="last_30_days")
    p_gen.add_argument("--start", help="YYYY-MM-DD (use with --end for custom range)")
    p_gen.add_argument("--end", help="YYYY-MM-DD")
    p_gen.add_argument("--open", action="store_true",
                       help="Auto-open generated report in default browser")
    p_gen.add_argument("--no-open", dest="open", action="store_false")
    p_gen.set_defaults(open=True)
    p_gen.add_argument("--output",
                       help="Write report to this exact path (overwrite). "
                            "Use for cron-driven runs that need a stable URL.")

    p_dep = sub.add_parser("deploy",
        help="One-time: install skill + cron on remote SSH host. "
             "Subsequent runs will be driven by the remote cron.")
    p_dep.add_argument("--profile", required=True,
                       help="Profile to use on remote (must exist locally)")
    p_dep.add_argument("--ssh-host", required=True,
                       help="SSH host alias or user@host (e.g. fsi)")
    p_dep.add_argument("--webroot", required=True,
                       help="Remote directory served by web server "
                            "(e.g. /var/www/btt.com.vn/cro-reports)")
    p_dep.add_argument("--public-url",
                       help="Public URL prefix (e.g. https://btt.com.vn/cro-reports). "
                            "Combined with --report-name to form the final URL")
    p_dep.add_argument("--report-name",
                       help="HTML filename on server (default: {profile-slug}.html)")
    p_dep.add_argument("--cron", default="0 */6 * * *",
                       help="Crontab schedule on remote (default: every 6 hours)")
    p_dep.add_argument("--date-range",
                       choices=["last_7_days", "last_30_days", "last_90_days"],
                       default="last_30_days")
    p_dep.add_argument("--dry-run", action="store_true",
                       help="Print plan, don't execute")

    args = parser.parse_args()
    {
        "list-profiles": cmd_list_profiles,
        "generate": cmd_generate,
        "deploy": cmd_deploy,
    }[args.command](args)


if __name__ == "__main__":
    main()
