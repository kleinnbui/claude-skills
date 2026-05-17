"""OAuth2 flow + credential loader for cro-report.

Two-phase flow (sandbox-friendly):
  - generate_auth_url(): returns URL for user to open in browser
  - complete_auth(): exchanges code from pasted redirect URL for token

Scopes:
  - analytics.readonly  (read GA4 reports, list properties)

Standalone mode only. When co-existing with cro-setup, we reuse cro-setup's
credentials (which already include analytics.readonly + more).
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlparse, parse_qs

SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
]

_REDIRECT_PORT = 8766  # different port from cro-setup (8765) to avoid collision
_REDIRECT_URI = f"http://localhost:{_REDIRECT_PORT}"


# ── Credential loader ────────────────────────────────────────────────────────

def load_credentials(cred_path: str, scopes: list | None = None):
    scopes = scopes or SCOPES
    with open(cred_path) as f:
        data = json.load(f)

    cred_type = data.get("type", "")

    if cred_type == "service_account":
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_file(
            cred_path, scopes=scopes
        )

    if cred_type in ("authorized_user", "") and "refresh_token" in data:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        # When loading cro-setup credentials, the file has more scopes than we
        # need. Pass scopes=None so library uses whatever the token has.
        creds = Credentials.from_authorized_user_file(cred_path)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(cred_path, creds)
        return creds

    raise ValueError(f"Unknown credential type '{cred_type}' in {cred_path}")


def _save_token(path: str, creds) -> None:
    data = json.loads(creds.to_json())
    data["type"] = "authorized_user"
    with open(path, "w") as f:
        json.dump(data, f)


# ── OAuth client helpers ─────────────────────────────────────────────────────

def _get_oauth_client_config() -> dict:
    """Load OAuth client from local accounts.json, else fall back to cro-setup."""
    import config as cfg_module
    raw = cfg_module._local_oauth_client_path()
    if raw and Path(raw).exists():
        with open(raw) as f:
            return json.load(f)

    # Fallback: try cro-setup's oauth_client
    cro_setup_client = cfg_module.CRO_SETUP_DIR / "oauth_client.json"
    if cro_setup_client.exists():
        with open(cro_setup_client) as f:
            return json.load(f)

    raise ValueError(
        "OAuth client not configured.\n"
        "Run: python manage_accounts.py set-oauth-client ~/Downloads/client_secret.json\n"
        "Hoặc cài /cro-setup trước (cro-report sẽ reuse OAuth client của cro-setup)."
    )


# ── URL-based OAuth (sandbox-friendly) ──────────────────────────────────────

def generate_auth_url(profile_name: str) -> dict:
    from google_auth_oauthlib.flow import Flow

    client_config = _get_oauth_client_config()
    flow = Flow.from_client_config(client_config, SCOPES, redirect_uri=_REDIRECT_URI)

    state = secrets.token_urlsafe(16)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
    )

    pending_path = SKILL_DIR / "credentials" / f".{profile_name}_pending.json"
    pending_path.parent.mkdir(exist_ok=True)
    with open(pending_path, "w") as f:
        json.dump({
            "state": state,
            "redirect_uri": _REDIRECT_URI,
            "client_config": client_config,
            "code_verifier": getattr(flow, "code_verifier", None),
        }, f)

    return {
        "auth_url": auth_url,
        "redirect_uri": _REDIRECT_URI,
        "instructions": (
            f"1. Mở link trên trong browser\n"
            f"2. Đăng nhập Google account có quyền Read GA4 property\n"
            f"3. Browser sẽ báo lỗi 'This site can't be reached' — đó là bình thường\n"
            f"4. Copy toàn bộ URL từ address bar (bắt đầu bằng http://localhost:{_REDIRECT_PORT}/...)\n"
            f"5. Paste URL đó vào đây"
        ),
    }


def complete_auth(profile_name: str, redirect_url_or_code: str) -> str:
    from google_auth_oauthlib.flow import Flow

    pending_path = SKILL_DIR / "credentials" / f".{profile_name}_pending.json"
    if not pending_path.exists():
        raise ValueError(f"Không tìm thấy pending auth cho profile '{profile_name}'. Chạy auth-url trước.")

    with open(pending_path) as f:
        pending = json.load(f)

    raw = redirect_url_or_code.strip()
    if raw.startswith("http"):
        params = parse_qs(urlparse(raw).query)
        code = params.get("code", [None])[0]
        if not code:
            raise ValueError("Không tìm thấy 'code' trong URL. Hãy copy toàn bộ URL từ address bar.")
    else:
        code = raw

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    flow = Flow.from_client_config(
        pending["client_config"],
        SCOPES,
        redirect_uri=pending["redirect_uri"],
        state=pending["state"],
    )
    if pending.get("code_verifier"):
        flow.code_verifier = pending["code_verifier"]
    flow.fetch_token(code=code)
    creds = flow.credentials

    token_path = SKILL_DIR / "credentials" / f"{profile_name}.json"
    _save_token(str(token_path), creds)
    pending_path.unlink(missing_ok=True)

    return str(token_path)


# ── Discovery (GA4 only) ─────────────────────────────────────────────────────

def discover_ga4_properties(creds) -> list[dict]:
    from googleapiclient.discovery import build

    service = build("analyticsadmin", "v1beta", credentials=creds)
    properties = []
    try:
        accounts_resp = service.accounts().list().execute()
        for account in accounts_resp.get("accounts", []):
            try:
                props_resp = service.properties().list(
                    filter=f"ancestor:{account['name']}"
                ).execute()
                for prop in props_resp.get("properties", []):
                    prop_id = prop["name"].split("/")[-1]
                    measurement_id = _fetch_ga4_measurement_id(service, prop["name"])
                    properties.append({
                        "id": prop_id,
                        "display_name": prop.get("displayName", "?"),
                        "measurement_id": measurement_id,
                        "account": account.get("displayName", account["name"]),
                    })
            except Exception as e:
                print(f"Warning: skipped GA4 account '{account.get('displayName', account['name'])}' — {e}",
                      flush=True)
    except Exception as e:
        print(f"Warning: could not list GA4 properties: {e}", flush=True)
    return properties


def _fetch_ga4_measurement_id(service, property_name: str) -> str:
    try:
        streams = service.properties().dataStreams().list(parent=property_name).execute()
        for s in streams.get("dataStreams", []):
            if s.get("type") == "WEB_DATA_STREAM":
                return s.get("webStreamData", {}).get("measurementId", "")
    except Exception:
        pass
    return ""
