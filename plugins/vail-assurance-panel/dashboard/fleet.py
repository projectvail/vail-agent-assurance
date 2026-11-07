"""The assurance view of a Hermes install: its profiles, and what VAIL knows about each one.

Pure logic with no Hermes imports, so it can be tested on its own. plugin_api.py supplies the Hermes
root, the data directory, and a VailClient.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SEVERITIES = ("critical", "high", "medium", "low")

# What defines a profile as an agent, i.e. what VAIL would scan. Never credentials or history: no .env,
# auth files, sessions, memories, logs, or state databases.
_SOURCE_FILES = ("SOUL.md", "config.yaml")
_SOURCE_DIRS = ("skills", "plugins")
_SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv"}
_MAX_WALK = 5000
_PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


# -- profiles ----------------------------------------------------------------------------------------

def profile_dirs(root: Path) -> list[tuple[str, Path]]:
    """``default`` (the Hermes root itself) plus every named profile under ``profiles/``."""
    found = [("default", root)]
    profiles_root = root / "profiles"
    if profiles_root.is_dir():
        for entry in sorted(profiles_root.iterdir()):
            if (entry.is_dir() and entry.name != "default" and _PROFILE_NAME.match(entry.name)
                    and any((entry / name).exists() for name in _SOURCE_FILES)):
                found.append((entry.name, entry))
    return found


def describe_profile(name: str, home: Path) -> dict[str, Any]:
    """What the profile is made of, and when that last changed."""
    skills = 0
    newest = 0.0
    walked = 0
    for filename in _SOURCE_FILES:
        path = home / filename
        if path.is_file():
            newest = max(newest, path.stat().st_mtime)
    for dirname in _SOURCE_DIRS:
        base = home / dirname
        if not base.is_dir():
            continue
        for current, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
            if dirname == "skills" and "SKILL.md" in files:
                skills += 1
            for filename in files:
                walked += 1
                if walked > _MAX_WALK:
                    break
                try:
                    newest = max(newest, os.stat(os.path.join(current, filename)).st_mtime)
                except OSError:
                    continue
    plugins = []
    plugins_dir = home / "plugins"
    if plugins_dir.is_dir():
        plugins = sorted(entry.name for entry in plugins_dir.iterdir()
                         if entry.is_dir() and ((entry / "plugin.yaml").exists() or (entry / "plugin.json").exists()))
    return {
        "name": name,
        "has_soul": (home / "SOUL.md").is_file(),
        "skills": skills,
        "plugins": plugins,
        "changed_at": _iso(newest) if newest else None,
    }


# -- links between profiles and VAIL agents ----------------------------------------------------------

class LinkStore:
    """profile name -> VAIL agent id, kept in the plugin's data directory."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def load(self) -> dict[str, str]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {str(k): str(v) for k, v in data.items() if isinstance(v, str)} if isinstance(data, dict) else {}

    def set(self, profile: str, agent_id: str | None) -> dict[str, str]:
        with self._lock:
            links = self.load()
            if agent_id:
                links[profile] = agent_id
            else:
                links.pop(profile, None)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(links, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self.path)
            return links


def suggest_agent(profile: str, agents: list[dict]) -> str | None:
    """A Hermes agent on VAIL whose name is the profile's name, alone or followed by a qualifier."""
    wanted = profile.casefold()
    for agent in agents:
        if agent.get("platform") != "hermes":
            continue
        name = str(agent.get("name") or "").casefold().strip()
        if name == wanted or re.match(rf"^{re.escape(wanted)}\b", name):
            return agent.get("agent_id")
    return None


# -- VAIL results ------------------------------------------------------------------------------------

def summarize_agent(client: Any, agent_id: str) -> dict[str, Any]:
    """Stage, risk counts by severity, and probe coverage for one VAIL agent."""
    status = client.call("get_agent_status", {"agent_id": agent_id})
    results = status.get("results") or {}
    source = status.get("source") or {}
    summary: dict[str, Any] = {
        "agent_id": agent_id,
        "name": status.get("name"),
        "platform": status.get("platform"),
        "stage": status.get("stage"),
        "outdated": bool(results.get("outdated")),
        "scanned_at": source.get("collected_at"),
        "active_operation": (status.get("active_operation") or {}).get("label"),
        "risks": {severity: 0 for severity in SEVERITIES},
        "risk_total": 0,
        "probes": 0,
        "untested": 0,
    }
    if not results.get("behaviors"):
        return summary
    behaviors = client.call_results("get_behaviors", {"agent_id": agent_id})
    risks = _vulnerabilities(behaviors)
    probed: dict[str, int] = {}
    if results.get("probes"):
        probes = client.call_results("get_probes", {"agent_id": agent_id})
        vulnerability_probes = _probe_list(probes.get("vulnerability_probes"))
        summary["probes"] = len(vulnerability_probes) + len(_probe_list(probes.get("control_probes")))
        for probe in vulnerability_probes:
            for behavior_id in probe.get("behavior_ids") or []:
                probed[behavior_id] = probed.get(behavior_id, 0) + 1
    for risk in risks:
        severity = str(risk.get("severity") or "").lower()
        if severity in summary["risks"]:
            summary["risks"][severity] += 1
    summary["risk_total"] = len(risks)
    summary["untested"] = sum(1 for risk in risks if not probed.get(risk.get("id")))
    return summary


def risk_details(client: Any, agent_id: str) -> list[dict[str, Any]]:
    """Each behavior risk with its evidence tools and how many probes test it, most severe first."""
    behaviors = client.call_results("get_behaviors", {"agent_id": agent_id})
    try:
        probes = client.call_results("get_probes", {"agent_id": agent_id})
    except Exception:  # no probes yet is normal
        probes = {}
    probed: dict[str, list[str]] = {}
    for probe in _probe_list(probes.get("vulnerability_probes")):
        for behavior_id in probe.get("behavior_ids") or []:
            probed.setdefault(behavior_id, []).append(probe.get("id") or "")
    details = []
    for risk in _vulnerabilities(behaviors):
        tools: list[str] = []
        for requirement in risk.get("requirements") or []:
            for evidence in requirement.get("evidence") or []:
                for tool in evidence.get("tool_names") or []:
                    if tool not in tools:
                        tools.append(tool)
        details.append({
            "id": risk.get("id"),
            "title": risk.get("title"),
            "severity": str(risk.get("severity") or "").lower(),
            "description": risk.get("description"),
            "category": risk.get("category"),
            "tools": tools,
            "probes": probed.get(risk.get("id"), []),
        })
    order = {severity: index for index, severity in enumerate(SEVERITIES)}
    details.sort(key=lambda item: order.get(item["severity"], len(order)))
    return details


def _vulnerabilities(behaviors: dict) -> list[dict]:
    section = behaviors.get("vulnerabilities") or {}
    items = section.get("behaviors") if isinstance(section, dict) else section
    return [item for item in items or [] if isinstance(item, dict)]


def _probe_list(section: Any) -> list[dict]:
    items = section.get("probes") if isinstance(section, dict) else section
    return [item for item in items or [] if isinstance(item, dict)]


# -- the whole view ----------------------------------------------------------------------------------

class TTLCache:
    def __init__(self, seconds: float):
        self.seconds = seconds
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str, compute: Callable[[], Any], *, fresh: bool = False) -> Any:
        now = time.monotonic()
        with self._lock:
            hit = self._items.get(key)
        if hit and not fresh and now - hit[0] < self.seconds:
            return hit[1]
        value = compute()
        with self._lock:
            self._items[key] = (time.monotonic(), value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


def build_fleet(root: Path, links: LinkStore, client_factory: Callable[[], Any], cache: TTLCache,
                *, vail_url: str, refresh: bool = False) -> dict[str, Any]:
    profiles = [describe_profile(name, home) for name, home in profile_dirs(root)]
    linked = links.load()
    view: dict[str, Any] = {"vail": {"url": vail_url, "connected": False}, "profiles": profiles, "agents": []}
    try:
        client = client_factory()
        identity = cache.get("identity", lambda: client.call("get_identity"), fresh=refresh)
        agents = cache.get("agents", lambda: client.call("list_agents").get("agents", []), fresh=refresh)
    except Exception as exc:  # noqa: BLE001 - shown to the user as the connection state
        view["vail"].update(error=str(exc), code=getattr(exc, "code", None))
        for profile in profiles:
            profile["link"] = linked.get(profile["name"])
        return view
    organization = identity.get("organization") or {}
    view["vail"].update(connected=True, organization=organization.get("name"),
                        organization_id=organization.get("organization_id") or organization.get("id"))
    view["agents"] = [{"agent_id": a.get("agent_id"), "name": a.get("name"), "platform": a.get("platform"),
                       "stage": a.get("stage")} for a in agents]
    known = {a.get("agent_id") for a in agents}
    for profile in profiles:
        agent_id = linked.get(profile["name"])
        profile["link"] = agent_id
        if agent_id is None:
            profile["suggested"] = suggest_agent(profile["name"], agents)
            continue
        if agent_id not in known:
            profile["vail"] = {"agent_id": agent_id, "error": "This VAIL agent no longer exists."}
            continue
        try:
            summary = cache.get(f"agent:{agent_id}", lambda: summarize_agent(client, agent_id), fresh=refresh)
        except Exception as exc:  # noqa: BLE001 - one agent's failure must not hide the others
            summary = {"agent_id": agent_id, "error": str(exc)}
        profile["vail"] = summary
        scanned = _parse_iso(summary.get("scanned_at"))
        changed = _parse_iso(profile.get("changed_at"))
        profile["changed_since_scan"] = bool(scanned and changed and changed > scanned)
    return view


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
