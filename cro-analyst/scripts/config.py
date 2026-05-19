"""Profile-aware config loader for cro-analyst.

Co-existence with /cro-setup:
  - Auto-detect ~/.claude/skills/cro-setup/accounts.json
  - Reuse cro-setup profile (cro-setup OAuth scopes superset our analytics.readonly)
  - Standalone fallback: own accounts.json + credentials/

When listing profiles, cro-setup profiles win on name conflict.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

LOCAL_DIR = Path(__file__).parent.parent
LOCAL_ACCOUNTS = LOCAL_DIR / "accounts.json"
LOCAL_OAUTH_CLIENT = LOCAL_DIR / "oauth_client.json"

CRO_SETUP_DIR = Path.home() / ".claude" / "skills" / "cro-setup"
CRO_SETUP_ACCOUNTS = CRO_SETUP_DIR / "accounts.json"


# ── Low-level file ops ──────────────────────────────────────────────────────

def _load(path: Path) -> dict:
    if not path.exists():
        return {"default": None, "profiles": {}}
    with open(path) as f:
        return json.load(f)


def _save(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_accounts() -> dict:
    """For local standalone mode admin commands (manage_accounts.py)."""
    return _load(LOCAL_ACCOUNTS)


def _save_accounts(data: dict) -> None:
    _save(LOCAL_ACCOUNTS, data)


def _resolve_path(raw: str, base: Path) -> str:
    p = Path(raw).expanduser()
    return str(p) if p.is_absolute() else str(base / p)


def _local_oauth_client_path() -> str:
    """Return absolute path to local oauth_client.json, or '' if not set."""
    accounts = _load(LOCAL_ACCOUNTS)
    raw = accounts.get("oauth_client")
    if not raw:
        return ""
    return _resolve_path(raw, LOCAL_DIR)


# ── Merged profile listing ──────────────────────────────────────────────────

def list_all_profiles() -> dict:
    """Return merged profiles dict {name: {...profile, _source}}.
    cro-setup profiles win on name conflict.
    """
    out: dict[str, dict] = {}

    # cro-setup first (priority)
    if CRO_SETUP_ACCOUNTS.exists():
        cs = _load(CRO_SETUP_ACCOUNTS)
        for name, p in cs.get("profiles", {}).items():
            entry = dict(p)
            entry["_source"] = "cro-setup"
            out[name] = entry

    # local (only if not already from cro-setup)
    if LOCAL_ACCOUNTS.exists():
        loc = _load(LOCAL_ACCOUNTS)
        for name, p in loc.get("profiles", {}).items():
            if name not in out:
                entry = dict(p)
                entry["_source"] = "standalone"
                out[name] = entry

    return out


def get_default_profile_name() -> str | None:
    """Return default profile name. Prefer cro-setup default, else local default."""
    if CRO_SETUP_ACCOUNTS.exists():
        cs = _load(CRO_SETUP_ACCOUNTS)
        if cs.get("default"):
            return cs["default"]
    loc = _load(LOCAL_ACCOUNTS)
    return loc.get("default")


def load_profile(profile: str | None = None) -> dict:
    """Load profile config with credentials_path resolved to absolute.

    Adds:
      _profile_name : str — the profile name
      _source       : "cro-setup" | "standalone"
    """
    name = profile or os.environ.get("CRO_PROFILE") or get_default_profile_name()
    if not name:
        raise ValueError(
            "No profile specified. Use --profile <name> or set default via:\n"
            "  python manage_accounts.py default --name <name>"
        )

    profiles = list_all_profiles()
    if name not in profiles:
        available = ", ".join(profiles) or "(none)"
        raise ValueError(
            f"Profile '{name}' not found. Available: {available}\n"
            f"Add a new one via /cro-analyst or /cro-setup"
        )

    cfg = dict(profiles[name])
    src = cfg["_source"]
    base = CRO_SETUP_DIR if src == "cro-setup" else LOCAL_DIR

    raw_cred = cfg.get("credentials_path")
    if not raw_cred:
        raise ValueError(
            f"No credentials for profile '{name}' (source: {src}).\n"
            f"Re-run /cro-analyst (or /cro-setup) to authenticate."
        )
    cfg["credentials_path"] = _resolve_path(raw_cred, base)
    cfg["_profile_name"] = name
    return cfg


def credentials_path(profile: str | None = None) -> str:
    return load_profile(profile)["credentials_path"]


# ── OAuth client management (standalone) ────────────────────────────────────

def set_oauth_client(src_path: str | None = None,
                     client_id: str | None = None,
                     client_secret: str | None = None) -> None:
    """Store OAuth2 client config. Accepts a downloaded JSON file or raw id/secret."""
    dest = LOCAL_OAUTH_CLIENT

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
        dest.chmod(0o600)
    else:
        raise ValueError("Provide either a file path or --client-id + --client-secret")

    accounts = _load_accounts()
    accounts["oauth_client"] = "oauth_client.json"
    _save_accounts(accounts)
    print(f"OAuth client saved → {dest}")


def get_oauth_client_info() -> dict:
    """Inspect local OAuth client; if not set, fall back to cro-setup's."""
    accounts = _load_accounts()
    raw = accounts.get("oauth_client")
    source = "standalone"
    if not raw:
        cs_client = CRO_SETUP_DIR / "oauth_client.json"
        if cs_client.exists():
            path = str(cs_client)
            source = "cro-setup"
        else:
            return {"configured": False}
    else:
        path = _resolve_path(raw, LOCAL_DIR)

    if not Path(path).exists():
        return {"configured": True, "exists": False, "path": path, "source": source}

    with open(path) as f:
        data = json.load(f)
    cfg = data.get("installed") or data.get("web") or {}
    return {
        "configured": True,
        "exists": True,
        "path": path,
        "client_id": cfg.get("client_id", "?"),
        "source": source,
    }


# ── Profile management (standalone) ─────────────────────────────────────────

def list_profiles_summary() -> dict:
    """Used by manage_accounts.py list. Includes oauth_client info."""
    merged = list_all_profiles()
    return {
        "default": get_default_profile_name(),
        "oauth_client": get_oauth_client_info(),
        "profiles": {
            name: {k: v for k, v in p.items() if k != "credentials_path"}
            for name, p in merged.items()
        },
    }


def upsert_profile(name: str, **fields) -> None:
    """Standalone-only: write to local accounts.json."""
    accounts = _load_accounts()
    profiles = accounts.setdefault("profiles", {})
    existing = profiles.get(name, {})
    existing.update({k: v for k, v in fields.items() if v is not None})
    profiles[name] = existing
    if accounts.get("default") is None:
        accounts["default"] = name
    _save_accounts(accounts)


def remove_profile(name: str) -> None:
    """Standalone-only. Cannot remove cro-setup profiles from here."""
    accounts = _load_accounts()
    if name not in accounts.get("profiles", {}):
        raise ValueError(
            f"Profile '{name}' not found in standalone accounts.\n"
            f"Note: cro-setup profiles must be removed via /cro-setup."
        )
    cred_rel = accounts["profiles"][name].get("credentials_path", "")
    if cred_rel and not Path(cred_rel).is_absolute():
        cred_abs = LOCAL_DIR / cred_rel
        if cred_abs.exists():
            cred_abs.unlink()
    del accounts["profiles"][name]
    if accounts.get("default") == name:
        accounts["default"] = next(iter(accounts["profiles"]), None)
    _save_accounts(accounts)
    print(f"Profile '{name}' removed.")


def set_default(name: str) -> None:
    """Standalone-only default. cro-setup has its own default."""
    accounts = _load_accounts()
    merged = list_all_profiles()
    if name not in merged:
        raise ValueError(f"Profile '{name}' not found.")
    accounts["default"] = name
    _save_accounts(accounts)
    print(f"Default → '{name}'")
