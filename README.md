# VAIL Agent Assurance for coding agents

Use the [VAIL Agent Assurance Engine](https://agents.projectvail.com) from your coding agent. Collect an agent's source, scan for behavior risks, and generate probes that test them. Then run steering experiments and promote a winning profile as a draft PR, or test and fix the agent locally.

This repository is a plugin marketplace for Claude Code and Codex containing one plugin, `vail-agent-assurance`. It bundles:

- a connection to VAIL's hosted MCP server at `https://agents.projectvail.com/mcp`
- the `agent-assurance` skill for source collection, scans, probes, steering experiments and Promote
- the `agent-improvement` skill for testing behavior risks locally with VAIL's grading package and fixing agent code

Hermes doesn't install plugins from this marketplace, but it can use the same MCP server and skills. See [Hermes](#hermes).

VAIL runs scans and steering experiments on its server. You do not need a local VAIL server, CLI or AWS credentials. Your coding agent inspects your repository, collects source, and submits connection credentials directly from a local environment or key file. For local code improvements, it also runs your agent and VAIL's grading package on your machine.

## Before you start

1. You need a VAIL organization. Sign up at <https://agents.projectvail.com>.
2. Create a personal access token: sign in, open **Access tokens**, choose a name and an expiry, and copy the token (`vail_pat_...`). It is shown only once.

A token acts as you and has your permissions in the organization. It stops working if you revoke it, it expires, or you leave the organization. Use one token per device or tool.

## Install in Claude Code

```text
/plugin marketplace add projectvail/vail-agent-assurance
/plugin install vail-agent-assurance@vail-agent-assurance
```

Claude Code asks for your VAIL access token when you enable the plugin. It keeps the token in your system's secure credential store. To change it later, run `/plugin` and configure `vail-agent-assurance`.

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

### Steering experiments and Promote

The experiment workflow also exposes:

| Tools | Purpose |
|---|---|
| `get_steering_setup`, `validate_steering_contract` | Prepare and validate a contract and bindings for the agent's installed harness. |
| `collect_github_source` | Collect a committed source revision for later Promote. |
| `get_agent_connection`, `prepare_agent_connection` | Inspect a connection or securely submit/test a new direct endpoint. |
| `create_experiment`, `get_experiment`, `save_experiment_case`, `remove_experiment_case` | Create and review the fixed probe bundle. |
| `run_experiment`, `get_experiment_job`, `pause_experiment` | Run baseline and optimization as one job, follow progress, and pause or resume. |
| `set_experiment_profiles` | Configure manual comparisons when desired. |
| `get_experiment_report`, `get_experiment_execution` | Inspect scores, comparisons, responses and settings reported by the agent. |
| `get_promotion`, `preview_promotion`, `publish_promotion` | Review the best eligible change and publish one draft PR. |

For example: *"Set up steering for this agent on my test deployment. Run a reviewed experiment with at most three candidates and a $1 proposal budget. Show me the results and Promote preview."* Remote agent costs are separate from the proposal budget. Add *"Promote the winner if it beats both baselines. Don't merge it."* when you want to authorize PR publication too.

The [steering workflow](plugins/vail-agent-assurance/skills/agent-assurance/references/steering.md) covers setup, review, execution, retries and promotion. Choose baseline repetitions, comparison repetitions, search limits and a proposal budget before starting. One `run_experiment` call with `phase: steering` runs the baseline and continues into optimization. Each candidate and its fresh baseline use the same comparison count. A baseline score of 100% stops the search.

VAIL workers run the experiment independently of the editor session. Repeating a launch with the same request key and arguments returns the original job. For new HTTP/LangGraph bindings, VAIL sends only changed settings. The agent reports the effective configuration, and the baseline captures its starting settings.

Promote requires a qualifying winner, a reviewed preview, and a supported mapping to settings in a GitHub repository. Direct Hermes/OpenClaw API controls and extra request instructions do not have a supported mapping. VAIL never merges a PR or deploys the change. See the server's [steering guide](https://github.com/projectvail/probe-loop/blob/review/steering-contracts/docs/steering/README.md) for scoring, harness support and limitations.

**Server dependency:** these tools require [probe-loop PR #50](https://github.com/projectvail/probe-loop/pull/50). Until that server version is deployed, updating the plugin alone does not enable execution. `get_identity` advertises the available capabilities. Deploy the reviewed server changes before releasing this plugin version.

Create your account and access token in the web app, and authorize GitHub access there. The web app also handles probe approval and scheduling for recurring monitoring. Existing verified connectors can run experiments. You install and configure connectors and deploy agent code in your own infrastructure.

### Local code improvements

The [agent-improvement skill](plugins/vail-agent-assurance/skills/agent-improvement/SKILL.md) tests behavior risks against a local copy of your agent. It downloads VAIL's grading package and helps you review and implement source fixes. Those local results do not create a steering winner. Use steering experiments when you want to compare request settings and use Promote.

## Repository layout

```text
.claude-plugin/marketplace.json                  the marketplace (read by Claude Code and Codex)
plugins/vail-agent-assurance/
  .claude-plugin/plugin.json                     Claude Code manifest: token from userConfig
  .codex-plugin/plugin.json                      Codex manifest: token from $VAIL_TOKEN
  skills/agent-assurance/SKILL.md                the workflow skill, shared by all harnesses
  skills/agent-assurance/references/steering.md  experiment and Promote instructions
  skills/agent-improvement/                      testing and fixing an agent locally from its results
```

Validate changes with `claude plugin validate .` and `claude plugin validate ./plugins/vail-agent-assurance`. For every release, bump `version` in **both** manifests to the same value. CI checks this.

The published plugin connects to production. To test only skill changes against a local VAIL server, connect the local server directly and copy both skill directories:

| Harness | Connect `http://127.0.0.1:8099/mcp` | Copy the skill to |
|---|---|---|
| Claude Code | `claude mcp add` (as in [Without the plugin](#without-the-plugin)) | `~/.claude/skills/<skill>/` |
| Codex | a `[mcp_servers.vail]` entry in `~/.codex/config.toml` | `~/.agents/skills/<skill>/` |
| Hermes | `hermes mcp add vail --url http://127.0.0.1:8099/mcp --auth header` | `~/.hermes/skills/<skill>/` |

```sh
cp -R plugins/vail-agent-assurance/skills/agent-assurance plugins/vail-agent-assurance/skills/agent-improvement ~/.claude/skills/
```

Keep each skill as a directory of its own name containing `SKILL.md`. None of these harnesses discovers a `SKILL.md` placed directly in the skills directory. The server's README, under "Coding agents against a local server", explains how to run it.

For a full local plugin-package test, make a disposable copy of this marketplace and give it a unique marketplace name. Change the copied manifest's MCP URL to the isolated local server. Install that copy through the host's plugin installer and use a token for a fresh test organization. Keep the published manifests pointed at production. Remove the temporary installation when the test is complete. This exercises skill loading and MCP tools in the actual host. Direct HTTP MCP calls alone do not establish plugin-host compatibility.

Codex may request tool approval when source collection replaces existing source or an experiment invokes a remote agent. A noninteractive `approval_policy = "never"` can reject a tool that still requires approval. It does not grant every tool permission. For an explicitly authorized unattended sandbox test, configure only the required plugin-scoped tool permissions before launching the host. Follow [Codex's installed server policy documentation](https://developers.openai.com/plugins/build/plugins#configure-installed-server-policy). Keep publication disabled unless the test explicitly includes it. Interactive users can approve the requested operation through the host's normal approval flow.
