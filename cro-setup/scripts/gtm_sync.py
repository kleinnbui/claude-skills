"""Sync CRO Wizard spec into a GTM Web container (workspace-scoped, idempotent).

Spec source: cro-wizard.html:1772-1807 (GTM checklist).

Creates/updates:
  • 14 Data Layer Variables (type "v")
  • 1 Custom Event trigger ("GA4 CRO Events") matching the 3 event names by regex
  • 1 Custom HTML tag ("[CRO] Journey Tracker") fired on All Pages
  • 1 GA4 Configuration tag ("GA4 - Config - {measurementId}") if not already present
  • 1 GA4 Event tag ("GA4 - CRO Events") with 13 cro_* event parameters,
    fired by the Custom Event trigger above
  • 1 container version named "cro-setup {timestamp}" — NEVER auto-published

Idempotency: every artifact matches by name. Re-running updates in place.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import auth as auth_module
import config as cfg_module


# ── Spec ────────────────────────────────────────────────────────────────────

DLV_PARAMS = [
    "event",
    "cro_conversion_id",
    "cro_trigger_type",
    "cro_landing_page",
    "cro_submission_page",
    "cro_pages_visited",
    "cro_journey_length",
    "cro_session_ms",
    "cro_interaction",
    "cro_fail_reason",
    "cro_detection",
    "cro_elapsed_ms",
    "cro_success_selector",
    "cro_thank_you_path",
]

EVENT_PARAM_MAPPING = [
    ("cro_conversion_id", "{{DL - cro_conversion_id}}"),
    ("cro_trigger_type", "{{DL - cro_trigger_type}}"),
    ("cro_landing_page", "{{DL - cro_landing_page}}"),
    ("cro_submission_page", "{{DL - cro_submission_page}}"),
    ("cro_pages_visited", "{{DL - cro_pages_visited}}"),
    ("cro_journey_length", "{{DL - cro_journey_length}}"),
    ("cro_session_ms", "{{DL - cro_session_ms}}"),
    ("cro_interaction", "{{DL - cro_interaction}}"),
    ("cro_fail_reason", "{{DL - cro_fail_reason}}"),
    ("cro_detection", "{{DL - cro_detection}}"),
    ("cro_elapsed_ms", "{{DL - cro_elapsed_ms}}"),
    ("cro_success_selector", "{{DL - cro_success_selector}}"),
    ("cro_thank_you_path", "{{DL - cro_thank_you_path}}"),
]

CRO_EVENT_REGEX = "conversion_success|conversion_attempt_failed|form_interaction|funnel_step"
ALL_PAGES_BUILTIN_TRIGGER_ID = "2147479553"  # GTM magic constant


# ── Service builder ─────────────────────────────────────────────────────────

def _service(profile: str | None = None):
    from googleapiclient.discovery import build
    creds = auth_module.load_credentials(cfg_module.credentials_path(profile))
    return build("tagmanager", "v2", credentials=creds, cache_discovery=False)


def _workspace_path(profile_cfg: dict) -> str:
    return (
        f"accounts/{profile_cfg['gtm_account_id']}"
        f"/containers/{profile_cfg['gtm_container_id']}"
        f"/workspaces/{profile_cfg['gtm_workspace_id']}"
    )


# ── DLV spec builder ────────────────────────────────────────────────────────

def _dlv_body(param_name: str) -> dict:
    return {
        "name": f"DL - {param_name}",
        "type": "v",
        "parameter": [
            {"key": "name", "type": "template", "value": param_name},
            {"key": "dataLayerVersion", "type": "integer", "value": "2"},
        ],
    }


# ── Trigger spec builder ────────────────────────────────────────────────────

def _trigger_body() -> dict:
    return {
        "name": "GA4 CRO Events",
        "type": "customEvent",
        "customEventFilter": [
            {
                "type": "matchRegex",
                "parameter": [
                    {"key": "arg0", "type": "template", "value": "{{_event}}"},
                    {"key": "arg1", "type": "template", "value": CRO_EVENT_REGEX},
                ],
            }
        ],
    }


# ── Tag spec builders ──────────────────────────────────────────────────────

def _html_tag_body(engine_html: str) -> dict:
    return {
        "name": "[CRO] Journey Tracker",
        "type": "html",
        "parameter": [
            {"key": "html", "type": "template", "value": engine_html},
            {"key": "supportDocumentWrite", "type": "boolean", "value": "false"},
        ],
        "firingTriggerId": [ALL_PAGES_BUILTIN_TRIGGER_ID],
        "priority": {"type": "integer", "key": "priority", "value": "100"},
    }


def _ga4_config_tag_body(measurement_id: str) -> dict:
    """GA4 Configuration tag (googtag type)."""
    return {
        "name": f"GA4 - Config - {measurement_id}",
        "type": "googtag",
        "parameter": [
            {"key": "tagId", "type": "template", "value": measurement_id},
        ],
        "firingTriggerId": [ALL_PAGES_BUILTIN_TRIGGER_ID],
    }


def _ga4_event_tag_body(trigger_id: str, measurement_id: str) -> dict:
    """GA4 Event tag (gaawe type) with 13 cro_* event parameters."""
    event_params_list = [
        {
            "type": "map",
            "map": [
                {"key": "name", "type": "template", "value": name},
                {"key": "value", "type": "template", "value": value},
            ],
        }
        for name, value in EVENT_PARAM_MAPPING
    ]
    return {
        "name": "GA4 - CRO Events",
        "type": "gaawe",
        "parameter": [
            {"key": "eventName", "type": "template", "value": "{{DL - event}}"},
            {"key": "measurementIdOverride", "type": "template", "value": measurement_id},
            {
                "key": "eventParameters",
                "type": "list",
                "list": event_params_list,
            },
        ],
        "firingTriggerId": [trigger_id],
    }


# ── List + match-by-name helpers ────────────────────────────────────────────

def _list_by_name(items: list, key: str = "name") -> dict:
    return {it.get(key): it for it in items if it.get(key)}


def _list_variables(svc, ws_path: str) -> dict:
    resp = svc.accounts().containers().workspaces().variables().list(parent=ws_path).execute()
    return _list_by_name(resp.get("variable", []))


def _list_triggers(svc, ws_path: str) -> dict:
    resp = svc.accounts().containers().workspaces().triggers().list(parent=ws_path).execute()
    return _list_by_name(resp.get("trigger", []))


def _list_tags(svc, ws_path: str) -> dict:
    resp = svc.accounts().containers().workspaces().tags().list(parent=ws_path).execute()
    return _list_by_name(resp.get("tag", []))


# ── Sync operations ────────────────────────────────────────────────────────

def _upsert_variable(svc, ws_path: str, existing: dict, body: dict) -> tuple[str, dict]:
    """Returns (action, item) — action in {CREATE, UPDATE, NO_OP}."""
    cur = existing.get(body["name"])
    if cur:
        merged = {**cur, **body}
        result = svc.accounts().containers().workspaces().variables().update(
            path=cur["path"], body=merged
        ).execute()
        action = "UPDATE"
    else:
        result = svc.accounts().containers().workspaces().variables().create(
            parent=ws_path, body=body
        ).execute()
        action = "CREATE"
    return action, result


def _upsert_trigger(svc, ws_path: str, existing: dict, body: dict) -> tuple[str, dict]:
    cur = existing.get(body["name"])
    if cur:
        merged = {**cur, **body}
        result = svc.accounts().containers().workspaces().triggers().update(
            path=cur["path"], body=merged
        ).execute()
        action = "UPDATE"
    else:
        result = svc.accounts().containers().workspaces().triggers().create(
            parent=ws_path, body=body
        ).execute()
        action = "CREATE"
    return action, result


def _upsert_tag(svc, ws_path: str, existing: dict, body: dict) -> tuple[str, dict]:
    cur = existing.get(body["name"])
    if cur:
        merged = {**cur, **body}
        result = svc.accounts().containers().workspaces().tags().update(
            path=cur["path"], body=merged
        ).execute()
        action = "UPDATE"
    else:
        result = svc.accounts().containers().workspaces().tags().create(
            parent=ws_path, body=body
        ).execute()
        action = "CREATE"
    return action, result


# ── Stale-workspace retry ──────────────────────────────────────────────────

def _with_workspace_retry(profile_cfg: dict, fn):
    """Run fn(); on 'Workspace is already submitted' (HTTP 400), refresh
    Default Workspace in-place (mutates profile_cfg + persists accounts.json)
    and retry fn() once.

    Workspace gets consumed whenever GTM creates a version from it (by this
    skill or via the UI). A subsequent run pointing at the stale workspace
    fails with 400. This wrapper auto-recovers so user doesn't have to
    manually re-discover and update profile.
    """
    from googleapiclient.errors import HttpError
    try:
        return fn()
    except HttpError as e:
        if e.resp.status == 400 and "Workspace is already submitted" in str(e):
            svc = _service(profile_cfg.get("_profile_name"))
            new_id = _refresh_default_workspace(
                svc, profile_cfg,
                current_workspace_id=profile_cfg.get("gtm_workspace_id", ""),
            )
            profile_cfg["gtm_workspace_id"] = new_id
            return fn()
        raise


# ── Public entry ────────────────────────────────────────────────────────────

def preview(profile_cfg: dict) -> dict:
    """Return planned diff without mutating anything."""
    return _with_workspace_retry(profile_cfg, lambda: _preview_impl(profile_cfg))


def _preview_impl(profile_cfg: dict) -> dict:
    svc = _service(profile_cfg.get("_profile_name"))
    ws_path = _workspace_path(profile_cfg)

    variables = _list_variables(svc, ws_path)
    triggers = _list_triggers(svc, ws_path)
    tags = _list_tags(svc, ws_path)

    measurement_id = profile_cfg.get("ga4_measurement_id", "")
    warnings = []
    if not measurement_id:
        warnings.append("ga4_measurement_id missing from profile — GA4 Config + Event tags sẽ bị bỏ qua khi apply. Re-run /cro-setup để cập nhật profile.")
    plan = []

    for p in DLV_PARAMS:
        name = f"DL - {p}"
        plan.append({"kind": "variable", "name": name,
                     "action": "UPDATE" if name in variables else "CREATE"})

    plan.append({"kind": "trigger", "name": "GA4 CRO Events",
                 "action": "UPDATE" if "GA4 CRO Events" in triggers else "CREATE"})

    plan.append({"kind": "tag", "name": "[CRO] Journey Tracker",
                 "action": "UPDATE" if "[CRO] Journey Tracker" in tags else "CREATE"})

    has_ga4_config = any(
        t.get("type") == "googtag" and any(
            p.get("key") == "tagId" and p.get("value") == measurement_id
            for p in t.get("parameter", [])
        )
        for t in tags.values()
    ) if measurement_id else False
    if measurement_id and not has_ga4_config:
        plan.append({"kind": "tag", "name": f"GA4 - Config - {measurement_id}",
                     "action": "CREATE"})

    plan.append({"kind": "tag", "name": "GA4 - CRO Events",
                 "action": "UPDATE" if "GA4 - CRO Events" in tags else "CREATE"})

    return {"workspace_path": ws_path, "plan": plan, "warnings": warnings}


def sync(profile_cfg: dict, engine_html: str) -> dict:
    """Apply CRO spec, then create a version (NOT published).

    Returns dict with: actions[], version_id, version_name.
    """
    return _with_workspace_retry(profile_cfg, lambda: _sync_impl(profile_cfg, engine_html))


def _sync_impl(profile_cfg: dict, engine_html: str) -> dict:
    svc = _service(profile_cfg.get("_profile_name"))
    ws_path = _workspace_path(profile_cfg)
    measurement_id = profile_cfg.get("ga4_measurement_id", "")
    if not measurement_id:
        raise ValueError("ga4_measurement_id missing from profile — re-run /cro-setup")

    actions = []

    # 1. DLVs
    variables = _list_variables(svc, ws_path)
    for p in DLV_PARAMS:
        action, item = _upsert_variable(svc, ws_path, variables, _dlv_body(p))
        actions.append({"kind": "variable", "name": item["name"], "action": action, "id": item.get("variableId", "")})

    # 2. Trigger
    triggers = _list_triggers(svc, ws_path)
    action, trigger = _upsert_trigger(svc, ws_path, triggers, _trigger_body())
    trigger_id = trigger["triggerId"]
    actions.append({"kind": "trigger", "name": trigger["name"], "action": action, "id": trigger_id})

    # 3. Custom HTML tag (engine)
    tags = _list_tags(svc, ws_path)
    action, tag = _upsert_tag(svc, ws_path, tags, _html_tag_body(engine_html))
    actions.append({"kind": "tag", "name": tag["name"], "action": action, "id": tag.get("tagId", "")})

    # 4. GA4 Config tag — reuse existing if one matches measurement_id, else create
    existing_googtag = None
    for t in tags.values():
        if t.get("type") != "googtag":
            continue
        params = t.get("parameter", [])
        if any(p.get("key") == "tagId" and p.get("value") == measurement_id for p in params):
            existing_googtag = t
            break
    if not existing_googtag:
        action, config_tag = _upsert_tag(svc, ws_path, tags, _ga4_config_tag_body(measurement_id))
        actions.append({"kind": "tag", "name": config_tag["name"], "action": action, "id": config_tag.get("tagId", "")})

    # 5. GA4 Event tag (refresh listing — Config tag may have just been created)
    tags = _list_tags(svc, ws_path)
    action, event_tag = _upsert_tag(svc, ws_path, tags, _ga4_event_tag_body(trigger_id, measurement_id))
    actions.append({"kind": "tag", "name": event_tag["name"], "action": action, "id": event_tag.get("tagId", "")})

    # 6. Create version (NOT published)
    ts = time.strftime("%Y%m%d-%H%M")
    version_name = f"cro-setup {ts}"
    version_resp = svc.accounts().containers().workspaces().create_version(
        path=ws_path,
        body={"name": version_name, "notes": "Auto-installed by /cro-setup. Review in Preview, then Publish manually."},
    ).execute()

    version = version_resp.get("containerVersion") or {}

    # GTM consumes the workspace on create_version + auto-creates a new Default
    # Workspace. Update profile so next run targets the fresh workspace.
    new_workspace_id = _refresh_default_workspace(
        svc, profile_cfg, current_workspace_id=profile_cfg["gtm_workspace_id"]
    )

    return {
        "actions": actions,
        "version_id": version.get("containerVersionId", ""),
        "version_name": version_name,
        "compiler_error": version_resp.get("compilerError", False),
        "sync_status": version_resp.get("syncStatus", {}),
        "new_workspace_id": new_workspace_id,
    }


def sync_engine_only(profile_cfg: dict, engine_html: str) -> dict:
    """Update only the [CRO] Journey Tracker tag, then create a version (NOT published).

    Use when engine.py changed but DLVs / trigger / GA4 definitions are unchanged.
    Much faster than full sync — only 1 API write + create_version.
    """
    return _with_workspace_retry(profile_cfg, lambda: _sync_engine_only_impl(profile_cfg, engine_html))


def _sync_engine_only_impl(profile_cfg: dict, engine_html: str) -> dict:
    svc = _service(profile_cfg.get("_profile_name"))
    ws_path = _workspace_path(profile_cfg)

    tags = _list_tags(svc, ws_path)
    action, tag = _upsert_tag(svc, ws_path, tags, _html_tag_body(engine_html))

    ts = time.strftime("%Y%m%d-%H%M")
    version_name = f"cro-setup {ts}"
    version_resp = svc.accounts().containers().workspaces().create_version(
        path=ws_path,
        body={"name": version_name, "notes": "Engine-only update by /cro-setup."},
    ).execute()

    version = version_resp.get("containerVersion") or {}
    new_workspace_id = _refresh_default_workspace(
        svc, profile_cfg, current_workspace_id=profile_cfg["gtm_workspace_id"]
    )

    return {
        "actions": [{"kind": "tag", "name": tag["name"], "action": action, "id": tag.get("tagId", "")}],
        "version_id": version.get("containerVersionId", ""),
        "version_name": version_name,
        "compiler_error": version_resp.get("compilerError", False),
        "sync_status": version_resp.get("syncStatus", {}),
        "new_workspace_id": new_workspace_id,
    }


def _refresh_default_workspace(svc, profile_cfg: dict, current_workspace_id: str) -> str:
    """After create_version consumes the workspace, find the new Default
    Workspace and persist its ID back into accounts.json."""
    container_path = (
        f"accounts/{profile_cfg['gtm_account_id']}"
        f"/containers/{profile_cfg['gtm_container_id']}"
    )
    resp = svc.accounts().containers().workspaces().list(parent=container_path).execute()
    new_id = None
    for w in resp.get("workspace", []):
        if w.get("name") == "Default Workspace":
            new_id = w["workspaceId"]
            break
    if new_id and new_id != current_workspace_id:
        cfg_module.upsert_profile(profile_cfg["_profile_name"], gtm_workspace_id=new_id)
    return new_id or current_workspace_id
