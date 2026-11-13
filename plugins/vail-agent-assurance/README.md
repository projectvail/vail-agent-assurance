# VAIL Agent Assurance

Use the [VAIL Agent Assurance Engine](https://agents.projectvail.com) from your coding agent to check the AI agents you build. Collect an agent's source, scan for behavior risks, and generate probes. Run a steering experiment to compare request settings and promote an eligible profile as a draft PR, or use VAIL's grading package to test and fix the agent locally.

The plugin bundles:

- a connection to VAIL's hosted MCP server at `https://agents.projectvail.com/mcp` authenticated via **OAuth 2.1**,
- the `agent-assurance` skill for source collection, scans, probe generation, and [steering experiments and Promote](skills/agent-assurance/references/steering.md), and
- the `agent-improvement` skill, which tests behavior risks against a local copy of the agent and proposes fixes, each of which you approve.

## Supported platforms

### Coding platforms

- **Claude Code** (CLI, VS Code, Desktop) and **Claude on the web / Cowork** (`claude.ai`)
- **OpenAI Codex** (CLI, IDE extension, ChatGPT desktop app) and **ChatGPT** (Web & Work)
- **Hermes Agent** and **Hermes Desktop** (portable Agent Plugins v1)
- **OpenCode** and **Cursor** (connect `https://agents.projectvail.com/mcp` via OAuth 2.1 and optionally copy `skills/`)

*(Note: uploading local source files and running the `agent-improvement` local grading loop require a coding agent with local shell access, such as Claude Code, Codex CLI/Desktop/IDE, OpenCode, Cursor, or Hermes. In cloud-only chat surfaces such as `claude.ai` or ChatGPT web, you can inspect organizations and agents, start scans or probe generation on already-connected source, and review behaviors and probes.)*

### Target AI agent frameworks

- **Source scanning & probe generation:** `langgraph` (LangGraph), `hermes` (Hermes Agent), `openclaw` (OpenClaw), `pi` (Pi), `agentforce` (Salesforce Agentforce), `servicenow` (ServiceNow), and `http` (custom HTTP agents).
- **Local probe execution & grading (`vail-grading`):** **LangGraph**, **Hermes**, and **OpenClaw**.

## Before you start

Sign up for a VAIL organization at <https://agents.projectvail.com>. No API keys or environment variables are needed: when you connect the plugin, your browser opens VAIL so you can approve access for your account. You can view and revoke connected apps any time under **Access tokens** at <https://agents.projectvail.com/settings/tokens>.

## Install

### Claude Code

```text
/plugin marketplace add projectvail/vail-agent-assurance
/plugin install vail-agent-assurance@vail-agent-assurance
```

Run `/mcp`, select `vail`, and finish signing in through your browser.

### Codex

```sh
codex plugin marketplace add projectvail/vail-agent-assurance
```

Restart Codex, run `/plugins` to install `vail-agent-assurance`, and sign in to `vail` from `/mcp` (or **Settings → MCP servers**).

### Hermes Agent

```sh
hermes plugins install projectvail/vail-agent-assurance/plugins/vail-agent-assurance --enable
hermes mcp login vail
```

### OpenCode & Cursor

- **OpenCode:** run `opencode mcp add vail --url https://agents.projectvail.com/mcp` and `opencode mcp auth vail`.
- **Cursor:** add `"vail": { "url": "https://agents.projectvail.com/mcp" }` to `~/.cursor/mcp.json` and click **Connect** in Cursor's MCP settings.

Then ask your coding agent, for example: *"Scan the agent in ./support-bot with VAIL and show me the behaviors it finds."* Or, after a scan: *"Fix the behavior risks VAIL found in ./support-bot."*

## What the plugin sends and downloads

The plugin runs no background process and installs nothing when it is enabled. Everything below happens only when you ask your coding agent to do it.

**Sent to VAIL**

- Every MCP call goes to `https://agents.projectvail.com/mcp` authenticated with your OAuth 2.1 token (acting as your VAIL user in your organization).
- **Your agent's source code.** When you ask to scan or upload an agent, your coding agent uploads that agent's source files (or one `.tar.gz`/`.tgz`/`.tar` archive of them) to VAIL, which stores them as the agent's source in your organization and analyzes them. Files are uploaded with ordinary shell tools (`curl`) to the temporary upload URLs VAIL returns. The skill instructs the coding agent to send prompts, tool definitions, code, and relevant docs, and to leave out secrets (`.env` files, keys), lockfiles, build output, and data dumps. VAIL still receives whatever is uploaded, so ask to see the file list before anything is sent if you want to check it.
- **GitHub source and steering experiments.** If asked to collect source from GitHub, VAIL reads a committed revision through your organization's authorized GitHub App. An experiment sends reviewed probes to your connected test agent. Automatic steering also calls VAIL's proposal model within the experiment budget. If you authorize an eligible winner for Promote, VAIL opens a draft PR with the reviewed settings diff.
- **New direct connections.** Set up a new direct test endpoint in the VAIL web app when you use the OAuth plugin. With a personal access token session, `prepare_agent_connection` issues a ticket so the local client can submit the endpoint credential directly to VAIL outside the MCP call. VAIL sends one verification request before saving the connection.

**Downloaded to your machine**

- **Results.** Behaviors and probes come back as JSON. Larger results come back as a short-lived download URL, which the coding agent fetches with `curl` and verifies against the SHA-256 VAIL returns.
- **Steering setup and results.** The setup tool returns a skill, schema, starters, and a runtime helper. Experiment drafts, reports, and execution records are returned as JSON or a short-lived download with a SHA-256 digest.
- **The grading package (`agent-improvement` skill only).** To grade local test runs the way VAIL does, the skill calls `get_grading_package`, downloads VAIL's Python wheel `vail-grading` from the URL it returns, checks its SHA-256, and installs it with `pip` into a dedicated virtual environment (for example `.vail/grading/` in your agent's repository), separate from your agent's environment. `pip` also installs the package's dependencies (`pydantic` and `jsonpath-ng`) from PyPI. The coding agent then runs `python -m vail_grading` from that environment.

**Run and written locally (`agent-improvement` skill only)**

- To test a behavior risk, your coding agent runs your agent locally and sends it the test messages after you approve the number of runs. Your agent then does whatever it normally does, including calling its model provider with your own credentials. The skill asks before any test that would use a tool with real side effects, and never points a test at production systems.
- Test results, which can include your agent's replies, are written to `.vail/improvement/` in your agent's repository. Before the first write, the skill checks whether git ignores `.vail/` and recommends adding it to `.gitignore` if not. The results stay on your machine: the skill does not upload them to VAIL.
- Every code change proposed waits for your approval.

## Tools

| Tool | What it does |
|---|---|
| `get_identity` | Who the connection acts as, and what your organization may do. |
| `list_agents`, `create_agent` | Find or create the agent to work on. |
| `prepare_source_upload`, `complete_source_upload` | Upload an agent's source. |
| `scan_agent` | Generate the agent's context, then discover its behaviors. |
| `classify_behaviors` | Refresh behavior classifications. |
| `generate_probes`, `set_generation_limits` | Write probes for those behaviors. |
| `get_agent_status`, `get_operation_status` | Follow progress, failures, and what to do next. |
| `get_behaviors`, `get_probes` | Retrieve the current results as JSON. |
| `get_grading_package` | Get the download for `vail-grading`, to test probes against an agent running locally (LangGraph, Hermes, or OpenClaw). |

### Steering experiments and Promote

| Tools | What they do |
|---|---|
| `get_steering_setup`, `validate_steering_contract` | Get the setup bundle and validate the contract against the agent's platform. |
| `collect_github_source` | Collect a committed GitHub revision for Promote. |
| `get_agent_connection`, `prepare_agent_connection` | Inspect a connection or issue a direct-connection ticket for a personal access token session. |
| `list_experiments`, `create_experiment`, `get_experiment`, `save_experiment_case`, `remove_experiment_case` | Find experiments, create drafts, and review the cases before they freeze. |
| `set_experiment_profiles`, `run_experiment`, `get_experiment_job`, `pause_experiment` | Configure manual candidates, launch an experiment, follow progress, and pause or resume. |
| `get_experiment_report`, `get_experiment_execution` | Inspect scores, comparisons, and individual responses and steering evidence. |
| `get_promotion`, `preview_promotion`, `publish_promotion` | Check eligibility, review a fixed settings diff, and publish an authorized draft PR. |

Check `get_identity` and the available tools before running [steering experiments](skills/agent-assurance/references/steering.md). Approving and scheduling probes for recurring monitoring happens in the VAIL web app.

## Support and license

Homepage: <https://agents.projectvail.com>. Documentation and other harnesses: <https://github.com/projectvail/vail-agent-assurance>. Privacy Policy: <https://agents.projectvail.com/privacy>. Terms of Service: <https://agents.projectvail.com/terms>. Questions: <contact@projectvail.com>.

Copyright © 2026 Project VAIL. All rights reserved. See [LICENSE](LICENSE).
