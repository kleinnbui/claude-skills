"""Profile-aware config loader for cro-setup.

accounts.json structure:
{
  "oauth_client": "oauth_client.json",       # set once by admin (OAuth2 Desktop app)
  "default": "elitedental",
  "profiles": {
    "elitedental": {
      "client_name": "Elite Dental",
      "gtm_account_id": "1234567",
      "gtm_container_id": "GTM-XXXXXXX",
      "gtm_workspace_id": "3",                # default workspace
      "ga4_property_id": "315143198",
      "ga4_measurement_id": "G-XXXXXXXXXX",
      "credentials_path": "credentials/elitedental.json"
    }
  }
}
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
ACCOUNTS_FILE = SKILL_DIR / "accounts.json"


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


def load_config(profile: str | None = None) -> dict:
    accounts = _load_accounts()
    profiles = accounts.get("profiles", {})

    name = profile or os.environ.get("CRO_PROFILE") or accounts.get("default")
    if not name:
        raise ValueError(
            "No profile specified. Use --profile <name> or:\n"
            "  python manage_accounts.py default --name <name>"
        )
    if name not in profiles:
        available = ", ".join(profiles) or "(none)"
        raise ValueError(
            f"Profile '{name}' not found. Available: {available}\n"
            f"Add a new one via /cro-setup"
        )

    cfg = dict(profiles[name])

    raw_cred = cfg.get("credentials_path")
    if not raw_cred:
        raise ValueError(
            f"No credentials for profile '{name}'.\n"
            f"Re-run /cro-setup to authenticate."
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
        dest.chmod(0o600)
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
