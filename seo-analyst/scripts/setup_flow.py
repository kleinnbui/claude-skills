"""Two-phase OAuth setup — designed to be orchestrated by Claude Code.

Subcommands:
  discover      Legacy: opens browser directly (CLI only)
  save          Save selected GA4/GSC into accounts.json
  auth-url      Generate OAuth URL for user to open (sandbox-friendly, step 1)
  auth-complete Complete OAuth from redirect URL user pastes back (step 2)
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import auth as auth_module
import config as cfg_module


def cmd_auth_url(args):
    """Generate OAuth URL — no browser opening, no blocking. Step 1 of 2."""
    try:
        result = auth_module.generate_auth_url(args.name)
        _out({"ok": True, "profile_name": args.name, **result})
    except Exception as e:
        _out({"ok": False, "error": str(e)})
        sys.exit(1)


def cmd_auth_complete(args):
    """Complete OAuth from redirect URL user pasted. Step 2 of 2."""
    try:
        token_path = auth_module.complete_auth(args.name, args.redirect_url)
    except Exception as e:
        _out({"ok": False, "error": str(e)})
        sys.exit(1)
    try:
        creds = auth_module.load_credentials(token_path)
    except Exception as e:
        _out({"ok": False, "error": f"Token saved but could not load: {e}"})
        sys.exit(1)
    ga4, gsc = _discover_all(creds)
    _out({"ok": True, "profile_name": args.name, "token_path": token_path,
          "ga4_properties": ga4, "gsc_sites": gsc})


def cmd_save(args):
    rel_token = f"credentials/{args.name}.json"
    cfg_module.upsert_profile(
        name=args.name,
        ga4_property_id=args.ga4_id or "",
        gsc_site_url=args.gsc_url or "",
        url_groups_sheet_id=args.sheet_id or "",
        credentials_path=rel_token,
    )
    accounts = cfg_module._load_accounts()
    if accounts.get("default") is None:
        cfg_module.set_default(args.name)
    accounts = cfg_module._load_accounts()
    _out({"ok": True, "profile": args.name, "ga4_property_id": args.ga4_id,
          "gsc_site_url": args.gsc_url, "sheet_id": args.sheet_id or "",
          "is_default": accounts.get("default") == args.name})


def _discover_all(creds) -> tuple[list, list]:
    ga4 = []
    try:
        ga4 = auth_module.discover_ga4_properties(creds)
    except Exception:
        pass
    gsc = []
    try:
        gsc = auth_module.discover_gsc_sites(creds)
    except Exception:
        pass
    return ga4, gsc


def _out(data: dict):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="phase", required=True)

    p2 = sub.add_parser("auth-url", help="Generate OAuth URL, no browser (step 1)")
    p2.add_argument("--name", required=True)

    p3 = sub.add_parser("auth-complete", help="Complete OAuth from redirect URL (step 2)")
    p3.add_argument("--name", required=True)
    p3.add_argument("--redirect-url", required=True,
                    help="Full redirect URL from browser address bar")

    p4 = sub.add_parser("save", help="Save selected property/site as profile")
    p4.add_argument("--name", required=True)
    p4.add_argument("--ga4-id", required=True)
    p4.add_argument("--gsc-url", required=True)
    p4.add_argument("--sheet-id", default="")

    handlers = {
        "auth-url": cmd_auth_url,
        "auth-complete": cmd_auth_complete,
        "save": cmd_save,
    }
    args = parser.parse_args()
    handlers[args.phase](args)


if __name__ == "__main__":
    main()
