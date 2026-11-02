# VAIL Agent Assurance for coding agents

Use the [VAIL Agent Assurance Engine](https://agents.projectvail.com) from your coding agent: upload an AI agent's source, scan it for vulnerability and control behaviors, generate probes that test them, and retrieve the results, without leaving your editor.

This repository is a plugin marketplace for Claude Code and Codex containing one plugin, `vail-agent-assurance`. It bundles:

- a connection to VAIL's hosted MCP server at `https://agents.projectvail.com/mcp`, and
- the `agent-assurance` skill, which explains the workflow to the coding agent, and
- the `agent-improvement` skill, which works through an agent's behavior risks with you: testing them against the agent running locally, graded as VAIL grades them, and fixing what the tests show.

Hermes doesn't install plugins from this marketplace, but it can use the same MCP server and skill. See [Hermes](#hermes).

Nothing runs on your machine: there is no local server or CLI to install, and you don't need AWS credentials. Your coding agent uploads files with its ordinary shell tools.

## Before you start

1. You need a VAIL organization. Sign up at <https://agents.projectvail.com>.
2. Create a personal access token: sign in, open **Access tokens**, choose a name and an expiry, and copy the token (`vail_pat_...`). It is shown only once.

A token acts as you: it can do what you can in your organization, and stops working if it is revoked, if it expires, or if you leave the organization. Use one token per device or tool.

## Install in Claude Code

```text
/plugin marketplace add projectvail/vail-agent-assurance
/plugin install vail-agent-assurance@vail-agent-assurance
```

Claude Code asks for your VAIL access token when the plugin is enabled, and keeps it in your system's secure credential store, not in a settings file. To change it later, run `/plugin` and configure `vail-agent-assurance`.

Then ask Claude Code, for example: *"Scan the agent in ./support-bot with VAIL and show me the behaviors it finds."*

### Without the plugin

You can connect the MCP server alone. Put the token in an environment variable rather than typing it into the command:

```sh
export VAIL_TOKEN=vail_pat_...
claude mcp add --scope user --transport http vail https://agents.projectvail.com/mcp \
  --header "Authorization: Bearer $VAIL_TOKEN"
```

The shell expands `$VAIL_TOKEN` before Claude Code sees it, so the token is saved in plain text in your Claude Code configuration. The plugin avoids that.

## Install in Codex

```sh
export VAIL_TOKEN=vail_pat_...      # in the shell profile Codex starts from
codex plugin marketplace add projectvail/vail-agent-assurance
```

Restart Codex, run `/plugins`, and install `vail-agent-assurance`. The plugin connects with `bearer_token_env_var = "VAIL_TOKEN"`, so the token is read from Codex's environment each time it starts and is never written to Codex's configuration. Codex has no secure prompt like Claude Code's, so the token is only as protected as the place that sets the variable. A secret manager (`export VAIL_TOKEN="$(security find-generic-password -s vail -w)"` on macOS) is better than writing the token into a dotfile.

Codex reads `.codex-plugin/plugin.json` ahead of `.claude-plugin/plugin.json`, so the two manifests can differ in how they authenticate.

### Without the plugin

Add the server to `~/.codex/config.toml`, and copy the skill directories to `~/.agents/skills/agent-assurance/` and `~/.agents/skills/agent-improvement/`:

```toml
[mcp_servers.vail]
url = "https://agents.projectvail.com/mcp"
bearer_token_env_var = "VAIL_TOKEN"
```

## Hermes

[Hermes Agent](https://hermes-agent.nousresearch.com) has its own plugin format, which can't bundle an MCP server, so set up the two parts separately:

```sh
hermes mcp add vail --url https://agents.projectvail.com/mcp --auth header
hermes skills install projectvail/vail-agent-assurance/plugins/vail-agent-assurance/skills/agent-assurance
hermes skills install projectvail/vail-agent-assurance/plugins/vail-agent-assurance/skills/agent-improvement
```

`hermes mcp add` asks for the token and saves it as `MCP_VAIL_API_KEY` in Hermes's own secrets file (kept apart from the shareable config, which gets only the reference `Authorization: Bearer ${MCP_VAIL_API_KEY}`). Use `hermes skills update` to pick up new versions of the skill.

## What it can do

| Tool | What it does |
|---|---|
| `get_identity` | Who the token acts as, and what your organization may do. |
| `list_agents`, `create_agent` | Find or create the agent to work on. |
| `prepare_source_upload`, `complete_source_upload` | Upload an agent's source, as one `.tar.gz`/`.tgz`/`.tar` archive or a set of files. |
| `scan_agent` | Generate the agent's context, then discover its behaviors. |
| `generate_probes`, `set_generation_limits` | Write probes for those behaviors. |
| `get_agent_status`, `get_operation_status` | Follow progress, failures, and what to do next. |
| `get_behaviors`, `get_probes` | Retrieve the complete current results as JSON. |
| `get_grading_package` | Download `vail-grading`, the package VAIL grades probe replies with, to test probes against an agent running locally (LangGraph, Hermes, or OpenClaw). |

Connecting a live agent, and running, reviewing, approving, or scheduling probes on it, happen in the VAIL web app. Testing probes locally, with the `agent-improvement` skill, needs only your coding agent and a local copy of the agent.

## Repository layout

```text
.claude-plugin/marketplace.json                  the marketplace (read by Claude Code and Codex)
plugins/vail-agent-assurance/
  .claude-plugin/plugin.json                     Claude Code manifest: token from userConfig
  .codex-plugin/plugin.json                      Codex manifest: token from $VAIL_TOKEN
  skills/agent-assurance/SKILL.md                the workflow skill, shared by all harnesses
  skills/agent-improvement/                      testing and fixing an agent locally from its results
```

Validate changes with `claude plugin validate .` and `claude plugin validate ./plugins/vail-agent-assurance`. For every release, bump `version` in **both** manifests to the same value. CI checks this.

The plugin always connects to production. To try skill changes against a local VAIL server, don't install the plugin. Instead, connect the local server directly and copy the skill directory:

| Harness | Connect `http://127.0.0.1:8099/mcp` | Copy the skill to |
|---|---|---|
| Claude Code | `claude mcp add` (as in [Without the plugin](#without-the-plugin)) | `~/.claude/skills/<skill>/` |
| Codex | a `[mcp_servers.vail]` entry in `~/.codex/config.toml` | `~/.agents/skills/<skill>/` |
| Hermes | `hermes mcp add vail --url http://127.0.0.1:8099/mcp --auth header` | `~/.hermes/skills/<skill>/` |

```sh
cp -R plugins/vail-agent-assurance/skills/agent-assurance plugins/vail-agent-assurance/skills/agent-improvement ~/.claude/skills/
```

Keep each skill as a directory of its own name containing `SKILL.md`. None of these harnesses discovers a `SKILL.md` placed directly in the skills directory. The server's README, under "Coding agents against a local server", explains how to run it.
