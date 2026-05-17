"""OAuth2 flow + unified credential loader.

Supports both credential types transparently:
  - service_account: legacy SA JSON (requires manual property sharing)
  - authorized_user: OAuth token from run_flow() (no manual sharing needed)

OAuth flows:
  - run_flow(): legacy, opens browser directly (works in CLI)
  - generate_auth_url() + complete_auth(): URL-based, works in any env (sandbox/app)
"""
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlparse, parse_qs

SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_REDIRECT_PORT = 8765
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

        creds = Credentials.from_authorized_user_file(cred_path, scopes)
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
    from config import _load_accounts, _resolve_path
    accounts = _load_accounts()
    raw = accounts.get("oauth_client")
    if not raw:
        raise ValueError(
            "OAuth client not configured.\n"
            "Run: python manage_accounts.py set-oauth-client ~/Downloads/client_secret.json"
        )
    path = _resolve_path(raw)
    with open(path) as f:
        return json.load(f)


# ── URL-based OAuth (sandbox-friendly) ──────────────────────────────────────

def generate_auth_url(profile_name: str) -> dict:
    """Generate OAuth URL for user to open in browser. No blocking, no local server."""
    from google_auth_oauthlib.flow import Flow

    client_config = _get_oauth_client_config()
    flow = Flow.from_client_config(client_config, SCOPES, redirect_uri=_REDIRECT_URI)

    state = secrets.token_urlsafe(16)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
    )

    # Save state for complete_auth step
    pending_path = SKILL_DIR / "credentials" / f".{profile_name}_pending.json"
    pending_path.parent.mkdir(exist_ok=True)
    with open(pending_path, "w") as f:
        json.dump({
            "state": state,
            "redirect_uri": _REDIRECT_URI,
            "client_config": client_config,
        }, f)

    return {
        "auth_url": auth_url,
        "redirect_uri": _REDIRECT_URI,
        "instructions": (
            f"1. Mở link trên trong browser\n"
            f"2. Đăng nhập Google account có quyền GA4/GSC\n"
            f"3. Browser sẽ báo lỗi 'This site can't be reached' — đó là bình thường\n"
            f"4. Copy toàn bộ URL từ address bar (bắt đầu bằng http://localhost:{_REDIRECT_PORT}/...)\n"
            f"5. Paste URL đó vào đây"
        ),
    }


def complete_auth(profile_name: str, redirect_url_or_code: str) -> str:
    """Complete OAuth from redirect URL or authorization code. Returns token path."""
    from google_auth_oauthlib.flow import Flow

    pending_path = SKILL_DIR / "credentials" / f".{profile_name}_pending.json"
    if not pending_path.exists():
        raise ValueError(f"Không tìm thấy pending auth cho profile '{profile_name}'. Chạy auth-url trước.")

    with open(pending_path) as f:
        pending = json.load(f)

    # Extract code from redirect URL or use directly
    raw = redirect_url_or_code.strip()
    if raw.startswith("http"):
        params = parse_qs(urlparse(raw).query)
        code = params.get("code", [None])[0]
        if not code:
            raise ValueError("Không tìm thấy 'code' trong URL. Hãy copy toàn bộ URL từ address bar.")
    else:
        code = raw

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # localhost redirect is safe

    flow = Flow.from_client_config(
        pending["client_config"],
        SCOPES,
        redirect_uri=pending["redirect_uri"],
        state=pending["state"],
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    token_path = SKILL_DIR / "credentials" / f"{profile_name}.json"
    _save_token(str(token_path), creds)
    pending_path.unlink(missing_ok=True)

    return str(token_path)


# ── Legacy flow (CLI only) ───────────────────────────────────────────────────

def run_flow(profile_name: str):
    """Open browser directly. Only works in interactive CLI environments."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_config = _get_oauth_client_config()
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    token_path = SKILL_DIR / "credentials" / f"{profile_name}.json"
    token_path.parent.mkdir(exist_ok=True)
    _save_token(str(token_path), creds)
    return creds, str(token_path)


# ── Property discovery ───────────────────────────────────────────────────────

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
                    properties.append({
                        "id": prop["name"].split("/")[-1],
                        "display_name": prop.get("displayName", "?"),
                        "website_url": prop.get("websiteUrl", ""),
                        "account": account.get("displayName", account["name"]),
                    })
            except Exception:
                pass
    except Exception as e:
        print(f"Warning: could not list GA4 properties: {e}", flush=True)
    return properties


def discover_gsc_sites(creds) -> list[dict]:
    from googleapiclient.discovery import build

    try:
        service = build("searchconsole", "v1", credentials=creds)
        resp = service.sites().list().execute()
        return [
            {"url": entry["siteUrl"], "permission": entry.get("permissionLevel", "?")}
            for entry in resp.get("siteEntry", [])
        ]
    except Exception as e:
        print(f"Warning: could not list GSC sites: {e}", flush=True)
        return []
