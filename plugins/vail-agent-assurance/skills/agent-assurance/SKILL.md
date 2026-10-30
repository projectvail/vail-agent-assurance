---
name: agent-assurance
description: Use VAIL Agent Assurance Engine to scan an AI agent's source for unintended behaviors and generate test probes. Use when the user asks to scan, assess, or generate probes or test cases for an agent with VAIL or the Assurance Engine, to upload or replace an agent's source in VAIL, or to check on or retrieve VAIL behaviors and probes.
---

# VAIL Agent Assurance Engine

The Assurance Engine reads an AI agent's source (its prompts, tool definitions, and code) and works out how the agent could misbehave and what it must keep doing correctly. It then writes probes: test prompts that check those behaviors against the running agent. This skill drives that workflow through the `vail` MCP server's tools. Depending on the coding agent, they may appear with a prefix, such as `mcp__vail__get_identity` in Claude Code and Codex or `mcp_vail_get_identity` in Hermes; this skill uses the bare names.

## What the results mean

- **Vulnerability behaviors**: ways the agent could be led to do something harmful or unintended, such as acting on the wrong customer, calling a tool with the wrong argument, exceeding a limit, or leaking data. Each one cites the evidence in the source that suggests it.
- **Control behaviors**: things the agent must keep doing correctly, such as confirming before a refund or refusing out-of-scope requests.
- **Probes**: test cases for those behaviors. A probe has a message (often with placeholders filled from shared *option pools*), and the metrics that judge the agent's reply.

These are **hypotheses generated from source**, not findings. A vulnerability behavior means the source suggests a risk worth testing, not that the agent is vulnerable. Only running the probes against the agent establishes how it behaves: live, in the VAIL web app, or locally, through the `agent-improvement` skill. Say this when presenting results.

## Before you start

The user needs an existing VAIL organization (sign up at https://agents.projectvail.com) and a personal access token, created under **Access tokens** in the web app. The MCP connection authenticates against `https://agents.projectvail.com/mcp` with an `Authorization: Bearer` header holding that token; it is configured once, by the user, not by you.

If the `vail` tools are missing or every call fails to authenticate, ask the user to create a token and configure it for their coding agent:

- **Claude Code** (plugin): run `/plugin` and configure vail-agent-assurance. Claude Code keeps the token in secure storage.
- **Codex** (plugin or `config.toml`): Codex reads the token from the `VAIL_TOKEN` environment variable. Set it in the environment Codex starts from, then restart Codex.
- **Hermes**: run `hermes mcp add vail --url https://agents.projectvail.com/mcp --auth header` and enter the token when prompted. Hermes stores it in its own secrets file, outside the config you might share.

Never ask them to paste a token into the conversation, never write one into a file yourself, and never put one on a command line you run.

Call `get_identity` first to confirm which organization you are acting in.

## Choosing the agent

- `list_agents` lists the organization's agents with their IDs and stages. Always refer to an agent by its `agent_id`; names are not unique.
- If the user names an agent, match it against the list and confirm when more than one could match.
- `create_agent` creates a new one. It needs a name and a platform (`langgraph`, `hermes`, `openclaw`, `pi`, `agentforce`, `servicenow`, or `http`). Pass a `request_key`: a random string you generate once for this agent. If the call times out or the connection drops, retry with the **same** `request_key`, so the retry returns the agent the first call created instead of making a second one.

## Uploading source

VAIL cannot read files on this machine. You transfer them yourself with your shell tools, in three steps:

1. **Choose the files.** Either one archive (`.tar.gz`, `.tgz`, or `.tar`) or a set of individual text files. Supply the agent's own source: prompts, tool definitions, agent code, and relevant docs. Leave out secrets (`.env`, keys), lockfiles, build output, and data dumps; VAIL skips many of these anyway. For more than a few hundred files, make an archive (`tar czf agent.tgz <dir>`).
2. **Prepare the upload.** Call `prepare_source_upload` with the agent ID and, for each file, its relative path, size in bytes, and SHA-256 (`shasum -a 256 <file>`, or `sha256sum`). It returns an `upload_id` and, per file, a URL and form fields.
3. **Send each file** with a multipart POST, the returned fields first and the file last:
   ```sh
   curl -sS -X POST "<url>" -F "<field1>=<value1>" ... -F "file=@<local path>"
   ```
   A 2xx response means that file arrived. Then call `complete_source_upload` with the `upload_id`, plus optional `include`/`exclude` glob lists to narrow what is collected.

`complete_source_upload` validates the files and replaces the agent's source. The upload succeeding is not the same as the source being collected: read the response, which reports accepted files, skipped files with reasons, and whether a limit truncated the collection. Tell the user about skipped files that look important.

A replacement is the **whole** new source: files you leave out are not kept from before. Generated results from the earlier source are kept but marked **outdated**, and the agent goes back to needing a scan.

Upload sessions expire after an hour. If `complete_source_upload` reports the agent is busy (`operation_in_progress`), a scan or probe generation is running; wait for it, then call `complete_source_upload` again with the same `upload_id`.

## Scanning and generating probes

1. `scan_agent` starts the scan, which has two internal steps: **context generation** (reading the source into a structured description of the agent) and **behavior discovery**. It returns an `operation_id` straight away; the work continues on VAIL's servers even if this session ends.
2. Poll `get_operation_status` with that ID. Scans usually take several minutes; wait between polls (30–60 seconds is plenty) instead of polling in a tight loop. The status shows each step and recent progress messages.
3. When the scan has succeeded, retrieve the behaviors with `get_behaviors`.
4. `generate_probes` writes probes for those behaviors. It is a separate, explicit step: only run it when the user wants probes. Poll it the same way, then call `get_probes`.

`set_generation_limits` changes how many vulnerability and control probes the next generation writes. Its bounds are reported by `get_agent_status`.

`get_agent_status` is the overall view: the agent's stage, its current source, whether its results are current or outdated, any running operation, recent operations, and `next_actions` listing what can be done now. Prefer it to guessing.

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

Larger results come back as a short-lived `download_url` instead. Fetch it promptly (`curl -sS -o <file> "<download_url>"`) and check the returned SHA-256.

Save results to files only when the user asks, and where they ask.

## What this does not do

These tools do not connect to the live agent, run or review probes, approve or reject them, or schedule them. Those happen in the VAIL web app at https://agents.projectvail.com; point the user there for them.

To test and fix the agent locally from these results, use the `agent-improvement` skill. Once probes are retrieved, offer it to the user.
