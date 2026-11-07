"""Package a Hermes profile as agent source for VAIL, without its secrets.

An allowlist, not a denylist: only what defines the profile as an agent is considered (SOUL.md, AGENTS.md,
config.yaml, the profile's own skills, its plugins), and only text files. Credentials, sessions, memories,
logs, databases and hidden files are never read. Every included file is also searched for token-shaped
strings, which are replaced with <redacted>, and config.yaml values under secret-looking keys are redacted.

Pure standard library and no Hermes imports, so it can be tested on its own.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import tarfile
import time
from dataclasses import dataclass, field
from pathlib import Path

MAX_FILES = 200            # VAIL accepts at most 200 files per upload; we send one archive but keep its spirit
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024

ROOT_FILES = ("SOUL.md", "AGENTS.md", "config.yaml")
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".py", ".js", ".mjs", ".ts", ".sh", ".j2",
                 ".jinja", ".html", ".css", ".csv", ".ini", ".cfg"}
# Our own plugins describe VAIL, not the agent; leave them out of the agent's source.
SKIP_PLUGINS = {"vail-agent-assurance", "vail-assurance-panel"}
SKIP_DIRS = {"__pycache__", "node_modules", ".venv", "venv", ".git", "dist", "build"}
_SECRET_NAME = re.compile(r"(^|[._-])(env|secrets?|credentials?|passwords?|tokens?|auth)([._-]|$)|\.(pem|key|p12|pfx|keystore)$",
                          re.IGNORECASE)

# Token shapes. Each match is replaced with <redacted>.
SECRET_PATTERNS = [
    re.compile(r"vail_pat_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"vgw_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"sk-(?:ant-|proj-|or-)?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),  # Telegram bot token
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"(?i)\bbearer\s+(?!\$\{)[A-Za-z0-9._~+/\-]{20,}=*"),
]
# A YAML `key: value` line whose key looks secret and whose value is a literal (not empty, not ${VAR}).
_YAML_SECRET_LINE = re.compile(
    r"^(?P<lead>\s*-?\s*['\"]?(?P<key>[A-Za-z0-9_.\-]*?(?:api[_-]?key|apikey|secret|token|password|passwd|"
    r"private[_-]?key|authorization|access[_-]?key|client[_-]?secret)[A-Za-z0-9_.\-]*)['\"]?\s*:\s*)"
    r"(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
_YAML_KEEP_VALUE = re.compile(r"""^(?:''|""|~|null|\{\}|\[\]|['"]?\$\{[^}]+\}['"]?|['"]?<redacted>['"]?)$""", re.IGNORECASE)
_YAML_NAME_ONLY_KEYS = re.compile(r"(?i)(?:_env|env_var|_name|_header|_path|_file|_url|key_cmd)$")


@dataclass
class PackagedFile:
    path: str
    size: int
    redactions: int = 0


@dataclass
class Package:
    profile: str
    files: list[PackagedFile] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    contents: dict[str, bytes] = field(default_factory=dict, repr=False)
    archive: bytes = b""

    @property
    def redactions(self) -> int:
        return sum(item.redactions for item in self.files)

    @property
    def total_bytes(self) -> int:
        return sum(item.size for item in self.files)

    def summary(self) -> dict:
        return {
            "profile": self.profile,
            "files": [item.__dict__ for item in self.files],
            "skipped": self.skipped,
            "file_count": len(self.files),
            "total_bytes": self.total_bytes,
            "redactions": self.redactions,
            "archive_bytes": len(self.archive),
        }


def redact_text(text: str, *, yaml_config: bool = False) -> tuple[str, int]:
    """Replace token-shaped strings (and, for config.yaml, literal values under secret keys)."""
    count = 0
    for pattern in SECRET_PATTERNS:
        text, n = pattern.subn("<redacted>", text)
        count += n
    if yaml_config:
        lines = []
        for line in text.split("\n"):
            match = _YAML_SECRET_LINE.match(line)
            if match and not _YAML_NAME_ONLY_KEYS.search(match.group("key")) and not line.lstrip().startswith("#"):
                value = match.group("value")
                comment = ""
                if " #" in value:
                    value, comment = value.split(" #", 1)
                    value, comment = value.rstrip(), " #" + comment
                if value and not _YAML_KEEP_VALUE.match(value) and value not in ("|", ">") and not _only_references(value):
                    line = f"{match.group('lead')}'<redacted>'{comment}"
                    count += 1
            lines.append(line)
        text = "\n".join(lines)
    return text, count


def _only_references(value: str) -> bool:
    """`${VAR}` references with at most an auth scheme word around them (`Bearer ${VAIL_TOKEN}`)."""
    if "${" not in value:
        return False
    rest = re.sub(r"\$\{[^}]+\}", "", value).strip().strip("'\"").strip()
    return rest == "" or rest.lower() in ("bearer", "basic", "token")


def bundled_skill_names(skills_dir: Path) -> set[str]:
    """Skill names Hermes copied in from its bundled set (``skills/.bundled_manifest``: name:hash lines)."""
    try:
        lines = (skills_dir / ".bundled_manifest").read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {line.split(":", 1)[0].strip() for line in lines if line.strip() and not line.startswith("#")}


def _candidates(home: Path) -> list[tuple[str, Path, str]]:
    """(archive path, file, kind) for everything the allowlist admits, in upload priority order."""
    found: list[tuple[str, Path, str]] = []
    for name in ROOT_FILES:
        path = home / name
        if path.is_file() and not path.is_symlink():
            found.append((name, path, "config" if name == "config.yaml" else "root"))

    plugins_dir = home / "plugins"
    if plugins_dir.is_dir():
        for plugin in sorted(plugins_dir.iterdir()):
            if plugin.name in SKIP_PLUGINS or plugin.name.startswith(".") or not plugin.is_dir() or plugin.is_symlink():
                continue
            found.extend(_walk(plugin, f"plugins/{plugin.name}", "plugin"))

    skills_dir = home / "skills"
    if skills_dir.is_dir():
        bundled = bundled_skill_names(skills_dir)
        for current, dirs, files in os.walk(skills_dir):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
            if "SKILL.md" in files:
                skill_dir = Path(current)
                if skill_dir.name in bundled:
                    dirs[:] = []
                    continue
                rel = skill_dir.relative_to(home).as_posix()
                found.extend(_walk(skill_dir, rel, "skill"))
                dirs[:] = []
    return found


def _walk(base: Path, prefix: str, kind: str) -> list[tuple[str, Path, str]]:
    out = []
    for current, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for filename in sorted(files):
            path = Path(current) / filename
            rel = f"{prefix}/{path.relative_to(base).as_posix()}"
            out.append((rel, path, kind))
    return out


def build_package(profile: str, home: Path) -> Package:
    package = Package(profile=profile)
    total = 0
    for rel, path, kind in _candidates(home):
        name = path.name
        reason = None
        if name.startswith("."):
            reason = "hidden file"
        elif _SECRET_NAME.search(name) and name not in ("SKILL.md",):
            reason = "name suggests credentials"
        elif path.is_symlink():
            reason = "symlink"
        elif path.suffix.lower() not in TEXT_SUFFIXES:
            reason = "not a text source file"
        if reason:
            package.skipped.append({"path": rel, "reason": reason})
            continue
        try:
            size = path.stat().st_size
        except OSError:
            package.skipped.append({"path": rel, "reason": "unreadable"})
            continue
        if size > MAX_FILE_BYTES:
            package.skipped.append({"path": rel, "reason": f"larger than {MAX_FILE_BYTES // 1024} KB"})
            continue
        if len(package.files) >= MAX_FILES or total + size > MAX_TOTAL_BYTES:
            package.skipped.append({"path": rel, "reason": "upload limit reached"})
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            package.skipped.append({"path": rel, "reason": "not UTF-8 text"})
            continue
        text, redactions = redact_text(text, yaml_config=(kind == "config"))
        data = text.encode("utf-8")
        package.files.append(PackagedFile(path=rel, size=len(data), redactions=redactions))
        package.contents[rel] = data
        total += len(data)
    package.archive = _archive(package.contents)
    return package


def _archive(contents: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    now = time.time()
    with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
        for rel in sorted(contents):
            data = contents[rel]
            info = tarfile.TarInfo(name=rel)
            info.size = len(data)
            info.mtime = now
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def archive_digest(archive: bytes) -> str:
    return hashlib.sha256(archive).hexdigest()
