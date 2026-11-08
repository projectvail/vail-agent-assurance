#!/usr/bin/env python3
"""Install the VAIL trust and safety desk: four Hermes bots (profiles) that work as a team.

    python3 install.py                       # into ~/.hermes, models through OpenRouter
    python3 install.py --home /tmp/h --api http://127.0.0.1:8787/openrouter/v1 --key-env GATEWAY_KEY
    python3 install.py --force               # delete and recreate the four profiles

Each bot is created with `hermes profile create --no-skills`, then given its SOUL.md, its skills, its
stub tools (a plugin reading desk_data.json; nothing reaches the real VAIL Assurance Engine), its model,
and only the toolsets its job needs. profile.yaml gets a Bot Mode title, which also lets the bots
message each other with `message_agent` from their Bot Chat.

Standard library only. The API key is copied from the main profile's .env into each bot's .env, the
same thing Hermes Desktop's "Copy API keys from the main profile" does; it is never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOTS = ("martin", "ledger", "herald", "dispatch")
# Every built-in toolset a bot does not list in bot.json is disabled for it, on every surface.
BUILTIN_TOOLSETS = ("web", "browser", "terminal", "file", "code_execution", "vision", "video", "image_gen",
                    "video_gen", "x_search", "tts", "stt", "skills", "todo", "kanban", "memory", "context_engine",
                    "session_search", "connections", "clarify", "delegation", "cronjob", "yuanbao",
                    "computer_use", "a2a")


def run(hermes: list[str], home: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ, HERMES_HOME=str(home))
    result = subprocess.run([*hermes, *args], env=env, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"`hermes {' '.join(args)}` failed:\n{result.stdout}{result.stderr}")
    return result


def env_value(env_file: Path, name: str) -> str | None:
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return None


def set_env(env_file: Path, name: str, value: str) -> None:
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    lines = [line for line in lines if not line.startswith(f"{name}=")] + [f"{name}={value}"]
    fd = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def yaml_str(value: str) -> str:
    return json.dumps(value)  # a JSON string is a valid YAML scalar


def write_config(path: Path, bot: dict, api: str, key_env: str) -> None:
    disabled = [t for t in BUILTIN_TOOLSETS if t not in bot["toolsets"]]
    lines = [
        "# Written by examples/trust-safety-desk/install.py",
        "model:",
        f"  default: {yaml_str(bot['model'])}",
        "  provider: custom:desk-models",
        "providers:",
        "  desk-models:",
        f"    api: {yaml_str(api)}",
        f"    key_env: {key_env}",
        "    transport: chat_completions",
        "    catalog_provider: openrouter",
        f"    default_model: {yaml_str(bot['model'])}",
        "agent:",
        "  disabled_toolsets:",
        *[f"    - {name}" for name in disabled],
        "plugins:",
        "  enabled:",
        *[f"    - {name}" for name in bot["plugins"]],
        "  disabled: []",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def mark_bot(profile_yaml: Path, title: str) -> None:
    text = profile_yaml.read_text(encoding="utf-8") if profile_yaml.exists() else ""
    if "ui_meta:" in text:
        print(f"  ! {profile_yaml} already has ui_meta; left as is (set the title in Hermes Desktop)")
        return
    block = f"ui_meta:\n  hermes-bots:\n    title: {yaml_str(title)}\n"
    profile_yaml.write_text(text.rstrip("\n") + ("\n" if text.strip() else "") + block, encoding="utf-8")


def copy_tree(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def install(args: argparse.Namespace) -> None:
    hermes = [args.hermes]
    home = Path(args.home).expanduser().resolve()
    source_env = home / ".env"
    key = env_value(source_env, args.key_env) or os.environ.get(args.key_env)
    if not key:
        sys.exit(f"{args.key_env} is not set in {source_env} or the environment; the bots need it to reach their models.")

    existing = run(hermes, home, "profile", "list").stdout
    for name in BOTS:
        bot = json.loads((HERE / "bots" / name / "bot.json").read_text(encoding="utf-8"))
        profile_dir = home / "profiles" / name
        print(f"{bot['title']} ({name}) — {bot['model']}")
        if profile_dir.exists() or f" {name} " in f" {existing} ":
            if not args.force:
                print(f"  ! profile {name} exists; skipped (use --force to recreate it)")
                continue
            run(hermes, home, "profile", "delete", name, "--yes")
        run(hermes, home, "profile", "create", name, "--no-skills", "--no-alias", "--description", bot["description"])

        src = HERE / "bots" / name
        shutil.copy2(src / "SOUL.md", profile_dir / "SOUL.md")
        copy_tree(src / "skills", profile_dir / "skills")
        for plugin in bot["plugins"]:
            target = profile_dir / "plugins" / plugin
            copy_tree(src / "plugins" / plugin, target)
            shutil.copy2(HERE / "lib" / "desk_core.py", target / "desk_core.py")
            shutil.copy2(HERE / "data" / "desk_data.json", target / "desk_data.json")
        write_config(profile_dir / "config.yaml", bot, args.api, args.key_env)
        set_env(profile_dir / ".env", args.key_env, key)
        mark_bot(profile_dir / "profile.yaml", bot["title"])
        print(f"  ✓ {profile_dir}")
    print("\nDone. Talk to a bot with `hermes -p <name> chat`, or open Hermes Desktop's Bots tab.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--home", default=os.environ.get("HERMES_HOME", "~/.hermes"),
                        help="Hermes root to install into (default: $HERMES_HOME or ~/.hermes)")
    parser.add_argument("--hermes", default="hermes", help="The hermes executable (default: hermes on PATH)")
    parser.add_argument("--api", default="https://openrouter.ai/api/v1",
                        help="OpenAI-compatible endpoint serving the bots' models (default: OpenRouter)")
    parser.add_argument("--key-env", default="OPENROUTER_API_KEY",
                        help="Variable in the main profile's .env holding that endpoint's key")
    parser.add_argument("--force", action="store_true", help="Delete and recreate profiles that already exist")
    install(parser.parse_args())


if __name__ == "__main__":
    main()
