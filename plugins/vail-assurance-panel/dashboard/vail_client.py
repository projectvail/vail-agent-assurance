"""Minimal MCP Streamable HTTP client for the VAIL Assurance Engine, standard library only.

Hermes ships different `mcp` SDK versions over time (the client entry point was renamed in 2.0), so the
panel's backend talks JSON-RPC itself: initialize once per client, then tools/call. Responses may come
back as application/json or as a text/event-stream carrying the JSON-RPC message.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from typing import Any

PROTOCOL_VERSION = "2025-06-18"


class VailError(Exception):
    """A VAIL call failed: transport, HTTP status, JSON-RPC error, or a tool result marked isError."""

    def __init__(self, message: str, *, status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


class VailClient:
    def __init__(self, url: str, token: str, *, timeout: float = 60.0, client_name: str = "vail-assurance-panel",
                 client_version: str = "0.1.0"):
        if not token:
            raise VailError("No VAIL token is set", code="no_token")
        self.url = url
        self.token = token
        self.timeout = timeout
        self._client_info = {"name": client_name, "version": client_version}
        self._session_id: str | None = None
        self._next_id = 0

    # -- transport -------------------------------------------------------------------------------------

    def _post(self, payload: dict, *, expect_reply: bool = True) -> dict | None:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    self._session_id = session_id
                content_type = response.headers.get("Content-Type", "")
                body = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise VailError("VAIL rejected the token (HTTP %d)" % exc.code, status=exc.code, code="auth") from None
            raise VailError("VAIL answered HTTP %d" % exc.code, status=exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise VailError(f"Could not reach VAIL at {self.url}: {getattr(exc, 'reason', exc)}", code="unreachable") from None
        if not expect_reply:
            return None
        message = _parse_body(body, content_type, payload.get("id"))
        if message is None:
            raise VailError("VAIL sent no JSON-RPC reply")
        if "error" in message:
            error = message["error"] or {}
            raise VailError(str(error.get("message") or error), code=str(error.get("code")))
        return message.get("result") or {}

    def _request(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            payload["params"] = params
        return self._post(payload) or {}

    def _ensure_session(self) -> None:
        if self._session_id is not None or self._next_id:
            return
        self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": self._client_info,
        })
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect_reply=False)

    # -- tools -----------------------------------------------------------------------------------------

    def call(self, tool: str, arguments: dict | None = None) -> Any:
        """Call a VAIL tool and return its result as JSON (structured content, else the parsed text)."""
        self._ensure_session()
        result = self._request("tools/call", {"name": tool, "arguments": arguments or {}})
        data = result.get("structuredContent")
        if data is None:
            text = "".join(part.get("text", "") for part in result.get("content", []) if part.get("type") == "text")
            try:
                data = json.loads(text) if text else {}
            except ValueError:
                data = {"text": text}
        if result.get("isError"):
            error = data.get("error", data) if isinstance(data, dict) else {"message": data}
            if not isinstance(error, dict):
                error = {"message": error}
            message = error.get("message") or error.get("text") or "failed"
            raise VailError(f"{tool}: {message}", code=error.get("code"))
        return data

    def call_results(self, tool: str, arguments: dict | None = None) -> dict:
        """Call get_behaviors / get_probes and return the result, inline or fetched from its download."""
        data = self.call(tool, arguments)
        if data.get("delivery") != "download":
            return data.get("result") or {}
        download = data.get("download") or {}
        url = download.get("url")
        if not url:
            raise VailError(f"{tool}: download has no URL")
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                body = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise VailError(f"{tool}: could not fetch results: {getattr(exc, 'reason', exc)}") from None
        expected = download.get("sha256")
        if expected and hashlib.sha256(body).hexdigest() != expected:
            raise VailError(f"{tool}: downloaded results failed the sha256 check")
        return json.loads(body)


def _parse_body(body: str, content_type: str, request_id: Any) -> dict | None:
    if "text/event-stream" in content_type:
        reply = None
        for block in body.replace("\r\n", "\n").split("\n\n"):
            data = "\n".join(line[5:].lstrip() for line in block.split("\n") if line.startswith("data:"))
            if not data:
                continue
            try:
                message = json.loads(data)
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("id") == request_id and ("result" in message or "error" in message):
                reply = message
        return reply
    if not body.strip():
        return None
    message = json.loads(body)
    return message if isinstance(message, dict) else None
