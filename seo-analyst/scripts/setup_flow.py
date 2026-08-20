"""Two-phase OAuth setup — designed to be orchestrated by Claude Code.

Subcommands:
  auth-url      Generate OAuth URL for user to open (sandbox-friendly, step 1)
  auth-complete Complete OAuth from redirect URL user pastes back (step 2)
  scan          Scan all saved credentials to find which has GA4/GSC access for a site
  auto-save     Auto-match GA4/GSC by domain and save profile (scans all creds automatically)
  save          Save profile with explicit IDs
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import auth as auth_module
import config as cfg_module


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


def _norm(url: str) -> str:
    u = (url or "").lower()
    for prefix in ("https://", "http://", "sc-domain:", "www."):
        u = u.replace(prefix, "")
    return u.rstrip("/")


def _match_ga4(props, site):
    return next(
        (p for p in props
         if site in _norm(p.get("website_url", "")) or _norm(p.get("website_url", "")) in site),
        None,
    )


def _match_gsc(sites, site):
    return next(
        (s for s in sites
         if site in _norm(s.get("url", "")) or _norm(s.get("url", "")) in site),
        None,
    )


def _scan_credentials(website: str) -> dict:
    """Try every credential file to find which has GA4/GSC access for the target site."""
    creds_dir = SCRIPTS_DIR.parent / "credentials"
    site = _norm(website)
    result = {"ga4": None, "gsc": None, "full_match": None, "scanned": [], "errors": []}

    for cred_file in sorted(creds_dir.glob("*.json")):
        if cred_file.name.startswith("."):
            continue
        cred_name = cred_file.stem
        try:
            creds = auth_module.load_credentials(str(cred_file))
            ga4_props, gsc_sites = _discover_all(creds)
            ga4 = _match_ga4(ga4_props, site)
            gsc = _match_gsc(gsc_sites, site)
            result["scanned"].append({"credential": cred_name, "ga4": bool(ga4), "gsc": bool(gsc)})
            if ga4 and not result["ga4"]:
                result["ga4"] = {"credential": cred_name, **ga4}
            if gsc and not result["gsc"]:
                result["gsc"] = {"credential": cred_name, **gsc}
            if ga4 and gsc and not result["full_match"]:
                result["full_match"] = cred_name
        except Exception as e:
            result["errors"].append({"credential": cred_name, "error": str(e)})

    return result


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
    ga4, gsc = _discover_all(creds)
    _out({"ok": True, "profile_name": args.name, "token_path": token_path,
          "ga4_properties": ga4, "gsc_sites": gsc})


def cmd_scan(args):
    """Scan all saved credentials to find which has GA4/GSC access for the target site."""
    scan = _scan_credentials(args.website)
    _out({
        "ok": bool(scan["full_match"] or scan["ga4"] or scan["gsc"]),
        "website": args.website,
        "full_match_credential": scan["full_match"],
        "ga4": scan["ga4"],
        "gsc": scan["gsc"],
        "scanned": scan["scanned"],
        "errors": scan["errors"],
        "needs_oauth": not bool(scan["full_match"]),
    })


def cmd_auto_save(args):
    """Auto-match GA4 + GSC by domain. Scans all saved credentials automatically."""
    site = _norm(args.website)

    scan = _scan_credentials(args.website)
    ga4_info = scan["ga4"]
    gsc_info = scan["gsc"]
    ga4_match = {k: v for k, v in ga4_info.items() if k != "credential"} if ga4_info else None
    gsc_match = {k: v for k, v in gsc_info.items() if k != "credential"} if gsc_info else None
    ga4_cred = ga4_info["credential"] if ga4_info else None
    gsc_cred = gsc_info["credential"] if gsc_info else None

    if not ga4_match and not gsc_match:
        _out({
            "ok": False,
            "needs_oauth": True,
            "error": f"Không tìm thấy match cho '{args.website}' trong {len(scan['scanned'])} credential(s). Cần đăng nhập Google account có quyền GA4/GSC.",
            "scanned": scan["scanned"],
        })
        sys.exit(1)

    # Use the credential that found GA4 (preferred); fallback to GSC's
    cred_to_use = ga4_cred or gsc_cred
    ga4_id = ga4_match["id"] if ga4_match else ""
    gsc_url = gsc_match["url"] if gsc_match else ""

    cfg_module.upsert_profile(
        name=args.name,
        ga4_property_id=ga4_id,
        gsc_site_url=gsc_url,
        url_groups_sheet_id="",
        credentials_path=f"credentials/{cred_to_use}.json",
    )
    accounts = cfg_module._load_accounts()
    if accounts.get("default") is None:
        cfg_module.set_default(args.name)

    _out({
        "ok": True,
        "profile_name": args.name,
        "ga4_property_id": ga4_id,
        "ga4_display_name": ga4_match.get("display_name") if ga4_match else None,
        "ga4_credential": ga4_cred,
        "gsc_site_url": gsc_url,
        "gsc_credential": gsc_cred,
        "credential_used": cred_to_use,
        "needs_oauth": False,
        "is_default": cfg_module._load_accounts().get("default") == args.name,
    })


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

    p_sc = sub.add_parser("scan", help="Scan all saved credentials for site GA4/GSC access")
    p_sc.add_argument("--website", required=True)

    p_as = sub.add_parser("auto-save", help="Auto-match GA4/GSC by domain (scans all credentials)")
    p_as.add_argument("--name", required=True, help="Profile name (usually domain)")
    p_as.add_argument("--website", required=True, help="Website domain to match")

    p4 = sub.add_parser("save", help="Save profile with explicit IDs")
    p4.add_argument("--name", required=True)
    p4.add_argument("--ga4-id", required=True)
    p4.add_argument("--gsc-url", required=True)
    p4.add_argument("--sheet-id", default="")

    handlers = {
        "auth-url": cmd_auth_url,
        "auth-complete": cmd_auth_complete,
        "scan": cmd_scan,
        "auto-save": cmd_auto_save,
        "save": cmd_save,
    }
    args = parser.parse_args()
    handlers[args.phase](args)


if __name__ == "__main__":
    main()
