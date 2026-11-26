# VAIL Agent Assurance for coding agents

Use the [VAIL Agent Assurance Engine](https://agents.projectvail.com) from your coding agent: upload or collect an AI agent's source, scan it for vulnerability and control behaviors, classify risks against five security taxonomies and `model_based` attribution, generate deterministic probes, score every vulnerability on **Impact**, **Trigger**, and **Fidelity risks**, run steering experiments with draft PR promotion, or test and harden the agent locally—without leaving your editor.

This repository packages `vail-agent-assurance` as a plugin marketplace for **Claude** and **Codex**, and as a portable [Agent Plugins v1](https://agent-plugins.org) package for **Hermes Agent**. The hosted MCP server at `https://agents.projectvail.com/mcp` authenticates with **OAuth 2.1** (and also accepts personal access tokens for headless or CI scripts), so it works out of the box across every major coding harness.

It bundles:

- a connection to VAIL's hosted MCP server at `https://agents.projectvail.com/mcp` (OAuth 2.1),
- the `agent-assurance` skill, which guides your coding agent through source collection, scanning, security framework classification, probe generation, Impact/Trigger/Fidelity risk scoring, steering experiments, and draft PR promotion, and
- the `agent-improvement` skill, which works through an agent's behavior risks with you: testing them against a local copy of the agent, graded the exact way VAIL grades them (including nested consistency checks for contradictory rules), and fixing what the tests show.

There is no local MCP server or VAIL CLI to install, and you don't need AWS credentials. Your coding agent uploads files with its ordinary shell tools. Only the `agent-improvement` skill installs anything: VAIL's Python grading wheel (`vail-grading`), into a virtual environment of its own. [What the plugin sends and downloads](plugins/vail-agent-assurance/README.md#what-the-plugin-sends-and-downloads) lists it all.

## Supported platforms

### Coding harnesses (where you use VAIL)

| Coding platform | Plugin / skills bundle | MCP connection | Authentication |
|---|---|---|---|
| **Claude Code** (CLI, VS Code, Desktop) | Yes (`vail-agent-assurance` plugin) | `https://agents.projectvail.com/mcp` | OAuth 2.1 in browser (`/mcp` or `claude mcp login`) |
| **Claude on the web & Cowork** (`claude.ai`) | Yes (Anthropic Directory plugin + connector) | `https://agents.projectvail.com/mcp` | OAuth 2.1 in browser |
| **OpenAI Codex** (CLI, IDE extension, ChatGPT desktop) | Yes (`vail-agent-assurance` plugin) | `https://agents.projectvail.com/mcp` | OAuth 2.1 in browser (`/mcp` or `codex mcp login`) |
| **ChatGPT** (Web & Work) | Yes (OpenAI Plugins Directory) | `https://agents.projectvail.com/mcp` | OAuth 2.1 in browser |
| **OpenCode** | Copy `skills/` (optional) | `opencode mcp add vail --url https://agents.projectvail.com/mcp` | OAuth 2.1 in browser (default; `/mcps` or `opencode mcp auth vail`) |
| **Cursor** | Copy `skills/` to `~/.cursor/skills/` (optional) | `~/.cursor/mcp.json` (`"url": "https://agents.projectvail.com/mcp"`) | OAuth 2.1 in browser (Connect in Cursor MCP settings) |
| **Hermes Agent & Hermes Desktop** | Yes (`vail-agent-assurance` + `vail-assurance-panel`) | `https://agents.projectvail.com/mcp` | OAuth 2.1 (`hermes mcp login vail`); PAT for the Desktop fleet panel |

### Target AI agent frameworks (what VAIL scans and grades)

- **Source scanning, classification, probe generation, and scoring (all 7 platforms):** `langgraph` (LangGraph), `hermes` (Hermes Agent), `openclaw` (OpenClaw), `pi` (Pi), `agentforce` (Salesforce Agentforce), `servicenow` (ServiceNow), and `http` (any custom HTTP agent).
- **Live probing & steering experiments:** **LangGraph**, **Hermes**, **OpenClaw**, and **custom HTTP** (`http`). For LangGraph, Hermes, and OpenClaw agents inside a private network that cannot be exposed to the internet, use the signed outbound-only VAIL agent connector container ([setup guide](https://agents.projectvail.com/docs/guides/connector.md)).
- **Local probe execution & deterministic grading (`vail-grading` / `agent-improvement` skill):** **LangGraph**, **Hermes**, and **OpenClaw**.

## Before you start

You need a VAIL organization. Sign up at <https://agents.projectvail.com> (see [plans and pricing](https://agents.projectvail.com/pricing), or [pricing.md](https://agents.projectvail.com/pricing.md) for agents; probe run history is retained for 90 days on every plan). When you connect from any coding agent below, your browser opens VAIL to confirm which account and organization to authorize. You can review or revoke connected apps at any time under **Access tokens** in the VAIL web app.

*(For headless environments, SSH boxes without port forwarding, CI pipelines, or the Hermes Desktop panel, you can also create a personal access token under **Access tokens** at <https://agents.projectvail.com/settings/tokens>.)*

## Install in Claude Code (and Claude / Cowork)

```text
/plugin marketplace add projectvail/vail-agent-assurance
/plugin install vail-agent-assurance@vail-agent-assurance
```

Then run `/mcp`, select `vail`, and complete the OAuth sign-in in your browser (or run `claude mcp login plugin:vail-agent-assurance:vail` in your terminal).

Ask Claude Code naturally—you don't need to mention VAIL by name to trigger the skills, for example: *"Find out where the agent in ./support-bot breaks its own instructions, and check whether it is ready to ship."*

### Without the plugin

```sh
claude mcp add --scope user --transport http vail https://agents.projectvail.com/mcp
claude mcp login vail
```

Clients that support Skills over MCP (`io.modelcontextprotocol/skills`) and MCP Tasks (`io.modelcontextprotocol/tasks`) also discover VAIL's skills and run scans, classifications, probe generations, and steering experiments as background tasks directly through `https://agents.projectvail.com/mcp`.

## Install in Codex (and ChatGPT)

```sh
codex plugin marketplace add projectvail/vail-agent-assurance
```

Restart Codex, run `/plugins`, install `vail-agent-assurance`, and authenticate `vail` via `/mcp` (or select **Authenticate** next to `vail` under **Settings → MCP servers** in the ChatGPT desktop app / IDE extension).

### Without the plugin

```sh
codex mcp add vail --url https://agents.projectvail.com/mcp
codex mcp login vail
```

Optionally copy `plugins/vail-agent-assurance/skills/agent-assurance/` and `plugins/vail-agent-assurance/skills/agent-improvement/` into `~/.agents/skills/`.

## Install in OpenCode

OpenCode uses OAuth by default for remote Streamable HTTP MCP servers:

```sh
opencode mcp add vail --url https://agents.projectvail.com/mcp
opencode mcp auth vail
```

(Or run `/mcps` inside OpenCode, select `vail`, and complete sign-in in your browser.) Optionally copy `plugins/vail-agent-assurance/skills/agent-assurance/` and `plugins/vail-agent-assurance/skills/agent-improvement/` to `~/.config/opencode/skills/` or `.agents/skills/`.

## Install in Cursor

Add VAIL to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "vail": {
      "url": "https://agents.projectvail.com/mcp"
    }
  }
}
```

Open **Cursor Settings → MCP**, click **Connect** next to `vail`, and approve access in your browser. Optionally copy the two skill directories into `~/.cursor/skills/`.

## Install in Hermes

The plugin directory is a portable Agent Plugins v1 package (`plugin.json`, `mcp.json`, and `skills/`):

```sh
hermes plugins install projectvail/vail-agent-assurance/plugins/vail-agent-assurance --enable
hermes mcp login vail
```

Once the plugin is in the Hermes plugin catalog, `hermes plugins install vail-agent-assurance` does the same. In Hermes Desktop, you can also click **Authenticate** on the `vail` card under **Capabilities → Connectors**. *(On older Hermes releases prior to portable-plugin OAuth support, connect the server directly with `hermes mcp add vail --url https://agents.projectvail.com/mcp --auth oauth` and run `hermes mcp login vail`.)*

The tools appear as `mcp__vail__<tool>`, and the skills as `vail-agent-assurance:agent-assurance` and `vail-agent-assurance:agent-improvement`.

What the plugin does on your machine: it connects to `https://agents.projectvail.com/mcp` using your OAuth credentials. When you ask it to scan an agent, Hermes uploads that agent's source files to VAIL. It runs no background process and stores nothing besides the OAuth token in Hermes's token store, unless you use the `agent-improvement` skill, which downloads and installs VAIL's grading package in a virtual environment of its own and writes local test results to `.vail/` in the agent's repository.

### The assurance panel for Hermes Desktop

A second Hermes plugin, [`vail-assurance-panel`](plugins/vail-assurance-panel/), adds an **Assurance** page to Hermes Desktop: every Hermes profile (each bot) with its VAIL results, a one-click **Scan with VAIL** that shows exactly which files would be uploaded before sending them, and whether a profile changed since its last scan. Because the panel's backend runs outside an interactive MCP session, configure it with a personal access token created under **Access tokens** at <https://agents.projectvail.com/settings/tokens>:

```sh
hermes plugins install projectvail/vail-agent-assurance/plugins/vail-assurance-panel --enable
```

Then enter your token in the plugin's settings form in Hermes Desktop (or store it in your profile's `.env`), and switch on **VAIL Assurance Panel** under **Capabilities → Plugins**. See its [README](plugins/vail-assurance-panel/README.md).

[`examples/trust-safety-desk`](examples/trust-safety-desk/) is a team of four Hermes bots to try both plugins on.

## What it can do (all 33 MCP tools)

### Identity, agents, source, scanning, and probes (14 tools)

| Tool | What it does |
|---|---|
| `get_identity` | Who the connection acts as, and what your organization may do. |
| `list_agents`, `create_agent` | Find or create the agent to work on. |
| `get_agent_status` | Report the agent's stage, collected source, result freshness, steering links, and `next_actions`. |
| `prepare_source_upload`, `complete_source_upload` | Upload an agent's source, as one `.tar.gz`/`.tgz`/`.tar` archive or a set of files. |
| `scan_agent` | Generate the agent's context, discover vulnerability and control behaviors, and automatically classify vulnerabilities against the five security taxonomies and `model_based` attribution. |
| `classify_behaviors` | Classify or re-classify vulnerability behaviors against Cisco AI Security & Safety v2.0.0, OWASP Agentic Top 10 2026, OWASP LLM Top 10 2026, MITRE ATLAS v2026.09, and NIST AI 100-2 E2025 (with `model_based` attribution; human overrides are preserved). |
| `generate_probes`, `set_generation_limits` | Write probes and option pools, then score every vulnerability behavior (including behaviors without probes; controls are not scored) on Impact, Trigger, and Fidelity-risk membership, and configure probe limits. |
| `get_operation_status` | Poll progress, substeps (`generate_context`, `discover_behaviors`, `generate_probes`, `score_behaviors`), warnings, and outcomes for scans, classifications, and probe generation. |
| `get_behaviors`, `get_probes` | Retrieve the complete current behavior artifact (with `scores`, `fidelity_risks` count, `scoring_guide`, and `classifications`; discovery `severity` is not returned) and probe artifact as JSON or verified downloads. |
| `get_grading_package` | Download `vail-grading`, the package VAIL grades probe replies with, to test probes against an agent running locally (LangGraph, Hermes, or OpenClaw). |

### Steering setup, endpoint connection, experiments, and Promote (19 tools)

| Tool | What it does |
|---|---|
| `get_steering_setup`, `validate_steering_contract` | Fetch steering setup materials and statically validate a `vail-steering.json` contract for the agent's platform. |
| `collect_github_source` | Collect a committed GitHub revision via your organization's VAIL GitHub App for Promote provenance. |
| `get_agent_connection`, `prepare_agent_connection` | Inspect an agent's connection state or prepare a ticketed direct endpoint verification without passing secrets in MCP arguments. |
| `list_experiments`, `create_experiment`, `get_experiment` | List experiments, create a draft from generated probes with a proposal budget, and inspect draft cases and progress. |
| `save_experiment_case`, `remove_experiment_case` | Review, edit, or remove draft experiment cases with completion checks and action authorization. |
| `set_experiment_profiles` | Configure manual candidate profiles and comparison repetition counts. |
| `run_experiment`, `get_experiment_job`, `pause_experiment` | Run baseline/steering/comparison jobs on VAIL workers, poll job progress, and pause safely. |
| `get_experiment_report`, `get_experiment_execution` | Read experiment scores, fresh-baseline comparisons, winners, and per-execution traces and profile receipts. |
| `get_promotion`, `preview_promotion`, `publish_promotion` | Check eligibility, preview the immutable GitHub diff and `plan_id`, and open a draft GitHub PR (never merges or deploys). |

Approving catalog probes for recurring scheduled monitoring and managing schedules happen in the VAIL web app, as do initial organization signup and GitHub App installation. Testing and fixing source code locally uses the `agent-improvement` skill; comparing runtime/request settings and opening a draft PR uses the [steering workflow](plugins/vail-agent-assurance/skills/agent-assurance/references/steering.md).

## Repository layout

```text
.claude-plugin/marketplace.json                  the marketplace (read by Claude Code and Codex)
plugins/vail-agent-assurance/
  .claude-plugin/plugin.json                     Claude Code & Anthropic Directory manifest (OAuth 2.1)
  .codex-plugin/plugin.json, .mcp.json           Codex compatibility manifest & MCP server entry
  plugin.json, mcp.json                          Portable Agent Plugins v1 manifest (OpenAI & Hermes, OAuth 2.1)
  assets/                                        Square light/dark plugin logos and composer icons
  skills/agent-assurance/SKILL.md                the workflow skill, shared by all harnesses
  skills/agent-assurance/references/steering.md  steering experiments and draft PR promotion guide
  skills/agent-improvement/                      testing and fixing an agent locally from its results
plugins/vail-assurance-panel/                    Hermes Desktop page and its backend (a native Hermes plugin)
examples/trust-safety-desk/                      four Hermes bots that work as a team, with stub tools
tests/                                           tests for the panel's profile packaging (python -m pytest tests/)
```

Validate changes with `claude plugin validate .` and `claude plugin validate ./plugins/vail-agent-assurance`. Validate the Hermes package with `hermes plugins validate ./plugins/vail-agent-assurance`. For every release, bump `version` in **all three** manifests (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and `plugin.json`) to the same value. CI checks this. Validate the panel with `hermes plugins validate ./plugins/vail-assurance-panel`.

The plugin always connects to production. To try skill changes against a local VAIL server (`http://127.0.0.1:8099/mcp`), connect the local server directly with OAuth instead of installing the plugin, and copy the skill directories:

| Harness | Connect `http://127.0.0.1:8099/mcp` | Copy the skill to |
|---|---|---|
| Claude Code | `claude mcp add --transport http vail-local http://127.0.0.1:8099/mcp && claude mcp login vail-local` | `~/.claude/skills/<skill>/` |
| Codex | `codex mcp add vail-local --url http://127.0.0.1:8099/mcp && codex mcp login vail-local` | `~/.agents/skills/<skill>/` |
| OpenCode | `opencode mcp add vail-local --url http://127.0.0.1:8099/mcp && opencode mcp auth vail-local` | `~/.config/opencode/skills/<skill>/` |
| Hermes | `hermes mcp add vail-local --url http://127.0.0.1:8099/mcp --auth oauth && hermes mcp login vail-local` | `~/.hermes/skills/<skill>/` |

```sh
cp -R plugins/vail-agent-assurance/skills/agent-assurance plugins/vail-agent-assurance/skills/agent-improvement ~/.claude/skills/
```

Keep each skill as a directory of its own name containing `SKILL.md`. None of these harnesses discovers a `SKILL.md` placed directly in the skills directory. The server's README, under "Coding agents against a local server", explains how to run it.
