"""Two-phase OAuth + GA4 discovery for cro-report standalone mode.

Subcommands:
  auth-url       Generate OAuth URL (step 1)
  auth-complete  Complete OAuth from pasted redirect URL (step 2) + discover GA4
  discover       Re-discover GA4 properties for an existing profile
  save           Save selected GA4 property to local profile
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import auth as auth_module
import config as cfg_module


def cmd_auth_url(args):
    try:
        result = auth_module.generate_auth_url(args.name)
        _out({"ok": True, "profile_name": args.name, **result})
    except Exception as e:
        _out({"ok": False, "error": str(e)})
        sys.exit(1)


def cmd_auth_complete(args):
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
    properties = auth_module.discover_ga4_properties(creds)
    _out({
        "ok": True,
        "profile_name": args.name,
        "token_path": token_path,
        "ga4_properties": properties,
    })


def cmd_discover(args):
    try:
        token_path = cfg_module.credentials_path(args.name)
        creds = auth_module.load_credentials(token_path)
    except Exception as e:
        _out({"ok": False, "error": str(e)})
        sys.exit(1)
    properties = auth_module.discover_ga4_properties(creds)
    _out({"ok": True, "profile_name": args.name, "ga4_properties": properties})


def cmd_save(args):
    rel_token = f"credentials/{args.name}.json"
    cfg_module.upsert_profile(
        name=args.name,
        client_name=args.client_name or args.name,
        ga4_property_id=args.ga4_property_id,
        ga4_measurement_id=args.ga4_measurement_id or "",
        credentials_path=rel_token,
    )
    accounts = cfg_module._load_accounts()
    if accounts.get("default") is None:
        cfg_module.set_default(args.name)
    accounts = cfg_module._load_accounts()
    _out({
        "ok": True,
        "profile": args.name,
        "is_default": accounts.get("default") == args.name,
    })


def _out(data: dict):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="phase", required=True)

    p1 = sub.add_parser("auth-url", help="Generate OAuth URL (step 1)")
    p1.add_argument("--name", required=True)

    p2 = sub.add_parser("auth-complete", help="Complete OAuth from redirect URL (step 2)")
    p2.add_argument("--name", required=True)
    p2.add_argument("--redirect-url", required=True)

    p3 = sub.add_parser("discover", help="Re-discover GA4 properties for existing profile")
    p3.add_argument("--name", required=True)

    p5 = sub.add_parser("save", help="Save selected GA4 property as profile")
    p5.add_argument("--name", required=True)
    p5.add_argument("--client-name")
    p5.add_argument("--ga4-property-id", required=True)
    p5.add_argument("--ga4-measurement-id", default="")

    handlers = {
        "auth-url": cmd_auth_url,
        "auth-complete": cmd_auth_complete,
        "discover": cmd_discover,
        "save": cmd_save,
    }
    args = parser.parse_args()
    handlers[args.phase](args)


if __name__ == "__main__":
    main()
