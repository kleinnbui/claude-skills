#!/usr/bin/env python3
"""Account manager for /cro-setup skill.

── Admin setup (one-time) ──────────────────────────────────────────────────
  python manage_accounts.py set-oauth-client ~/Downloads/client_secret.json

── Daily use ───────────────────────────────────────────────────────────────
  python manage_accounts.py list
  python manage_accounts.py show --name <profile>
  python manage_accounts.py default --name <profile>
  python manage_accounts.py remove --name <profile>
"""
import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
import config as cfg_module


def cmd_set_oauth_client(args):
    try:
        if args.path:
            cfg_module.set_oauth_client(src_path=args.path)
        else:
            if not args.client_id or not args.client_secret:
                print("ERROR: provide --path or both --client-id and --client-secret",
                      file=sys.stderr)
                sys.exit(1)
            cfg_module.set_oauth_client(
                client_id=args.client_id, client_secret=args.client_secret
            )

        info = cfg_module.get_oauth_client_info()
        print(f"\nOAuth client configured.")
        print(f"  Client ID: {info['client_id']}")
        print(f"\nReady to authenticate. Run /cro-setup in Claude Code.")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list(_args):
    data = cfg_module.list_profiles()
    default = data["default"]
    profiles = data["profiles"]

    oauth = data["oauth_client"]
    if oauth.get("exists"):
        print(f"OAuth client: OK  (client_id: {oauth['client_id'][:30]}...)\n")
    else:
        print("OAuth client: NOT CONFIGURED — run: python manage_accounts.py set-oauth-client\n")

    if not profiles:
        print("No profiles yet. Run /cro-setup in Claude Code to add one.")
        return

    print(f"{'NAME':<22} {'DEFAULT':<9} {'GTM':<16} {'GA4 PROPERTY'}")
    print("─" * 78)
    for name, p in profiles.items():
        marker = "*" if name == default else ""
        print(
            f"{name:<22} {marker:<9}"
            f"{p.get('gtm_public_id') or p.get('gtm_container_id', '?'):<16} "
            f"{p.get('ga4_property_id', '?')} ({p.get('ga4_measurement_id', '?')})"
        )


def cmd_remove(args):
    cfg_module.remove_profile(args.name)


def cmd_default(args):
    cfg_module.set_default(args.name)


def cmd_show(args):
    accounts = cfg_module._load_accounts()
    name = args.name or accounts.get("default")
    if not name:
        print("No default profile. Use --name.")
        return
    p = accounts["profiles"].get(name)
    if not p:
        print(f"Profile '{name}' not found.")
        return
    print(f"Profile: {name}")
    print(json.dumps({k: v for k, v in p.items() if "credentials" not in k},
                     indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="/cro-setup — Account Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_soc = sub.add_parser("set-oauth-client", help="[Admin] Set OAuth2 client credentials")
    p_soc.add_argument("path", nargs="?", help="Path to client_secret.json from GCP")
    p_soc.add_argument("--client-id")
    p_soc.add_argument("--client-secret")

    sub.add_parser("list", help="List all profiles")

    p_rm = sub.add_parser("remove", help="Remove a profile")
    p_rm.add_argument("--name", required=True)

    p_def = sub.add_parser("default", help="Set default profile")
    p_def.add_argument("--name", required=True)

    p_show = sub.add_parser("show", help="Show profile details")
    p_show.add_argument("--name")

    args = parser.parse_args()
    {
        "set-oauth-client": cmd_set_oauth_client,
        "list": cmd_list,
        "remove": cmd_remove,
        "default": cmd_default,
        "show": cmd_show,
    }[args.command](args)


if __name__ == "__main__":
    main()
