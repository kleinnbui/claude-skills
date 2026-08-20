"""Profile-aware config loader.

accounts.json structure:
{
  "oauth_client": "oauth_client.json",      // set once by admin (OAuth2 Desktop app)
  "shared_credentials": "credentials/shared.json",  // optional legacy SA
  "default": "my-site",
  "profiles": {
    "my-site": {
      "ga4_property_id": "123456789",
      "gsc_site_url": "https://example.com/",
      "url_groups_sheet_id": "...",          // optional
      "url_groups_worksheet": "Sheet1",
      // per-profile credential (set automatically by `auth` command):
      "credentials_path": "credentials/my-site.json",
      // optional tuning:
      "decay_threshold_percent": 30,
      "ctr_opportunity_min_impressions": 100,
      "cannibalization_min_clicks": 5,
      "potential_min_impressions": 50,
      "potential_max_position": 20
    }
  }
}

Credential resolution order (per profile):
  1. profile["credentials_path"]    — OAuth token saved by `auth` command
  2. accounts["shared_credentials"] — legacy shared service account
"""
import json
import os
import shutil
from datetime import date
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
ACCOUNTS_FILE = SKILL_DIR / "accounts.json"

_DEFAULTS = {
    "url_groups_worksheet": "Sheet1",
    "decay_threshold_percent": 30,
    "ctr_opportunity_min_impressions": 100,
    "cannibalization_min_clicks": 5,
    "cannibalization_min_impressions": 50,
    "potential_min_impressions": 50,
    "potential_max_position": 20,
    "full_report_min_sessions": 10,
    "anomaly_threshold_percent": 30,
    "query_trend_threshold_percent": 20,
    "brand_keywords": [],
    # kpi: {"source": "gsc", "metric": "clicks", "monthly_target": 0}
}


def _load_accounts() -> dict:
    if not ACCOUNTS_FILE.exists():
        return {"default": None, "profiles": {}}
    with open(ACCOUNTS_FILE) as f:
        return json.load(f)


def _save_accounts(data: dict) -> None:
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _resolve_path(raw: str) -> str:
    p = Path(raw).expanduser()
    return str(p) if p.is_absolute() else str(SKILL_DIR / p)


# ── Config loader ────────────────────────────────────────────────────────────

def load_config(profile: str | None = None) -> dict:
    accounts = _load_accounts()
    profiles = accounts.get("profiles", {})

    name = profile or os.environ.get("SEO_PROFILE") or accounts.get("default")
    if not name:
        raise ValueError(
            "No profile specified. Use --profile <name> or:\n"
            "  python manage_accounts.py default --name <name>"
        )
    if name not in profiles:
        available = ", ".join(profiles) or "(none)"
        raise ValueError(
            f"Profile '{name}' not found. Available: {available}\n"
            f"Run: python manage_accounts.py auth --name {name}"
        )

    cfg = {**_DEFAULTS, **profiles[name]}

    raw_cred = cfg.get("credentials_path") or accounts.get("shared_credentials")
    if not raw_cred:
        raise ValueError(
            f"No credentials for profile '{name}'.\n"
            f"Run: python manage_accounts.py auth --name {name}"
        )
    cfg["credentials_path"] = _resolve_path(raw_cred)
    cfg["_profile_name"] = name
    return cfg


def credentials_path(profile: str | None = None) -> str:
    return load_config(profile)["credentials_path"]


# ── OAuth client management ──────────────────────────────────────────────────

def set_oauth_client(src_path: str | None = None,
                     client_id: str | None = None,
                     client_secret: str | None = None) -> None:
    """Store OAuth2 client config. Accepts a downloaded JSON file or raw id/secret."""
    dest = SKILL_DIR / "oauth_client.json"

    if src_path:
        src = Path(src_path).expanduser()
        if not src.exists():
            raise FileNotFoundError(f"File not found: {src}")
        shutil.copy2(src, dest)
    elif client_id and client_secret:
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": ["http://localhost"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        with open(dest, "w") as f:
            json.dump(client_config, f, indent=2)
    else:
        raise ValueError("Provide either a file path or --client-id + --client-secret")

    accounts = _load_accounts()
    accounts["oauth_client"] = "oauth_client.json"
    _save_accounts(accounts)
    print(f"OAuth client saved → {dest}")


def get_oauth_client_info() -> dict:
    accounts = _load_accounts()
    raw = accounts.get("oauth_client")
    if not raw and (SKILL_DIR / "oauth_client.json").exists():
        raw = "oauth_client.json"
    if not raw:
        return {"configured": False}
    path = _resolve_path(raw)
    if not Path(path).exists():
        return {"configured": True, "exists": False, "path": path}
    with open(path) as f:
        data = json.load(f)
    cfg = data.get("installed") or data.get("web") or {}
    return {
        "configured": True,
        "exists": True,
        "path": path,
        "client_id": cfg.get("client_id", "?"),
    }


# ── Profile management ───────────────────────────────────────────────────────

def list_profiles() -> dict:
    accounts = _load_accounts()
    return {
        "default": accounts.get("default"),
        "oauth_client": get_oauth_client_info(),
        "profiles": {
            name: {k: v for k, v in p.items() if k != "credentials_path"}
            for name, p in accounts.get("profiles", {}).items()
        },
    }


def upsert_profile(name: str, **fields) -> None:
    """Create or update a profile with the given fields."""
    accounts = _load_accounts()
    profiles = accounts.setdefault("profiles", {})
    existing = profiles.get(name, {})
    existing.update({k: v for k, v in fields.items() if v is not None})
    profiles[name] = existing
    if accounts.get("default") is None:
        accounts["default"] = name
    _save_accounts(accounts)


def remove_profile(name: str) -> None:
    accounts = _load_accounts()
    if name not in accounts.get("profiles", {}):
        raise ValueError(f"Profile '{name}' not found.")
    # Also remove token file if it's a per-profile credential
    cred_rel = accounts["profiles"][name].get("credentials_path", "")
    if cred_rel and not Path(cred_rel).is_absolute():
        cred_abs = SKILL_DIR / cred_rel
        if cred_abs.exists():
            cred_abs.unlink()
    del accounts["profiles"][name]
    if accounts.get("default") == name:
        accounts["default"] = next(iter(accounts["profiles"]), None)
    _save_accounts(accounts)
    print(f"Profile '{name}' removed.")


def set_default(name: str) -> None:
    accounts = _load_accounts()
    if name not in accounts.get("profiles", {}):
        raise ValueError(f"Profile '{name}' not found.")
    accounts["default"] = name
    _save_accounts(accounts)
    print(f"Default → '{name}'")


# ── Watchlist management ─────────────────────────────────────────────────────

def add_to_watchlist(profile_name: str, url: str, note: str = "") -> None:
    accounts = _load_accounts()
    if profile_name not in accounts.get("profiles", {}):
        raise ValueError(f"Profile '{profile_name}' not found.")
    profile = accounts["profiles"][profile_name]
    watchlist = profile.get("watchlist", [])
    if any(w["url"] == url for w in watchlist):
        raise ValueError(f"URL already in watchlist for '{profile_name}'.")
    watchlist.append({"url": url, "note": note, "added": date.today().isoformat()})
    profile["watchlist"] = watchlist
    _save_accounts(accounts)


def remove_from_watchlist(profile_name: str, url: str) -> None:
    accounts = _load_accounts()
    if profile_name not in accounts.get("profiles", {}):
        raise ValueError(f"Profile '{profile_name}' not found.")
    profile = accounts["profiles"][profile_name]
    watchlist = profile.get("watchlist", [])
    new_wl = [w for w in watchlist if w["url"] != url]
    if len(new_wl) == len(watchlist):
        raise ValueError(f"URL not found in watchlist for '{profile_name}'.")
    profile["watchlist"] = new_wl
    _save_accounts(accounts)


def get_watchlist(profile_name: str | None = None) -> list[dict]:
    accounts = _load_accounts()
    name = profile_name or accounts.get("default")
    if not name:
        return []
    return accounts.get("profiles", {}).get(name, {}).get("watchlist", [])
