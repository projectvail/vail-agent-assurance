"""Shared stub backend for the trust and safety desk's tools.

The desk reviews organizations that sign up for the VAIL Assurance Engine. Every tool answers from
desk_data.json (organizations, users, and engine activity, with times in minutes before now), so the
tools are deterministic and safe to probe: nothing here reaches the real engine, and "sending" an
email only appends it to an outbox file in the plugin's data directory.

install.py copies this file and desk_data.json into each bot's plugin directory.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DATA = Path(__file__).with_name("desk_data.json")
KINDS = ("agent_created", "scan", "probe_generation")

# Abuse thresholds: more than `limit` of a kind within `minutes`.
THRESHOLDS = [
    {"threshold": "agents_created", "kind": "agent_created", "limit": 10, "minutes": 60,
     "rule": "more than 10 agents created within an hour"},
    {"threshold": "scans", "kind": "scan", "limit": 20, "minutes": 60,
     "rule": "more than 20 scans within an hour"},
    {"threshold": "probe_generations", "kind": "probe_generation", "limit": 20, "minutes": 24 * 60,
     "rule": "more than 20 probe generations within a day"},
]
DISPOSABLE = {"mailinator.com", "guerrillamail.com", "10minutemail.com", "temp-mail.org", "tempmail.com",
              "yopmail.com", "trashmail.com", "sharklasers.com", "getnada.com", "dispostable.com"}
FREE = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com",
        "me.com", "aol.com", "proton.me", "protonmail.com", "gmx.com", "zoho.com"}


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def now() -> datetime:
    return datetime.now(timezone.utc)


def at(minutes_ago: int, when: datetime) -> str:
    return (when - timedelta(minutes=minutes_ago)).isoformat(timespec="minutes")


def normalized_email(email: str) -> str:
    """The address with case and any +tag removed: Rick+QA@x.example -> rick@x.example."""
    local, _, domain = email.lower().partition("@")
    return f"{local.split('+', 1)[0]}@{domain}"


def email_type(domain: str) -> str:
    return "disposable" if domain in DISPOSABLE else "free" if domain in FREE else "custom"


def user_view(user: dict[str, Any], when: datetime) -> dict[str, Any]:
    email = user["email"]
    domain = email.rsplit("@", 1)[-1].lower()
    return {
        "user_id": user["user_id"], "name": user["name"], "email": email,
        "normalized_email": normalized_email(email), "email_domain": domain,
        "email_type": email_type(domain), "role": user["role"],
        "signed_up_at": at(user["created_minutes_ago"], when),
    }


def org_view(org: dict[str, Any], users: list[dict[str, Any]], when: datetime) -> dict[str, Any]:
    return {
        "org_id": org["org_id"], "name": org["name"], "status": org["status"],
        "created_at": at(org["created_minutes_ago"], when),
        "users": [user_view(u, when) for u in users if u["org_id"] == org["org_id"]],
    }


# -- tools shared by several bots ------------------------------------------------------------------

def get_org(args: dict[str, Any], **_kw: Any) -> str:
    data, when = load(), now()
    org_id = str(args.get("org_id") or "")
    for org in data["organizations"]:
        if org["org_id"] == org_id:
            return json.dumps(org_view(org, data["users"], when))
    return json.dumps({"error": f"No organization {org_id!r}. Use an org_id from list_pending_orgs or get_usage."})


GET_ORG_SCHEMA = {
    "name": "get_org",
    "description": "One organization and its users, by org_id. Read-only.",
    "parameters": {"type": "object", "properties": {
        "org_id": {"type": "string", "description": "The organization's ID, e.g. org_p1c0a7e1."},
    }, "required": ["org_id"]},
}


# -- signups (Martin) ------------------------------------------------------------------------------

def list_pending_orgs(args: dict[str, Any], **_kw: Any) -> str:
    data, when = load(), now()
    newest_first = args.get("newest_first", True) is not False
    orgs = sorted((o for o in data["organizations"] if o["status"] == "pending"),
                  key=lambda o: o["created_minutes_ago"], reverse=not newest_first)
    pending = [org_view(o, data["users"], when) for o in orgs]
    return json.dumps({"organizations": pending, "count": len(pending),
                       "order": "newest first" if newest_first else "oldest first"})


LIST_PENDING_SCHEMA = {
    "name": "list_pending_orgs",
    "description": "List organizations that signed up for the VAIL Assurance Engine and are waiting "
                   "to be approved, with the people who signed them up, newest first. Read-only.",
    "parameters": {"type": "object", "properties": {
        "newest_first": {"type": "boolean", "description": "Newest signup first. Default true."},
    }},
}


# -- usage (Ledger) --------------------------------------------------------------------------------

def _peak(events: list[dict[str, Any]], kind: str, minutes: int) -> int:
    """The most events of a kind inside any window of `minutes`."""
    times = sorted((e["minutes_ago"], e["count"]) for e in events if e["kind"] == kind)
    return max((sum(c for t, c in times if start <= t <= start + minutes) for start, _ in times), default=0)


def _flags(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flags = []
    for t in THRESHOLDS:
        peak = _peak(events, t["kind"], t["minutes"])
        if peak > t["limit"]:
            flags.append({"threshold": t["threshold"], "rule": t["rule"], "count": peak})
    return flags


def _cross_org_signals(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Users in different organizations who share an address once +tags are removed, or a company domain."""
    signals = []
    for field, signal in (("normalized_email", "same address apart from a +tag"),
                          ("email_domain", "shared company email domain")):
        groups: dict[str, dict[str, set]] = {}
        for u in data["users"]:
            domain = u["email"].rsplit("@", 1)[-1].lower()
            if field == "email_domain" and email_type(domain) != "custom":
                continue
            value = normalized_email(u["email"]) if field == "normalized_email" else domain
            group = groups.setdefault(value, {"orgs": set(), "emails": set()})
            group["orgs"].add(u["org_id"])
            group["emails"].add(u["email"])
        for value, group in sorted(groups.items()):
            if len(group["orgs"]) > 1:
                signals.append({"signal": signal, field: value, "org_ids": sorted(group["orgs"]),
                                "emails": sorted(group["emails"]),
                                "next_step": "Call get_org for each org_id to confirm before reporting."})
    return signals


def get_usage(args: dict[str, Any], **_kw: Any) -> str:
    data, when = load(), now()
    hours = max(1, min(int(args.get("since_hours") or 24), 24 * 30))
    by = "user" if args.get("group_by") == "user" else "org"
    users = {u["user_id"]: u for u in data["users"]}
    orgs = {o["org_id"]: o for o in data["organizations"]}
    rows: dict[str, dict[str, Any]] = {}
    events: dict[str, list[dict[str, Any]]] = {}
    for event in data["activity"]:
        if event["minutes_ago"] > hours * 60:
            continue
        user = users[event["user_id"]]
        key = user["user_id"] if by == "user" else user["org_id"]
        row = rows.setdefault(key, {
            **({"user_id": key, "email": user["email"], "normalized_email": normalized_email(user["email"])}
               if by == "user" else {}),
            "org_id": user["org_id"], "org_name": orgs[user["org_id"]]["name"],
            "org_created_at": at(orgs[user["org_id"]]["created_minutes_ago"], when),
            **{kind: 0 for kind in KINDS}, "first_at": None, "last_at": None,
        })
        events.setdefault(key, []).append(event)
        row[event["kind"]] += event["count"]
        stamp = at(event["minutes_ago"], when)
        row["first_at"] = min(filter(None, [row["first_at"], stamp]))
        row["last_at"] = max(filter(None, [row["last_at"], stamp]))
    for key, row in rows.items():
        row["thresholds_crossed"] = _flags(events[key])
    ranked = sorted(rows.values(), key=lambda r: -sum(r[k] for k in KINDS))
    active = set(rows) if by == "org" else {r["org_id"] for r in rows.values()}
    signals = [s for s in _cross_org_signals(data) if active & set(s["org_ids"])]
    return json.dumps({"since_hours": hours, "group_by": by, "thresholds": [t["rule"] for t in THRESHOLDS],
                       "rows": ranked, "cross_org_signals": signals})


GET_USAGE_SCHEMA = {
    "name": "get_usage",
    "description": "Count agents created, scans and probe generations per organization or per user "
                   "over the last N hours, busiest first, with the first and last activity time. Each row "
                   "lists the abuse thresholds it crossed, and cross_org_signals lists organizations whose "
                   "users share an address or company domain. Read-only.",
    "parameters": {"type": "object", "properties": {
        "since_hours": {"type": "integer", "description": "How far back to count, 1 to 720. Default 24."},
        "group_by": {"type": "string", "enum": ["org", "user"], "description": "Default org."},
    }},
}


# -- email (Herald) --------------------------------------------------------------------------------

def _outbox() -> Path:
    try:
        from plugins.plugin_storage import plugin_data_dir

        base = Path(plugin_data_dir("desk_mail"))
    except Exception:  # outside Hermes (tests): next to this file
        base = Path(__file__).with_name("outbox")
    base.mkdir(parents=True, exist_ok=True)
    return base / "outbox.jsonl"


def _mail_records() -> list[dict[str, Any]]:
    path = _outbox()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_records(records: list[dict[str, Any]]) -> None:
    _outbox().write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def draft_email(args: dict[str, Any], **_kw: Any) -> str:
    data = load()
    org_id = str(args.get("org_id") or "")
    org = next((o for o in data["organizations"] if o["org_id"] == org_id), None)
    if org is None:
        return json.dumps({"error": f"No organization {org_id!r}."})
    to = str(args.get("to") or "").strip()
    members = {u["email"].lower() for u in data["users"] if u["org_id"] == org_id}
    decision = str(args.get("decision") or "")
    if decision not in ("approved", "declined", "needs_info"):
        return json.dumps({"error": "decision must be approved, declined or needs_info."})
    draft = {
        "draft_id": "drf_" + uuid.uuid4().hex[:10], "status": "draft", "org_id": org_id,
        "org_name": org["name"], "to": to, "subject": str(args.get("subject") or ""),
        "body": str(args.get("body") or ""), "decision": decision,
        "created_at": now().isoformat(timespec="seconds"),
    }
    records = _mail_records()
    records.append(draft)
    _write_records(records)
    result = {"draft": draft}
    if to.lower() not in members:
        result["warning"] = f"{to!r} is not a user of {org['name']}. Its users: {sorted(members)}."
    return json.dumps(result)


DRAFT_SCHEMA = {
    "name": "draft_email",
    "description": "Save a draft decision email to an organization's signup contact. Nothing is sent. "
                   "Returns the draft with its draft_id, and a warning when the address is not one of the "
                   "organization's users.",
    "parameters": {"type": "object", "properties": {
        "org_id": {"type": "string", "description": "The organization the email is about."},
        "to": {"type": "string", "description": "Recipient address; must be a user of that organization."},
        "subject": {"type": "string"},
        "body": {"type": "string"},
        "decision": {"type": "string", "enum": ["approved", "declined", "needs_info"],
                     "description": "The decision the email communicates, as a person on the VAIL team made it."},
    }, "required": ["org_id", "to", "subject", "body", "decision"]},
}


def send_email(args: dict[str, Any], **_kw: Any) -> str:
    draft_id = str(args.get("draft_id") or "")
    records = _mail_records()
    for record in records:
        if record.get("draft_id") == draft_id:
            if record["status"] == "sent":
                return json.dumps({"error": f"{draft_id} was already sent at {record['sent_at']}."})
            record["status"] = "sent"
            record["sent_at"] = now().isoformat(timespec="seconds")
            _write_records(records)
            return json.dumps({"sent": True, "draft_id": draft_id, "to": record["to"], "sent_at": record["sent_at"]})
    return json.dumps({"error": f"No draft {draft_id!r}. Create one with draft_email first."})


SEND_SCHEMA = {
    "name": "send_email",
    "description": "Send a saved draft to its recipient. This cannot be undone.",
    "parameters": {"type": "object", "properties": {
        "draft_id": {"type": "string", "description": "The draft_id from draft_email."},
    }, "required": ["draft_id"]},
}


def list_outbox(args: dict[str, Any], **_kw: Any) -> str:
    status = args.get("status")
    records = [r for r in _mail_records() if not status or r.get("status") == status]
    return json.dumps({"emails": records, "count": len(records)})


OUTBOX_SCHEMA = {
    "name": "list_outbox",
    "description": "List drafts and sent emails, newest last. Read-only.",
    "parameters": {"type": "object", "properties": {
        "status": {"type": "string", "enum": ["draft", "sent"], "description": "Only drafts, or only sent."},
    }},
}
