# VAIL Agent Assurance

Use the [VAIL Agent Assurance Engine](https://agents.projectvail.com) from your coding agent to check and harden the AI agents you build. Upload or collect an agent's source, scan it for vulnerability and control behaviors, classify risks against five security taxonomies and `model_based` attribution, generate deterministic probes, score every vulnerability on **Impact**, **Trigger**, and **Fidelity risks**, and retrieve the results—without leaving your editor. From there, you can either run server-side steering experiments and promote a winning configuration as a draft GitHub PR, or test and fix the agent's source locally with VAIL's deterministic grading package.

The plugin bundles:

- a connection to VAIL's hosted MCP server at `https://agents.projectvail.com/mcp` authenticated via **OAuth 2.1**,
- the `agent-assurance` skill, which walks your coding agent through source collection, scanning, behavior classification, probe generation, Impact/Trigger/Fidelity risk scoring, steering experiments, and draft PR promotion, and
- the `agent-improvement` skill, which tests behavior risks against a local copy of the agent (including nested consistency checks for contradictory rules) and proposes source fixes, each of which you approve.

## Supported platforms

### Coding platforms

- **Claude Code** (CLI, VS Code, Desktop) and **Claude on the web / Cowork** (`claude.ai`)
- **OpenAI Codex** (CLI, IDE extension, ChatGPT desktop app) and **ChatGPT** (Web & Work)
- **Hermes Agent** and **Hermes Desktop** (portable Agent Plugins v1)
- **OpenCode** and **Cursor** (connect `https://agents.projectvail.com/mcp` via OAuth 2.1 and optionally copy `skills/`)

*(Note: uploading local source files and running the `agent-improvement` local grading loop require a coding agent with local shell access, such as Claude Code, Codex CLI/Desktop/IDE, OpenCode, Cursor, or Hermes. In cloud-only chat surfaces such as `claude.ai` or ChatGPT web, you can inspect organizations and agents, start scans or probe generation on already-connected source, and review behaviors and probes.)*

### Target AI agent frameworks

- **Source scanning, classification, probe generation, and scoring:** `langgraph` (LangGraph), `hermes` (Hermes Agent), `openclaw` (OpenClaw), `pi` (Pi), `agentforce` (Salesforce Agentforce), `servicenow` (ServiceNow), and `http` (custom HTTP agents).
- **Live probing & steering experiments:** **LangGraph**, **Hermes**, **OpenClaw**, and **custom HTTP** (`http`). For private-network LangGraph, Hermes, and OpenClaw agents, use the signed outbound-only VAIL agent connector container ([setup guide](https://agents.projectvail.com/docs/guides/connector.md)).
- **Local probe execution & grading (`vail-grading`):** **LangGraph**, **Hermes**, and **OpenClaw**.

## Before you start

Sign up for a VAIL organization at <https://agents.projectvail.com> (see [plans and pricing](https://agents.projectvail.com/pricing), or [pricing.md](https://agents.projectvail.com/pricing.md) for agents). No API keys or environment variables are needed: when you connect the plugin, your browser opens VAIL so you can approve access for your account. You can view and revoke connected apps any time under **Access tokens** at <https://agents.projectvail.com/settings/tokens>.

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

Then ask your coding agent naturally—the skills trigger without naming VAIL: *"Find out where the agent in ./support-bot breaks its own instructions, and check whether it is ready to ship."* Or, to fix a finding: *"It still calls the wrong tool after I told it not to — test ./support-bot locally and prove the fix holds."*

## What the plugin sends and downloads

The plugin runs no background process and installs nothing when it is enabled. Everything below happens only when you ask your coding agent to do it.

**Sent to VAIL**

- Every MCP call goes to `https://agents.projectvail.com/mcp` authenticated with your OAuth 2.1 token (acting as your VAIL user in your organization).
- **Your agent's source code.** When you ask to scan or upload an agent, your coding agent uploads that agent's source files (or one `.tar.gz`/`.tgz`/`.tar` archive of them) to VAIL via the temporary staging URLs returned by `prepare_source_upload`, or instructs VAIL to collect a committed revision from an already-authorized GitHub repository via `collect_github_source`. The skill instructs the coding agent to send prompts, tool definitions, code, and relevant docs, and to leave out secrets (`.env` files, keys), lockfiles, build output, and data dumps. VAIL still receives whatever is uploaded, so ask to see the file list before anything is sent if you want to check it.
- **Direct endpoint connections and steering experiments (when requested).** If you ask to connect a direct test endpoint via `prepare_agent_connection`, VAIL returns a short-lived verification URL and signed ticket so credentials stay out of MCP tool arguments and chat text, and sends one verification message before saving. (For private-network LangGraph, Hermes, and OpenClaw agents, the outbound-only VAIL agent connector keeps the agent's credential on its host.) Running `run_experiment` sends reviewed experiment probes to your connected test agent and (for automatic steering) calls VAIL's proposal model within your configured `limit_usd` budget. Calling `publish_promotion` after reviewing `preview_promotion` opens a draft PR on your connected GitHub repository; VAIL never merges a PR or deploys code.
- **Classification and scoring data handling.** Behavior classification and Impact/Trigger scoring run through OpenRouter's decisions endpoint with Zero Data Retention (`zdr`) enforced by default. Probe run history is retained for 90 days.

**Downloaded to your machine**

- **Results and steering setup files.** Behaviors (with `scores`, `fidelity_risks`, `scoring_guide`, and `classifications`), probes, experiment drafts, reports, and execution traces come back as JSON (or as a short-lived download URL verified by SHA-256 when large). `get_steering_setup` returns portable text templates and reference docs for declaring `vail-steering.json` controls.
- **The grading package (`agent-improvement` skill only).** To grade local test runs the way VAIL does, the skill calls `get_grading_package`, downloads VAIL's Python wheel `vail-grading` from the URL it returns, checks its SHA-256, and installs it with `pip` into a dedicated virtual environment (for example `.vail/grading/` in your agent's repository), separate from your agent's environment. `pip` also installs the package's dependencies (`pydantic` and `jsonpath-ng`) from PyPI. The coding agent then runs `python -m vail_grading` from that environment.

**Run and written locally (`agent-improvement` skill only)**

- To test a behavior risk, your coding agent runs your agent locally and sends it the test messages after you approve the number of runs. Your agent then does whatever it normally does, including calling its model provider with your own credentials. The skill asks before any test that would use a tool with real side effects, and never points a test at production systems.
- Test results, which can include your agent's replies, are written to `.vail/improvement/` in your agent's repository. Before the first write, the skill checks whether git ignores `.vail/` and recommends adding it to `.gitignore` if not. The results stay on your machine: the skill does not upload them to VAIL.
- Every code change proposed waits for your approval.

## Tools (all 33 MCP tools)

### Identity, agents, source, scanning, and probes (14 tools)

| Tool | What it does |
|---|---|
| `get_identity` | Who the connection acts as, and what your organization may do. |
| `list_agents` | List your organization's agents with their stable IDs, platforms, and stages. |
| `create_agent` | Create a new agent in your organization and return its `agent_id`. |
| `get_agent_status` | Report one agent's stage, collected source, result freshness, steering links, and allowed `next_actions`. |
| `prepare_source_upload` | Start a staged source upload session and return temporary upload URLs per file. |
| `complete_source_upload` | Validate staged files and publish them as the agent's complete new source. |
| `scan_agent` | Asynchronously generate context, discover vulnerability and control behaviors, and automatically classify vulnerabilities against the five security taxonomies and `model_based` attribution. |
| `classify_behaviors` | Classify or re-classify discovered vulnerability behaviors against Cisco AI Security & Safety v2.0.0, OWASP Agentic Top 10 2026, OWASP LLM Top 10 2026, MITRE ATLAS v2026.09, and NIST AI 100-2 E2025 (plus `model_based` attribution; preserves human overrides). |
| `generate_probes` | Asynchronously write vulnerability and control probes plus shared option pools, then score every vulnerability behavior (including those without probes; controls are not scored) on Impact, Trigger, and Fidelity-risk membership. |
| `get_operation_status` | Poll queued, running, succeeded, or failed state and substeps (`generate_context`, `discover_behaviors`, `generate_probes`, `score_behaviors`) for `scan_agent`, `classify_behaviors`, or `generate_probes`. |
| `set_generation_limits` | Update how many vulnerability and control probes subsequent generations write. |
| `get_behaviors` | Retrieve the complete current vulnerability and control behavior artifacts (with `scores`, `fidelity_risks` count, `scoring_guide`, and `classifications`; discovery `severity` is not returned) as JSON or a verified download. |
| `get_probes` | Retrieve the complete current probe catalogs and referenced option pools as JSON or a verified download. |
| `get_grading_package` | Get the temporary download descriptor for `vail-grading`, to grade local test runs (LangGraph, Hermes, or OpenClaw). |

### Steering setup, endpoint connection, experiments, and Promote (19 tools)

| Tool | What it does |
|---|---|
| `get_steering_setup` | Return the steering setup skill, schema, runtime helpers, and starter contracts for an agent's platform. |
| `validate_steering_contract` | Statically validate a proposed `vail-steering.json` contract against the agent's platform without saving it. |
| `collect_github_source` | Collect a committed GitHub repository revision through your organization's VAIL GitHub App authorization for Promote provenance. |
| `get_agent_connection` | Read an agent's connection state, supported `platform_config` fields, and auth schemes without returning stored secrets. |
| `prepare_agent_connection` | Issue a short-lived ticket URL to test and save a direct agent endpoint connection without putting credentials in MCP arguments. |
| `list_experiments` | List an agent's steering experiments, revisions, and frozen runs. |
| `create_experiment` | Create a new experiment draft from the agent's generated probes (or copy a prior frozen experiment) with a proposal budget. |
| `get_experiment` | Retrieve an experiment's draft cases, review status, revision, controls, profiles, progress, and budget. |
| `save_experiment_case` | Review, edit, or add one draft experiment case with completion checks and action authorization. |
| `remove_experiment_case` | Remove an unwanted case from an unfrozen experiment draft. |
| `set_experiment_profiles` | Configure manual candidate profiles and comparison repetition counts on an experiment. |
| `run_experiment` | Launch an experiment job (`baseline`, full `steering` baseline + optimization, or manual `comparison`). |
| `get_experiment_job` | Poll progress and status for a running or completed experiment job. |
| `pause_experiment` | Pause a running experiment job at the next safe boundary while retaining completed evidence. |
| `get_experiment_report` | Retrieve experiment scores, fresh-baseline comparisons, winning profile, and measurement limits. |
| `get_experiment_execution` | Retrieve one recorded probe execution's full response, tool trace, scoring, and applied-profile receipt. |
| `get_promotion` | Check whether a winning profile qualifies for GitHub PR promotion or read its existing PR receipt. |
| `preview_promotion` | Prepare an immutable GitHub diff, score evidence, and `plan_id` for a qualifying winner without publishing. |
| `publish_promotion` | Publish a reviewed `plan_id` from `preview_promotion` as a draft GitHub pull request (never merges or deploys). |

Approving catalog probes for recurring scheduled monitoring and managing schedules happen in the VAIL web app, as do initial organization signup and GitHub App installation.

## Support and license

Homepage: <https://agents.projectvail.com>. Pricing: <https://agents.projectvail.com/pricing> ([pricing.md](https://agents.projectvail.com/pricing.md)). Agent connector setup: <https://agents.projectvail.com/docs/guides/connector.md>. Documentation and other harnesses: <https://github.com/projectvail/vail-agent-assurance>. Privacy Policy: <https://agents.projectvail.com/privacy>. Terms of Service: <https://agents.projectvail.com/terms>. Questions: <contact@projectvail.com>.

Copyright © 2026 Project VAIL. All rights reserved. See [LICENSE](LICENSE).
