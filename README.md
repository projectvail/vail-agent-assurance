# VAIL Agent Assurance for coding agents

Use the [VAIL Agent Assurance Engine](https://agents.projectvail.com) from your coding agent: upload an AI agent's source, scan it for vulnerability and control behaviors, generate probes that test them, and retrieve the results, without leaving your editor.

This repository is a Claude Code plugin marketplace containing one plugin, `vail-agent-assurance`. It bundles:

- a connection to VAIL's hosted MCP server at `https://agents.projectvail.com/mcp`, and
- the `agent-assurance` skill, which explains the workflow to the coding agent.

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

## Codex

The MCP server and skill are not specific to Claude Code. In Codex, add the server to `~/.codex/config.toml`, with the token read from an environment variable:

```toml
[mcp_servers.vail]
url = "https://agents.projectvail.com/mcp"
bearer_token_env_var = "VAIL_TOKEN"
```

To give Codex the workflow instructions too, copy `plugins/vail-agent-assurance/skills/agent-assurance/` into your Codex skills directory.

> Codex support has not been tested yet. Check the [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) for the current configuration format.

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

Connecting a live agent, and running, reviewing, approving, or scheduling probes, happen in the VAIL web app.

## Repository layout

```text
.claude-plugin/marketplace.json                  the marketplace
plugins/vail-agent-assurance/
  .claude-plugin/plugin.json                     plugin manifest and MCP connection
  skills/agent-assurance/SKILL.md                the workflow skill
```

Validate changes with `claude plugin validate .` and `claude plugin validate ./plugins/vail-agent-assurance`. Bump `version` in `plugin.json` for every release.

The plugin always connects to production. To try skill changes against a local VAIL server, don't install the plugin. Instead, connect the local server with `claude mcp add` (as in [Without the plugin](#without-the-plugin), using `http://127.0.0.1:8099/mcp`), and copy `skills/agent-assurance/` to `~/.claude/skills/`. The server's README, under "Coding agents against a local server", explains how to run it.
