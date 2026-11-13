# VAIL Agent Assurance for coding agents

Use the [VAIL Agent Assurance Engine](https://agents.projectvail.com) from your coding agent. Collect an agent's source, scan for behavior risks, and generate probes that test them. Then run steering experiments and promote a winning profile as a draft PR, or test and fix the agent locally.

This repository packages `vail-agent-assurance` as a plugin marketplace for **Claude** and **Codex**, and as a portable [Agent Plugins v1](https://agent-plugins.org) package for **Hermes Agent**. The hosted MCP server at `https://agents.projectvail.com/mcp` authenticates with **OAuth 2.1** (and also accepts personal access tokens for headless or CI scripts), so it works out of the box across every major coding harness.

It bundles:

- a connection to VAIL's hosted MCP server at `https://agents.projectvail.com/mcp` (OAuth 2.1),
- the `agent-assurance` skill, which guides your coding agent through source collection, scans, probe generation, steering experiments, and Promote, and
- the `agent-improvement` skill, which works through an agent's behavior risks with you: testing them against a local copy of the agent, graded the exact way VAIL grades them, and fixing what the tests show.

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

- **Source scanning & probe generation (all 7 platforms):** `langgraph` (LangGraph), `hermes` (Hermes Agent), `openclaw` (OpenClaw), `pi` (Pi), `agentforce` (Salesforce Agentforce), `servicenow` (ServiceNow), and `http` (any custom HTTP agent).
- **Local probe execution & deterministic grading (`vail-grading` / `agent-improvement` skill):** **LangGraph**, **Hermes**, and **OpenClaw** (matching the platforms VAIL can also connect to and probe live on a schedule in the web app).

## Before you start

You need a VAIL organization. Sign up at <https://agents.projectvail.com>. When you connect from any coding agent below, your browser opens VAIL to confirm which account and organization to authorize. You can review or revoke connected apps at any time under **Access tokens** in the VAIL web app.

*(For headless environments, SSH boxes without port forwarding, CI pipelines, or the Hermes Desktop panel, you can also create a personal access token under **Access tokens** at <https://agents.projectvail.com/settings/tokens>.)*

## Install in Claude Code (and Claude / Cowork)

```text
/plugin marketplace add projectvail/vail-agent-assurance
/plugin install vail-agent-assurance@vail-agent-assurance
```

Then run `/mcp`, select `vail`, and complete the OAuth sign-in in your browser (or run `claude mcp login plugin:vail-agent-assurance:vail` in your terminal).

Ask Claude Code, for example: *"Scan the agent in ./support-bot with VAIL and show me the behaviors it finds."*

### Without the plugin

```sh
claude mcp add --scope user --transport http vail https://agents.projectvail.com/mcp
claude mcp login vail
```

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

## What it can do

| Tool | What it does |
|---|---|
| `get_identity` | Who the connection acts as, and what your organization may do. |
| `list_agents`, `create_agent` | Find or create the agent to work on. |
| `prepare_source_upload`, `complete_source_upload` | Upload an agent's source, as one `.tar.gz`/`.tgz`/`.tar` archive or a set of files. |
| `scan_agent` | Generate the agent's context and discover its behaviors. |
| `classify_behaviors` | Refresh risk classifications without rescanning. |
| `generate_probes`, `set_generation_limits` | Write probes for those behaviors. |
| `get_agent_status`, `get_operation_status` | Follow progress, failures, and what to do next. |
| `get_behaviors`, `get_probes` | Retrieve the complete current results as JSON. |
| `get_grading_package` | Download `vail-grading`, the package VAIL grades probe replies with, to test probes against an agent running locally (LangGraph, Hermes, or OpenClaw). |

### Steering experiments and Promote

The experiment workflow also exposes:

| Tools | Purpose |
|---|---|
| `get_steering_setup`, `validate_steering_contract` | Prepare and validate a contract and bindings for the agent's installed harness. |
| `collect_github_source` | Collect a committed source revision for later Promote. |
| `get_agent_connection`, `prepare_agent_connection` | Inspect a connection, or prepare a new direct endpoint when using a personal access token. Plugin OAuth users can connect a new endpoint in the VAIL web app. |
| `list_experiments`, `create_experiment`, `get_experiment`, `save_experiment_case`, `remove_experiment_case` | Find experiments, create drafts, and review the cases before they freeze. |
| `run_experiment`, `get_experiment_job`, `pause_experiment` | Run baseline and optimization as one job, follow progress, and pause or resume. |
| `set_experiment_profiles` | Configure manual comparisons when desired. |
| `get_experiment_report`, `get_experiment_execution` | Inspect scores, comparisons, responses and settings reported by the agent. |
| `get_promotion`, `preview_promotion`, `publish_promotion` | Review the best eligible change and publish one draft PR. |

Ask your coding agent to *"Set up steering for this agent on my test deployment. Run a reviewed experiment with at most three candidates and a $1 proposal budget. Show me the results and Promote preview."* Remote agent costs are separate from the proposal budget. To authorize publication after reviewing the preview, ask it to *"Open a draft PR for this Promote preview."*

The [steering workflow](plugins/vail-agent-assurance/skills/agent-assurance/references/steering.md) covers setup, review, execution, retries and promotion. Choose baseline repetitions, comparison repetitions, search limits and a proposal budget before starting. One `run_experiment` call with `phase: steering` runs the baseline and continues into optimization. Each candidate and its fresh baseline use the same comparison count. A baseline score of 100% stops the search.

VAIL workers run the experiment independently of the editor session. Repeating a launch with the same request key and arguments returns the original job. HTTP (`http-profile`) and LangGraph (`langgraph-context`) bindings receive only changed settings. The agent reports its defaults and effective values for every declared control. VAIL establishes the starting configuration from the first valid baseline receipt.

Promote requires a qualifying winner, a reviewed preview, and a supported HTTP or LangGraph mapping to settings in a GitHub repository. Review and merge the draft PR in GitHub, then deploy the change through your normal process. See the server's [steering guide](https://github.com/projectvail/probe-loop/blob/main/docs/steering/README.md) for scoring, harness support and limitations.

Steering requires a server deployment that includes [the steering implementation](https://github.com/projectvail/probe-loop/pull/50) and [the current MCP tool schemas](https://github.com/projectvail/probe-loop/pull/92). Check the `steering` capabilities in `get_identity` and verify that the needed tools are available before starting.

Create your VAIL account and authorize the GitHub App in the web app. The web app also handles probe approval and scheduling for recurring monitoring. Existing verified connections can run experiments. Deploy agents and install connectors in your own infrastructure.

### Local code improvements

The [agent-improvement skill](plugins/vail-agent-assurance/skills/agent-improvement/SKILL.md) downloads VAIL's grading package to test behavior risks against a local copy of your agent and help you implement source fixes.

## Repository layout

```text
.claude-plugin/marketplace.json                  the marketplace (read by Claude Code and Codex)
plugins/vail-agent-assurance/
  .claude-plugin/plugin.json                     Claude Code & Anthropic Directory manifest (OAuth 2.1)
  .codex-plugin/plugin.json, .mcp.json           Codex compatibility manifest & MCP server entry
  plugin.json, mcp.json                          Portable Agent Plugins v1 manifest (OpenAI & Hermes, OAuth 2.1)
  assets/                                        Square light/dark plugin logos and composer icons
  skills/agent-assurance/SKILL.md                the workflow skill, shared by all harnesses
  skills/agent-assurance/references/steering.md   experiment and Promote instructions
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

Keep each skill as a directory of its own name containing `SKILL.md`. None of these harnesses discovers a `SKILL.md` placed directly in the skills directory. Follow the [local server setup](https://github.com/projectvail/probe-loop/blob/main/README.md#coding-agents-against-a-local-server).

For a full local plugin-package test, make a disposable copy of this marketplace and give it a unique marketplace name. Change the MCP URL in the copied `.mcp.json` and `mcp.json` to point to the isolated server. Install that copy through the host's plugin installer and sign in as a test user in a fresh organization. Keep the published manifests pointed at production. Remove the temporary installation when the test is complete. This exercises skill loading and MCP tools in the actual host. Direct HTTP MCP calls alone do not establish plugin-host compatibility.

Codex may request tool approval when source collection replaces existing source or an experiment invokes a remote agent. A noninteractive `approval_policy = "never"` can reject a tool that still requires approval. It does not grant every tool permission. For an explicitly authorized unattended sandbox test, configure only the required plugin-scoped tool permissions before launching the host. Follow [Codex's installed server policy documentation](https://developers.openai.com/plugins/build/plugins#configure-installed-server-policy). Keep publication disabled unless the test explicitly includes it. Interactive users can approve the requested operation through the host's normal approval flow.
