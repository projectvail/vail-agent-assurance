---
name: agent-assurance
description: Scan agent source, classify behavior risks, and generate probes with VAIL, or set up steering contracts, run reviewed baseline and optimization experiments, and promote winning profiles as draft PRs. Use for VAIL onboarding, assurance scans and probes, behavior classification, steering experiments, and promotion. For local source fixes with VAIL's grading package, use agent-improvement.
---

# VAIL Agent Assurance Engine

The Assurance Engine reads an AI agent's source (its prompts, tool definitions, and code) and works out how the agent could misbehave and what it must keep doing correctly. It classifies discovered risks against industry security taxonomies and writes probes: test prompts with deterministic checks that evaluate those behaviors against the running agent. This skill drives that workflow—plus optional steering experiments and draft PR promotion—through the `vail` MCP server's tools. Depending on the coding agent, tools may appear with a prefix such as `mcp__vail__get_identity` or `mcp__plugin_vail-agent-assurance_vail__get_identity`; this skill uses the bare names.

## What the results mean

- **Vulnerability behaviors**: ways the agent could be led to do something harmful or unintended, such as acting on the wrong customer, calling a tool with the wrong argument, exceeding a limit, or leaking data. Each cites the evidence in the source that suggests it, plus security framework classifications (Cisco AI Security & Safety, OWASP Agentic Top 10, OWASP LLM Top 10, MITRE ATLAS, NIST AI 100-2) and `model_based` attribution when available.
- **Control behaviors**: things the agent must keep doing correctly, such as confirming before a refund or refusing out-of-scope requests.
- **Probes**: test cases for those behaviors. A probe has a message (often with placeholders filled from shared *option pools*) and the metrics that judge the agent's reply.

These are **hypotheses generated from source**, not findings. A vulnerability behavior means the source suggests a risk worth testing, not that the agent is vulnerable. Only running the probes against the agent establishes how it behaves: in the VAIL web app, through MCP steering experiments ([references/steering.md](references/steering.md)), or locally through the `agent-improvement` skill. Say this when presenting results.

## Before you start

The user needs an existing VAIL organization (sign up at https://agents.projectvail.com). The MCP server at `https://agents.projectvail.com/mcp` authenticates with **OAuth 2.1** in the browser (and also accepts personal access tokens for headless environments).

If the `vail` tools are missing or calls fail to authenticate, ask the user to complete sign-in for their client:

- **Claude Code / claude.ai / Cowork**: run `/mcp` (or `claude mcp login vail` in a terminal) and complete the browser sign-in, or click **Connect** on the VAIL connector in Claude.
- **Codex / ChatGPT**: run `/mcp` or `codex mcp login vail` (or click **Authenticate** in Settings → MCP servers) and allow access in the browser.
- **OpenCode**: run `/mcps` and select `vail`, or run `opencode mcp auth vail` in a terminal.
- **Cursor**: click **Connect** on the `vail` MCP server in Cursor's MCP settings to sign in via OAuth.
- **Hermes**: run `hermes mcp login vail` (or click **Authenticate** on the `vail` card under Capabilities → Connectors in Hermes Desktop). On older Hermes builds without portable plugin OAuth, run `hermes mcp add vail --url https://agents.projectvail.com/mcp --auth oauth` and sign in.

Never ask the user to paste a password or access token into the conversation, never write a token into a file yourself, and never put a token on a command line you run.

Call `get_identity` first to confirm which organization you are acting in.

## Choosing the agent

- `list_agents` lists the organization's agents with their IDs and stages. Always refer to an agent by its `agent_id`; names are not unique.
- If the user names an agent, match it against the list and confirm when more than one could match.
- `create_agent` creates a new one. It needs a name and a platform (`langgraph`, `hermes`, `openclaw`, `pi`, `agentforce`, `servicenow`, or `http`). Pass a `request_key`: a random string you generate once for this agent. If the call times out or the connection drops, retry with the **same** `request_key`, so the retry returns the agent the first call created instead of making a second one.

## Uploading or collecting source

VAIL cannot read files on this machine directly. You can either upload local files (`prepare_source_upload` + `complete_source_upload`) or, when the organization has authorized VAIL's GitHub App (and you want GitHub provenance for later Promote), collect a committed repository revision with `collect_github_source`.

To upload local files in three steps:

1. **Choose the files.** Either one archive (`.tar.gz`, `.tgz`, or `.tar`) or a set of individual text files. Supply the agent's own source: prompts, tool definitions, agent code, and relevant docs. Leave out secrets (`.env`, keys), lockfiles, build output, and data dumps; VAIL skips many of these anyway. For more than a few hundred files, make an archive (`tar czf agent.tgz <dir>`).
2. **Prepare the upload.** Call `prepare_source_upload` with the agent ID and, for each file, its relative path, size in bytes, and SHA-256 (`shasum -a 256 <file>`, or `sha256sum`). It returns an `upload_id` and, per file, a URL and form fields.
3. **Send each file** with a multipart POST, the returned fields first and the file last:
   ```sh
   curl -sS -X POST "<url>" -F "<field1>=<value1>" ... -F "file=@<local path>"
   ```
   A 2xx response means that file arrived. Then call `complete_source_upload` with the `upload_id`, plus optional `include`/`exclude` glob lists to narrow what is collected.

`complete_source_upload` validates the files and replaces the agent's source. Read the response, which reports accepted files, skipped files with reasons, and whether a limit truncated the collection. Tell the user about skipped files that look important.

A replacement is the **whole** new source: files you leave out are not kept from before. Generated results from the earlier source are kept but marked **outdated**, and the agent goes back to needing a scan.

Upload sessions expire after an hour. If `complete_source_upload` reports `operation_in_progress`, wait for the running operation and call `complete_source_upload` again with the same `upload_id`.

## Scanning, classifying, and generating probes

1. `scan_agent` starts the scan, which generates context and discovers vulnerability and control behaviors (automatically classifying vulnerability behaviors against security taxonomies when configured). It returns an `operation_id` straight away; the work continues on VAIL's servers even if this session ends.
2. Poll `get_operation_status` with that ID every 30–60 seconds rather than in a tight loop.
3. When the scan has succeeded, retrieve the behaviors with `get_behaviors`. To refresh taxonomy classifications later without rescanning, call `classify_behaviors` and poll `get_operation_status`.
4. `generate_probes` writes probes for those behaviors. It is a separate, explicit step: only run it when the user wants probes. Poll `get_operation_status` the same way, then call `get_probes`.

`set_generation_limits` changes how many vulnerability and control probes the next generation writes. Its bounds are reported by `get_agent_status`.

`get_agent_status` is the overall view: the agent's stage, its current source, whether its results are current or outdated, any running operation, recent operations, steering links, and `next_actions` listing what can be done now. Prefer it to guessing.

## Steering experiments and Promote

When the user wants to set up steering contracts (`get_steering_setup`, `validate_steering_contract`), connect a test endpoint (`get_agent_connection`, `prepare_agent_connection`), run reviewed baseline/optimization experiments (`list_experiments`, `create_experiment`, `get_experiment`, `save_experiment_case`, `remove_experiment_case`, `set_experiment_profiles`, `run_experiment`, `get_experiment_job`, `pause_experiment`, `get_experiment_report`, `get_experiment_execution`), or publish a winning profile as a draft GitHub PR (`get_promotion`, `preview_promotion`, `publish_promotion`), read and follow [references/steering.md](references/steering.md).

## When something fails

Errors have a `code`, a `message`, `retryable`, and `next_actions`. Follow `next_actions` rather than inventing a workaround.

- `missing_prerequisite`: an earlier step is needed (upload source before scanning; scan before generating probes).
- `operation_in_progress`: other work is running for this agent. Wait for it (`get_operation_status`) and try again.
- `source_replacement_in_progress`: a source upload is being saved. Try again shortly.
- `organization_not_approved`: the organization is awaiting approval, so scans and generation are off. Uploading still works. The user should contact VAIL.
- `results_not_ready`: there are no current results of that kind yet, or only outdated ones from earlier source.
- `upload_expired` / `upload_incomplete`: start a new upload, or send the missing files.

If a scan step fails, `get_operation_status` says which step and why. Calling `scan_agent` again is a new attempt, and it keeps a context step that already succeeded. Don't retry a failed step more than once or twice without telling the user.

## Retrieving results

`get_behaviors` and `get_probes` return complete JSON for the agent's current results, including `schema_version`, the agent, the source it was generated from, and the run that produced it. Probe exports include the option pools their placeholders draw from.

Larger results come back as a short-lived `download.url` instead. Fetch it promptly (`curl -sS -o <file> "<download.url>"`) and check the returned SHA-256.

Save results to files only when the user asks, and where they ask.

## Boundaries and next steps

Approving catalog probes for recurring scheduled monitoring and managing schedules happen in the VAIL web app at https://agents.projectvail.com, as do initial account signup and GitHub App installation. VAIL never merges promotion PRs or deploys changes to user infrastructure.

For local source fixes based on VAIL results, use the [agent-improvement skill](../agent-improvement/SKILL.md) (which downloads `vail-grading` via `get_grading_package` and grades local runs). For comparing runtime/request settings and opening a draft PR with a winning profile, use [references/steering.md](references/steering.md). If the user only requested a scan or probes, present the results and offer the relevant next step without starting it unasked.
