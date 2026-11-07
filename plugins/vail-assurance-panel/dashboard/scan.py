"""Scan a Hermes profile with VAIL: create its agent if needed, upload its source, scan, generate probes.

The steps that can fail fast (creating the agent, packaging, uploading, starting the scan) run in the
request, so their errors reach the user directly. Waiting for the scan and then generating probes runs in
a short-lived background thread that follows VAIL's own operation status; VAIL keeps working even if Hermes
restarts, and the panel reads progress from VAIL, so a lost thread only means probes must be started again.
"""

from __future__ import annotations

import contextvars
import secrets
import threading
import time
from typing import Any, Callable

POLL_SECONDS = 15
MAX_WAIT_SECONDS = 45 * 60


class ScanJobs:
    """In-memory record of scans this Hermes process started, keyed by profile name."""

    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, profile: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(profile)
            return dict(job) if job else None

    def all(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {name: dict(job) for name, job in self._jobs.items()}

    def update(self, profile: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.setdefault(profile, {"profile": profile})
            job.update(fields, updated_at=time.time())
            return dict(job)

    def running(self, profile: str) -> bool:
        job = self.get(profile)
        return bool(job and job.get("phase") not in (None, "done", "failed"))


def start_scan(*, profile: str, home, client: Any, links: Any, jobs: ScanJobs, package_module: Any,
               upload: Callable[[str, dict, str, bytes], None], generate_probes: bool,
               on_change: Callable[[str, dict], None]) -> dict[str, Any]:
    """Run the fast steps now and hand the waiting to a background thread. Returns the job."""
    if jobs.running(profile):
        raise ScanError("A scan for this profile is already running.")

    def step(phase: str, **extra: Any) -> dict[str, Any]:
        job = jobs.update(profile, phase=phase, **extra)
        on_change(profile, job)
        return job

    step("packaging", error=None, operation_id=None, started_at=time.time())
    try:
        pkg = package_module.build_package(profile, home)
        if not pkg.files:
            raise ScanError("Nothing to scan: this profile has no SOUL.md, config.yaml, skills or plugins.")

        agent_id = links.load().get(profile)
        if not agent_id:
            step("creating agent")
            created = client.call("create_agent", {
                "name": f"{profile} (Hermes profile)"[:100],
                "platform": "hermes",
                "request_key": f"hermes-{profile}-{secrets.token_hex(8)}"[:128],
            })
            agent_id = created.get("agent_id")
            if not agent_id:
                raise ScanError("VAIL did not return an agent id.")
            links.set(profile, agent_id)

        step("uploading", agent_id=agent_id, file_count=len(pkg.files), redactions=pkg.redactions)
        filename = f"{profile}-hermes-profile.tar.gz"
        prepared = client.call("prepare_source_upload", {
            "agent_id": agent_id,
            "files": [{"path": filename, "size": len(pkg.archive),
                       "sha256": package_module.archive_digest(pkg.archive)}],
        })
        target = (prepared.get("files") or [{}])[0]
        upload(target["url"], target.get("fields") or {}, filename, pkg.archive)
        completed = client.call("complete_source_upload", {"upload_id": prepared["upload_id"]})

        step("starting scan", collected=_collected(completed))
        started = client.call("scan_agent", {"agent_id": agent_id})
    except ScanError as exc:
        step("failed", error=str(exc))
        raise
    except Exception as exc:  # noqa: BLE001 - every failure is reported on the row
        step("failed", error=str(exc))
        raise ScanError(str(exc)) from None

    if started.get("status") == "already_complete":
        operation_id = None
    else:
        operation_id = (started.get("operation") or {}).get("operation_id")
    job = step("scanning", operation_id=operation_id)

    context = contextvars.copy_context()
    thread = threading.Thread(
        target=context.run,
        args=(_follow, profile, agent_id, operation_id, client, jobs, generate_probes, step),
        name=f"vail-scan-{profile}",
        daemon=True,
    )
    thread.start()
    return job


def _follow(profile, agent_id, operation_id, client, jobs, generate_probes, step) -> None:
    try:
        if operation_id and not _wait(client, operation_id, step, "scanning"):
            return
        if not generate_probes:
            step("done", operation_id=None)
            return
        started = client.call("generate_probes", {"agent_id": agent_id})
        probe_op = None if started.get("status") == "already_complete" else (started.get("operation") or {}).get("operation_id")
        step("generating probes", operation_id=probe_op)
        if probe_op and not _wait(client, probe_op, step, "generating probes"):
            return
        step("done", operation_id=None)
    except Exception as exc:  # noqa: BLE001 - background thread: record, never raise
        step("failed", error=str(exc))


def _wait(client, operation_id, step, phase) -> bool:
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    while time.monotonic() < deadline:
        status = client.call("get_operation_status", {"operation_id": operation_id})
        state = status.get("status")
        if state == "succeeded":
            return True
        if state == "failed":
            error = status.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else str(error)
            step("failed", error=f"{phase} failed: {message or 'no detail'}")
            return False
        progress = status.get("progress") or status.get("message")
        step(phase, operation_id=operation_id, progress=progress if isinstance(progress, str) else None)
        time.sleep(POLL_SECONDS)
    step("failed", error=f"{phase} is taking longer than {MAX_WAIT_SECONDS // 60} minutes; check VAIL later.")
    return False


def _collected(completed: dict) -> dict:
    return {
        "accepted": completed.get("file_count", len(completed.get("accepted_files") or [])),
        "skipped": completed.get("skipped_count", len(completed.get("skipped_files") or [])),
        "truncated": bool(completed.get("truncated")),
    }


class ScanError(Exception):
    pass
