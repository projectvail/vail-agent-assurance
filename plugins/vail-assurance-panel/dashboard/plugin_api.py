"""Backend routes for the VAIL Assurance panel, mounted by Hermes under /api/plugins/vail-assurance-panel/.

Hermes imports this file on its own (not as part of a package), so the sibling modules are loaded by
path. Routes are plain `def`s: FastAPI runs them in a worker thread, so the blocking VAIL calls never
hold the gateway's event loop.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

PLUGIN_ID = "vail-assurance-panel"
DEFAULT_URL = "https://agents.projectvail.com/mcp"
_HERE = Path(__file__).resolve().parent


def _load(name: str):
    module_name = f"hermes_dashboard_plugin_{PLUGIN_ID.replace('-', '_')}_{name}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


vail_client = _load("vail_client")
fleet = _load("fleet")
package = _load("package")
scan = _load("scan")

router = APIRouter()
_cache = fleet.TTLCache(seconds=120)
_jobs = scan.ScanJobs()


def _settings() -> dict:
    from hermes_cli.config import load_config_readonly

    entry = ((load_config_readonly().get("plugins") or {}).get("entries") or {}).get(PLUGIN_ID) or {}
    return entry.get("settings") or {}


def _vail_url() -> str:
    return str(_settings().get("vail_url") or DEFAULT_URL).strip()


def _client():
    from agent.secret_scope import get_secret

    return vail_client.VailClient(_vail_url(), get_secret("VAIL_TOKEN") or "", client_name=PLUGIN_ID)


def _root() -> Path:
    from hermes_constants import get_default_hermes_root

    return Path(get_default_hermes_root())


def _links():
    from plugins.plugin_storage import plugin_data_dir

    return fleet.LinkStore(Path(plugin_data_dir(PLUGIN_ID)) / "links.json")


def _profile_home(name: str) -> Path:
    homes = dict(fleet.profile_dirs(_root()))
    if name not in homes:
        raise HTTPException(status_code=404, detail=f"No Hermes profile named {name!r}")
    return homes[name]


@router.get("/fleet")
def get_fleet(refresh: bool = False):
    jobs = _jobs.all()
    if any(job.get("phase") not in ("done", "failed") for job in jobs.values()):
        refresh = True  # a scan is moving: show VAIL's current state, not the cache
    view = fleet.build_fleet(_root(), _links(), _client, _cache, vail_url=_vail_url(), refresh=refresh)
    for profile in view["profiles"]:
        if profile["name"] in jobs:
            profile["job"] = jobs[profile["name"]]
    return view


@router.get("/profiles/{name}/package")
def preview_package(name: str):
    """Exactly what a scan would upload for this profile, before anything is sent."""
    return package.build_package(name, _profile_home(name)).summary()


class ScanBody(BaseModel):
    generate_probes: bool = True


@router.post("/profiles/{name}/scan")
def start_scan(name: str, body: ScanBody):
    home = _profile_home(name)

    def on_change(profile: str, job: dict) -> None:
        _cache.clear()
        try:
            from hermes_cli.plugin_events import broadcast_plugin_event

            broadcast_plugin_event(PLUGIN_ID, "scan.updated", {"profile": profile, "phase": job.get("phase")})
        except Exception:  # noqa: BLE001 - the page also polls while a scan runs
            pass

    try:
        job = scan.start_scan(profile=name, home=home, client=_client(), links=_links(), jobs=_jobs,
                              package_module=package, upload=vail_client.post_multipart,
                              generate_probes=body.generate_probes, on_change=on_change)
    except scan.ScanError as exc:
        raise HTTPException(status_code=409 if "already running" in str(exc) else 502, detail=str(exc)) from None
    return {"ok": True, "job": job}


class LinkBody(BaseModel):
    profile: str
    agent_id: str | None = None


@router.post("/link")
def set_link(body: LinkBody):
    names = {name for name, _ in fleet.profile_dirs(_root())}
    if body.profile not in names:
        raise HTTPException(status_code=404, detail=f"No Hermes profile named {body.profile!r}")
    links = _links().set(body.profile, body.agent_id)
    return {"ok": True, "links": links}


@router.get("/agents/{agent_id}/risks")
def get_risks(agent_id: str, refresh: bool = False):
    try:
        client = _client()
        risks = _cache.get(f"risks:{agent_id}", lambda: fleet.risk_details(client, agent_id), fresh=refresh)
    except vail_client.VailError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    return {"agent_id": agent_id, "risks": risks}
