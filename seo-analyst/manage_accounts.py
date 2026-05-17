#!/usr/bin/env python3
"""Account manager for SEO Analyst skill.

── Admin setup (one-time) ──────────────────────────────────────────────────
  python manage_accounts.py set-oauth-client ~/Downloads/client_secret.json
  # Or with raw values:
  python manage_accounts.py set-oauth-client --client-id xxx --client-secret yyy

── Per-user setup ───────────────────────────────────────────────────────────
  python manage_accounts.py auth
  # → browser opens → log in with Google → pick GA4 property + GSC site → done

── Daily use ───────────────────────────────────────────────────────────────
  python manage_accounts.py list
  python scripts/main.py 30d                   # uses default profile
  python scripts/main.py 30d --profile my-site
"""
import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
import config as cfg_module


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_set_oauth_client(args):
    try:
        if args.path:
            cfg_module.set_oauth_client(src_path=args.path)
        else:
            if not args.client_id or not args.client_secret:
                print("ERROR: provide --path or both --client-id and --client-secret", file=sys.stderr)
                sys.exit(1)
            cfg_module.set_oauth_client(client_id=args.client_id, client_secret=args.client_secret)

        info = cfg_module.get_oauth_client_info()
        print(f"\nOAuth client configured.")
        print(f"  Client ID: {info['client_id']}")
        print(f"\nUsers can now authenticate by running:")
        print(f"  python manage_accounts.py auth")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_auth(args):
    """Interactive OAuth flow: authenticate → discover properties → save profile."""
    import auth as auth_module

    # Determine profile name
    profile_name = args.name
    if not profile_name:
        profile_name = input("Profile name (e.g. blog-abc): ").strip()
        if not profile_name:
            print("Cancelled.")
            return

    # Run OAuth flow
    try:
        creds, token_path = auth_module.run_flow(profile_name)
    except Exception as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Discover GA4 properties
    print("\nFetching your GA4 properties...")
    ga4_props = auth_module.discover_ga4_properties(creds)

    ga4_id = None
    if not ga4_props:
        print("No GA4 properties found for this account.")
        ga4_id = input("Enter GA4 Property ID manually (or press Enter to skip): ").strip() or None
    elif len(ga4_props) == 1:
        p = ga4_props[0]
        print(f"  Found: {p['display_name']} ({p['id']})")
        ga4_id = p["id"]
    else:
        print()
        for i, p in enumerate(ga4_props, 1):
            site = f" — {p['website_url']}" if p["website_url"] else ""
            print(f"  [{i}] {p['display_name']} ({p['id']}){site}")
        while True:
            raw = input(f"\nSelect GA4 property [1-{len(ga4_props)}]: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(ga4_props):
                ga4_id = ga4_props[int(raw) - 1]["id"]
                break
            print("  Invalid selection, try again.")

    # Discover GSC sites
    print("\nFetching your GSC sites...")
    gsc_sites = auth_module.discover_gsc_sites(creds)

    gsc_url = None
    if not gsc_sites:
        print("No GSC sites found for this account.")
        gsc_url = input("Enter GSC site URL manually (or press Enter to skip): ").strip() or None
    elif len(gsc_sites) == 1:
        gsc_url = gsc_sites[0]["url"]
        print(f"  Found: {gsc_url}")
    else:
        print()
        for i, s in enumerate(gsc_sites, 1):
            perm = s["permission"].replace("site", "").replace("User", "")
            print(f"  [{i}] {s['url']}  ({perm})")
        while True:
            raw = input(f"\nSelect GSC site [1-{len(gsc_sites)}]: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(gsc_sites):
                gsc_url = gsc_sites[int(raw) - 1]["url"]
                break
            print("  Invalid selection, try again.")

    # Optional: Google Sheet ID
    sheet_id = input("\nGoogle Sheet ID for URL groups (press Enter to skip): ").strip() or ""

    # Save profile
    rel_token = f"credentials/{profile_name}.json"
    cfg_module.upsert_profile(
        name=profile_name,
        ga4_property_id=ga4_id or "",
        gsc_site_url=gsc_url or "",
        url_groups_sheet_id=sheet_id,
        credentials_path=rel_token,
    )

    # Set as default if first profile
    accounts = cfg_module._load_accounts()
    if len(accounts.get("profiles", {})) == 1:
        cfg_module.set_default(profile_name)

    print(f"\nProfile '{profile_name}' saved.")
    if ga4_id:
        print(f"  GA4 : {ga4_id}")
    if gsc_url:
        print(f"  GSC : {gsc_url}")
    if sheet_id:
        print(f"  Sheet: {sheet_id}")

    # Quick test
    answer = input("\nRun connection test? [Y/n]: ").strip().lower()
    if answer != "n":
        cmd_test(argparse.Namespace(name=profile_name))


def cmd_list(_args):
    data = cfg_module.list_profiles()
    default = data["default"]
    profiles = data["profiles"]

    oauth = data["oauth_client"]
    if oauth.get("exists"):
        print(f"OAuth client: ✓  (client_id: {oauth['client_id'][:30]}...)\n")
    else:
        print("OAuth client: ⚠ not configured — run: python manage_accounts.py set-oauth-client\n")

    if not profiles:
        print("No profiles yet. Run: python manage_accounts.py auth")
        return

    print(f"{'NAME':<22} {'DEFAULT':<9} {'GA4 PROPERTY':<16} {'GSC SITE'}")
    print("─" * 78)
    for name, p in profiles.items():
        marker = "✓" if name == default else ""
        print(
            f"{name:<22} {marker:<9}"
            f"{p.get('ga4_property_id', '?'):<16} "
            f"{p.get('gsc_site_url', '?')}"
        )


def cmd_remove(args):
    cfg_module.remove_profile(args.name)
    print(f"Profile '{args.name}' removed.")


def cmd_default(args):
    cfg_module.set_default(args.name)


def cmd_update(args):
    accounts = cfg_module._load_accounts()
    if args.name not in accounts.get("profiles", {}):
        print(f"ERROR: Profile '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)

    profile = accounts["profiles"][args.name]
    updated = []

    for field, val in [
        ("ga4_property_id", args.ga4_id),
        ("gsc_site_url", args.gsc_url),
        ("url_groups_sheet_id", args.sheet_id),
        ("url_groups_worksheet", args.worksheet),
    ]:
        if val is not None:
            profile[field] = val
            updated.append(field)

    # KPI — nested dict
    if args.kpi_target is not None or args.kpi_source:
        kpi = profile.get("kpi") or {}
        if args.kpi_target is not None:
            kpi["monthly_target"] = args.kpi_target
        if args.kpi_source:
            kpi["source"] = args.kpi_source
            kpi["metric"] = "clicks" if args.kpi_source == "gsc" else "sessions"
        elif "source" not in kpi:
            kpi["source"] = "gsc"
            kpi["metric"] = "clicks"
        profile["kpi"] = kpi
        updated.append("kpi")

    # Brand keywords — comma-separated string → list
    if args.brand_keywords is not None:
        keywords = [k.strip() for k in args.brand_keywords.split(",") if k.strip()]
        profile["brand_keywords"] = keywords
        updated.append("brand_keywords")

    # Thresholds
    if args.decay_threshold is not None:
        profile["decay_threshold_percent"] = args.decay_threshold
        updated.append("decay_threshold_percent")
    if args.anomaly_threshold is not None:
        profile["anomaly_threshold_percent"] = args.anomaly_threshold
        updated.append("anomaly_threshold_percent")

    if not updated:
        print("Nothing to update. Pass at least one option.", file=sys.stderr)
        sys.exit(1)

    cfg_module._save_accounts(accounts)
    print(f"Profile '{args.name}' updated: {', '.join(updated)}")
    for field in updated:
        print(f"  {field}: {profile.get(field)}")


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
    print(json.dumps({k: v for k, v in p.items() if "credentials" not in k}, indent=2))


def cmd_watchlist_add(args):
    try:
        cfg_module.add_to_watchlist(args.name, args.url, args.note or "")
        print(f"Added to watchlist [{args.name}]: {args.url}")
        if args.note:
            print(f"  Note: {args.note}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_watchlist_remove(args):
    try:
        cfg_module.remove_from_watchlist(args.name, args.url)
        print(f"Removed from watchlist [{args.name}]: {args.url}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_watchlist_show(args):
    accounts = cfg_module._load_accounts()
    targets = ([args.name] if args.name
               else list(accounts.get("profiles", {}).keys()))
    for prof in targets:
        wl = cfg_module.get_watchlist(prof)
        print(f"\nWatchlist [{prof}] — {len(wl)} URL(s)")
        if wl:
            for i, w in enumerate(wl, 1):
                note = f"  {w['note']}" if w.get("note") else ""
                print(f"  {i}. {w['url']}{note}  (added: {w.get('added', '?')})")
        else:
            print("  (empty)")


def cmd_test(args):
    profile = getattr(args, "name", None) or None
    try:
        c = cfg_module.load_config(profile)
    except Exception as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    from pathlib import Path as P
    cred = P(c["credentials_path"])
    cred_type = "?"
    if cred.exists():
        import json
        with open(cred) as f:
            cred_type = json.load(f).get("type", "?")

    print(f"Profile   : {c['_profile_name']}")
    print(f"GA4 ID    : {c['ga4_property_id']}")
    print(f"GSC URL   : {c['gsc_site_url']}")
    print(f"Auth type : {cred_type}")

    if not cred.exists():
        print(f"\nERROR: credential file missing. Run: python manage_accounts.py auth --name {c['_profile_name']}")
        sys.exit(1)

    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    from datetime import date, timedelta
    today = date.today()
    d3 = (today - timedelta(days=3)).isoformat()
    end = today.isoformat()

    print("\nTesting GA4...")
    try:
        import fetch_ga4
        rows = fetch_ga4.by_page(d3, end, profile=profile)
        print(f"  ✓ GA4 OK — {len(rows)} rows")
    except Exception as e:
        print(f"  ✗ GA4 FAILED: {e}")

    print("Testing GSC...")
    try:
        import fetch_gsc
        rows = fetch_gsc.by_date(d3, end, profile=profile)
        print(f"  ✓ GSC OK — {len(rows)} rows")
    except Exception as e:
        print(f"  ✗ GSC FAILED: {e}")

    if c.get("url_groups_sheet_id"):
        print("Testing Sheets...")
        try:
            import fetch_sheets
            rows = fetch_sheets.load_url_groups(profile=profile)
            print(f"  ✓ Sheets OK — {len(rows)} rows")
        except Exception as e:
            print(f"  ✗ Sheets FAILED: {e}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SEO Analyst — Account Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # set-oauth-client
    p_soc = sub.add_parser("set-oauth-client", help="[Admin] Set OAuth2 client credentials")
    p_soc.add_argument("path", nargs="?", help="Path to client_secret.json downloaded from GCP")
    p_soc.add_argument("--client-id", help="OAuth client ID (alternative to file)")
    p_soc.add_argument("--client-secret", help="OAuth client secret (alternative to file)")

    # auth  ← main user command
    p_auth = sub.add_parser("auth", help="Authenticate with Google and set up a profile")
    p_auth.add_argument("--name", help="Profile name (prompted if omitted)")

    # list
    sub.add_parser("list", help="List all profiles")

    # remove
    p_rm = sub.add_parser("remove", help="Remove a profile")
    p_rm.add_argument("--name", required=True)

    # default
    p_def = sub.add_parser("default", help="Set default profile")
    p_def.add_argument("--name", required=True)

    # update
    p_upd = sub.add_parser("update", help="Update profile fields")
    p_upd.add_argument("--name", required=True)
    p_upd.add_argument("--ga4-id", dest="ga4_id", default=None)
    p_upd.add_argument("--gsc-url", dest="gsc_url", default=None)
    p_upd.add_argument("--sheet-id", dest="sheet_id", default=None)
    p_upd.add_argument("--worksheet", default=None)
    p_upd.add_argument("--kpi-target", dest="kpi_target", type=int, default=None,
                       help="Monthly KPI target (number)")
    p_upd.add_argument("--kpi-source", dest="kpi_source", choices=["gsc", "ga4"], default=None,
                       help="gsc = clicks, ga4 = sessions")
    p_upd.add_argument("--brand-keywords", dest="brand_keywords", default=None,
                       help="Comma-separated brand keywords (e.g. 'mybrand,my brand')")
    p_upd.add_argument("--decay-threshold", dest="decay_threshold", type=int, default=None,
                       help="Content decay threshold %% (default 30)")
    p_upd.add_argument("--anomaly-threshold", dest="anomaly_threshold", type=int, default=None,
                       help="Anomaly detection threshold %% (default 30)")
    # show
    p_show = sub.add_parser("show", help="Show profile details")
    p_show.add_argument("--name")

    # test
    p_test = sub.add_parser("test", help="Test API connections for a profile")
    p_test.add_argument("--name")

    # watchlist-add
    p_wla = sub.add_parser("watchlist-add", help="Add URL to watch list")
    p_wla.add_argument("--name", required=True, help="Profile name")
    p_wla.add_argument("--url", required=True, help="Page URL to watch")
    p_wla.add_argument("--note", default="", help="Optional note / reason")

    # watchlist-remove
    p_wlr = sub.add_parser("watchlist-remove", help="Remove URL from watch list")
    p_wlr.add_argument("--name", required=True)
    p_wlr.add_argument("--url", required=True)

    # watchlist-show
    p_wls = sub.add_parser("watchlist-show", help="Show watch list (all profiles or one)")
    p_wls.add_argument("--name", default=None, help="Profile name (omit = all)")

    args = parser.parse_args()
    {
        "set-oauth-client": cmd_set_oauth_client,
        "auth": cmd_auth,
        "list": cmd_list,
        "remove": cmd_remove,
        "default": cmd_default,
        "update": cmd_update,
        "show": cmd_show,
        "test": cmd_test,
        "watchlist-add": cmd_watchlist_add,
        "watchlist-remove": cmd_watchlist_remove,
        "watchlist-show": cmd_watchlist_show,
    }[args.command](args)


if __name__ == "__main__":
    main()
