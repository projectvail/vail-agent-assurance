# Example: the VAIL trust and safety desk

A team of four Hermes bots that reviews organizations signing up for the VAIL Assurance Engine. Each bot is its own Hermes profile with one specialty, its own model, and only the tools that specialty needs. Dispatch coordinates and hands work to the others with Bot Mode's `message_agent`.

It is the demo team for the two VAIL plugins: scan each bot with the **VAIL Assurance Panel**, then harden it with the `vail-agent-assurance` plugin's `agent-improvement` skill.

| Bot | Specialty | Tools | Model |
|---|---|---|---|
| **Dispatch** | Coordinates: hands vetting to Martin, usage to Ledger, emails to Herald, and brings the answers to you for a decision | `message_agent` (Bot Mode) | `moonshotai/kimi-k3` |
| **Martin** | Vetting: is a pending organization a real company or spam? | `list_pending_orgs`, `get_org`, web search | `deepseek/deepseek-v4.1-flash` |
| **Ledger** | Usage and abuse: thresholds crossed, usage split across organizations | `get_usage`, `get_org` | `google/gemini-3.8-flash` |
| **Herald** | Applicant emails: tells each organization the VAIL team's decision | `get_org`, `draft_email`, `send_email`, `list_outbox` | `anthropic/claude-haiku-5.5` |

Every bot also has Hermes's `skills`, `todo` and `clarify` toolsets; everything else (terminal, files, browser, code execution, memory, delegation, cron, computer use) is disabled for it.

## The tools are stubs

All desk tools answer from `data/desk_data.json`: eight fictional organizations (four pending, one with a disposable email, two that are the same person splitting usage), their users, and a day of engine activity, with times relative to now. Nothing reaches the real engine, and `send_email` only appends to an outbox file in the bot's plugin data directory. That makes the bots safe to probe and their answers repeatable.

## Install

```sh
python3 install.py                     # into ~/.hermes, models through OpenRouter (OPENROUTER_API_KEY)
python3 install.py --home /path/to/hermes-home --api https://gateway.example/openrouter/v1 --key-env GATEWAY_KEY
python3 install.py --force             # delete and recreate the four profiles
```

The installer runs `hermes profile create <bot> --no-skills` for each bot, then writes its `SOUL.md`, skills, plugin (with `desk_core.py` and `desk_data.json`), `config.yaml` (model, provider, disabled toolsets, enabled plugin), a Bot Mode title in `profile.yaml`, and copies the API key named by `--key-env` from the main profile's `.env` into the bot's `.env`.

## Try it

```sh
hermes -p martin chat -q "Which organizations are waiting for approval?"
hermes -p ledger chat -q "Who crossed an abuse threshold in the last 24 hours?"
hermes -p dispatch chat -c "Bot Chat" --create-if-missing -q "Run the weekly onboarding review."
```

Bots message each other only from their **Bot Chat** session, as in the last line (in Hermes Desktop, open the Bots tab and click a bot). A reply comes back to the sender's Bot Chat as a notification.

## Layout

```text
install.py              creates the four profiles
data/desk_data.json     the stub organizations, users and activity
lib/desk_core.py        the stub tools; copied into each bot's plugin
bots/<bot>/bot.json     title, description (shown to teammates), model, toolsets, plugins
bots/<bot>/SOUL.md      the bot's role and rules
bots/<bot>/skills/      its workflows
bots/<bot>/plugins/     its tools (a native Hermes plugin)
```
