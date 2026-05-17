"""Sync CRO spec into a GA4 property (idempotent).

Spec source: cro-wizard.html:1813-1841 (GA4 checklist).

Creates (no UPDATE — GA4 immutable parameter names):
  • 10 Custom Dimensions (Event scope)
  • 3 Custom Metrics (Event scope)
  • 1 Key Event: conversion_success (counting method: ONCE_PER_EVENT)

Match-by-parameterName. If a definition already exists with the same parameter
name, it's left alone (NO_OP). GA4 does not allow changing parameterName after
creation, so we never UPDATE — we only CREATE or skip.

Note: Custom dimensions/metrics show data only AFTER the parameter actually
arrives in events. They appear in Reports 24-48h later.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import auth as auth_module
import config as cfg_module


# ── Spec ────────────────────────────────────────────────────────────────────

CUSTOM_DIMENSIONS = [
    {"displayName": "CRO Conversion ID",    "parameterName": "cro_conversion_id"},
    {"displayName": "CRO Trigger Type",     "parameterName": "cro_trigger_type"},
    {"displayName": "CRO Landing Page",     "parameterName": "cro_landing_page"},
    {"displayName": "CRO Submission Page",  "parameterName": "cro_submission_page"},
    {"displayName": "CRO Pages Visited",    "parameterName": "cro_pages_visited"},
    {"displayName": "CRO Interaction",      "parameterName": "cro_interaction"},
    {"displayName": "CRO Fail Reason",      "parameterName": "cro_fail_reason"},
    {"displayName": "CRO Detection Method", "parameterName": "cro_detection"},
    {"displayName": "CRO Success Selector", "parameterName": "cro_success_selector"},
    {"displayName": "CRO Thank You Path",   "parameterName": "cro_thank_you_path"},
]

CUSTOM_METRICS = [
    {"displayName": "CRO Journey Length",   "parameterName": "cro_journey_length",
     "measurementUnit": "STANDARD"},
    {"displayName": "CRO Session Duration", "parameterName": "cro_session_ms",
     "measurementUnit": "MILLISECONDS"},
    {"displayName": "CRO Click to Success", "parameterName": "cro_elapsed_ms",
     "measurementUnit": "MILLISECONDS"},
]

KEY_EVENT_NAME = "conversion_success"


# ── Service builder ─────────────────────────────────────────────────────────

def _service(profile: str | None = None):
    from googleapiclient.discovery import build
    creds = auth_module.load_credentials(cfg_module.credentials_path(profile))
    return build("analyticsadmin", "v1beta", credentials=creds, cache_discovery=False)


def _property_path(profile_cfg: dict) -> str:
    return f"properties/{profile_cfg['ga4_property_id']}"


# ── List + match helpers ────────────────────────────────────────────────────

def _list_custom_dimensions(svc, prop_path: str) -> dict:
    items, page_token = [], None
    while True:
        kwargs = {"parent": prop_path}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = svc.properties().customDimensions().list(**kwargs).execute()
        items.extend(resp.get("customDimensions", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return {it["parameterName"]: it for it in items}


def _list_custom_metrics(svc, prop_path: str) -> dict:
    items, page_token = [], None
    while True:
        kwargs = {"parent": prop_path}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = svc.properties().customMetrics().list(**kwargs).execute()
        items.extend(resp.get("customMetrics", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return {it["parameterName"]: it for it in items}


def _list_key_events(svc, prop_path: str) -> dict:
    items, page_token = [], None
    while True:
        kwargs = {"parent": prop_path}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = svc.properties().keyEvents().list(**kwargs).execute()
        items.extend(resp.get("keyEvents", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return {it["eventName"]: it for it in items}


# ── Public entry ────────────────────────────────────────────────────────────

def preview(profile_cfg: dict) -> dict:
    svc = _service(profile_cfg.get("_profile_name"))
    prop_path = _property_path(profile_cfg)

    dims = _list_custom_dimensions(svc, prop_path)
    mets = _list_custom_metrics(svc, prop_path)
    kes = _list_key_events(svc, prop_path)

    plan = []
    for d in CUSTOM_DIMENSIONS:
        plan.append({"kind": "custom_dimension", "name": d["displayName"],
                     "parameter": d["parameterName"],
                     "action": "NO_OP" if d["parameterName"] in dims else "CREATE"})
    for m in CUSTOM_METRICS:
        plan.append({"kind": "custom_metric", "name": m["displayName"],
                     "parameter": m["parameterName"],
                     "action": "NO_OP" if m["parameterName"] in mets else "CREATE"})
    plan.append({"kind": "key_event", "name": KEY_EVENT_NAME,
                 "action": "NO_OP" if KEY_EVENT_NAME in kes else "CREATE"})
    return {"property_path": prop_path, "plan": plan}


def sync(profile_cfg: dict) -> dict:
    svc = _service(profile_cfg.get("_profile_name"))
    prop_path = _property_path(profile_cfg)

    dims = _list_custom_dimensions(svc, prop_path)
    mets = _list_custom_metrics(svc, prop_path)
    kes = _list_key_events(svc, prop_path)

    actions = []

    for d in CUSTOM_DIMENSIONS:
        if d["parameterName"] in dims:
            actions.append({"kind": "custom_dimension", "name": d["displayName"],
                            "action": "NO_OP"})
            continue
        body = {"displayName": d["displayName"], "parameterName": d["parameterName"], "scope": "EVENT"}
        result = svc.properties().customDimensions().create(parent=prop_path, body=body).execute()
        actions.append({"kind": "custom_dimension", "name": result["displayName"],
                        "action": "CREATE", "id": result["name"].split("/")[-1]})

    for m in CUSTOM_METRICS:
        if m["parameterName"] in mets:
            actions.append({"kind": "custom_metric", "name": m["displayName"],
                            "action": "NO_OP"})
            continue
        body = {
            "displayName": m["displayName"],
            "parameterName": m["parameterName"],
            "scope": "EVENT",
            "measurementUnit": m["measurementUnit"],
        }
        result = svc.properties().customMetrics().create(parent=prop_path, body=body).execute()
        actions.append({"kind": "custom_metric", "name": result["displayName"],
                        "action": "CREATE", "id": result["name"].split("/")[-1]})

    if KEY_EVENT_NAME in kes:
        actions.append({"kind": "key_event", "name": KEY_EVENT_NAME, "action": "NO_OP"})
    else:
        body = {"eventName": KEY_EVENT_NAME, "countingMethod": "ONCE_PER_EVENT"}
        result = svc.properties().keyEvents().create(parent=prop_path, body=body).execute()
        actions.append({"kind": "key_event", "name": result["eventName"],
                        "action": "CREATE", "id": result["name"].split("/")[-1]})

    return {"actions": actions, "property_path": prop_path}
