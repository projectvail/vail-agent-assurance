"""The profile packager must never send credentials to VAIL. Run: python -m pytest tests/"""

import importlib.util
import io
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "panel_package", HERE.parent / "plugins/vail-assurance-panel/dashboard/package.py")
package = importlib.util.module_from_spec(_spec)
sys.modules["panel_package"] = package
_spec.loader.exec_module(package)

PAT = "vail_pat_" + "A1b2C3d4E5f6G7h8I9j0"
OPENAI = "sk-proj-" + "abcdefghijklmnopqrstuvwxyz0123"
AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
LITERAL_KEY = "literal-not-a-pattern-but-secret-123"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_profile(home: Path) -> None:
    write(home / "SOUL.md", f"# Bot\nYou help with signups. Old token: {PAT}\n")
    write(home / "config.yaml", "\n".join([
        "model:",
        "  default: deepseek/deepseek-v4.1-flash",
        "  api_key: ''",
        "providers:",
        "  gw:",
        "    key_env: GATEWAY_KEY",
        f"    api_key: {LITERAL_KEY}",
        "mcp_servers:",
        "  vail:",
        "    headers:",
        "      Authorization: Bearer ${VAIL_TOKEN}",
        "telegram:",
        "  bot_token: \"123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawQ\"",
        "",
    ]))
    write(home / ".env", f"OPENAI_API_KEY={OPENAI}\nVAIL_TOKEN={PAT}\n")
    write(home / "auth.json", '{"token": "x"}')
    write(home / "sessions/abc.json", '{"messages": ["private"]}')
    write(home / "memories/MEMORY.md", "the user's private notes")
    write(home / "logs/agent.log", f"{AWS}\n")
    (home / "state.db").write_bytes(b"SQLite format 3\x00")
    # skills: one bundled, one the user's own
    write(home / "skills/.bundled_manifest", "arxiv:1f2a\n")
    write(home / "skills/research/arxiv/SKILL.md", "---\nname: arxiv\n---\nbundled\n")
    write(home / "skills/ops/vet-signup/SKILL.md", f"---\nname: vet-signup\n---\nUse key {AWS} never.\n")
    write(home / "skills/ops/vet-signup/references/notes.md", "notes")
    write(home / "skills/ops/vet-signup/.env", "SECRET=1")
    # plugins: the user's, ours, and junk
    write(home / "plugins/admin/plugin.yaml", "name: admin\n")
    write(home / "plugins/admin/__init__.py", f"TOKEN = '{OPENAI}'\n")
    write(home / "plugins/admin/credentials.json", '{"k": "v"}')
    (home / "plugins/admin/__pycache__").mkdir(parents=True)
    (home / "plugins/admin/__pycache__/x.pyc").write_bytes(b"\x00\x01")
    write(home / "plugins/vail-assurance-panel/plugin.yaml", "name: vail-assurance-panel\n")


def archive_members(archive: bytes) -> dict[str, str]:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        return {m.name: tar.extractfile(m).read().decode() for m in tar.getmembers()}


def test_only_allowlisted_files_are_packaged(tmp_path):
    make_profile(tmp_path)
    pkg = package.build_package("bot", tmp_path)
    paths = {f.path for f in pkg.files}
    assert paths == {
        "SOUL.md",
        "config.yaml",
        "plugins/admin/plugin.yaml",
        "plugins/admin/__init__.py",
        "skills/ops/vet-signup/SKILL.md",
        "skills/ops/vet-signup/references/notes.md",
    }
    assert set(archive_members(pkg.archive)) == paths


def test_no_secret_reaches_the_archive(tmp_path):
    make_profile(tmp_path)
    pkg = package.build_package("bot", tmp_path)
    blob = "\n".join(archive_members(pkg.archive).values())
    for secret in (PAT, OPENAI, AWS, LITERAL_KEY, "AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawQ", "private notes"):
        assert secret not in blob
    assert pkg.redactions >= 5


def test_config_keeps_structure_and_references(tmp_path):
    make_profile(tmp_path)
    pkg = package.build_package("bot", tmp_path)
    config = archive_members(pkg.archive)["config.yaml"]
    assert "default: deepseek/deepseek-v4.1-flash" in config
    assert "api_key: ''" in config                      # empty stays empty
    assert "key_env: GATEWAY_KEY" in config             # a variable's name is not a secret
    assert "Bearer ${VAIL_TOKEN}" in config             # references stay
    assert "api_key: '<redacted>'" in config


def test_skips_are_reported_with_reasons(tmp_path):
    make_profile(tmp_path)
    reasons = {s["path"]: s["reason"] for s in package.build_package("bot", tmp_path).skipped}
    assert reasons["plugins/admin/credentials.json"] == "name suggests credentials"
    assert reasons["skills/ops/vet-signup/.env"] == "hidden file"


def test_redact_text_patterns():
    text, n = package.redact_text(f"a {PAT} b {OPENAI} c Bearer abcdefghijklmnopqrstuvwxyz012345")
    assert PAT not in text and OPENAI not in text and "abcdefghijklmnopqrstuvwxyz012345" not in text
    assert n == 3
    kept, n = package.redact_text("Authorization: Bearer ${VAIL_TOKEN}")
    assert n == 0 and kept == "Authorization: Bearer ${VAIL_TOKEN}"
