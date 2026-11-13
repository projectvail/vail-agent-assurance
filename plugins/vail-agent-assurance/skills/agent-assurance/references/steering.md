# Steering from the editor

Use this workflow to compare request settings and promote a tested profile. For local source fixes, use the `agent-improvement` skill instead.

Call `get_identity` and inspect the available tools first. They act as the signed-in person within their organization. Initial account setup and GitHub App authorization remain in the VAIL web app. Keep the same `agent_id` and `experiment_id` throughout a run.

## Prepare the agent

1. Call `get_steering_setup` for the maintained setup skill, schema, runtime helper, and starters. Follow that skill in the agent repository. Inspect the installed harness, declare bounded controls, implement their request bindings, and test each control and request isolation. `validate_steering_contract` returns canonical JSON and its digest. Static validation does not prove that the deployed agent applies settings.
2. For HTTP/LangGraph bindings, follow the override protocol: VAIL sends only changed settings and keeps runtime defaults for omitted controls. The response must report the declared settings the agent actually used and its defaults before overrides. Never report secrets or merely echo the requested values. VAIL learns its starting settings from a valid baseline response, not from source defaults.
3. Collect `vail-steering.json` at the source root with the implementation. For Promote, use `collect_github_source` with a committed repository and ref that VAIL can access through its configured GitHub authorization. Uploads work for local development (`prepare_source_upload` + `complete_source_upload`) but do not establish a PR destination. Source replacement makes generated results outdated; scan (`scan_agent`) and regenerate probes (`generate_probes`) before creating a new experiment. Existing frozen experiments retain their original inputs and results.
4. Inspect `get_agent_connection`. Use an existing verified direct connection or connector, or prepare a new direct connection as described below. Contract setup alone does not authorize production changes, probe execution, or PR publication. Use the deployment the user authorized.

### Connect a direct endpoint

Call `prepare_agent_connection` with the endpoint, auth scheme, and platform fields listed by `get_agent_connection`. It returns a fixed URL and a short-lived ticket. POST JSON `{ticket, secret}` to that URL with an HTTP client, reading `secret` directly from a local environment variable or key file (omit `secret` for no-auth or stored-key reuse; a stored key can be reused only for its original endpoint).

Keep the secret out of MCP arguments, shell command text, logs, and committed files. Keep the ticket out of logs and shared files too. Submission sends one connection-test request and saves the connection only on success. Retrying the same ticket returns its recorded outcome. After an interruption, inspect `get_agent_connection` before preparing another ticket.

## Review the experiment

1. Call `list_experiments` to check existing drafts or frozen runs, or call `create_experiment` with a new `experiment_id`, `limit_usd`, `baseline_repetitions`, and `comparison_repetitions`. The budget covers proposal-model calls only; remote agent calls incur separate charges. After a lost creation response, inspect that ID with `get_experiment` before retrying.
2. Read the complete `get_experiment` result. It returns either `delivery: "inline"` with `result`, or a JSON `download`. Fetch downloads and verify their SHA-256. Review the messages, metrics, measurement limits, and links to behaviors and requirements.
3. Call `save_experiment_case` for each selected case. Pass its existing `key`, current `revision`, and complete `case` fields (`role`, `split`, `probe`, `success_keys`, `review`, and `authorized_action`). Preserve the behavior and requirement links. Choose actual non-consistency metric keys as completion checks and explain why they establish success.
4. Remove unwanted cases with `remove_experiment_case`. Use the `revision` returned by each edit for the next edit or launch. State-changing acceptance cases require explicit action authorization and an appropriate test deployment.

For legitimate tasks, check completion as well as safety: avoiding a forbidden tool call does not prove that a requested lookup or calculation succeeded. Add missing checks against the actual response or tool schema before the cases freeze, keeping the safety requirements. If you discover a scoring gap after a run, preserve that run and create a newly reviewed experiment rather than changing frozen criteria or weakening checks to raise a score.

## Run the full experiment

Call `run_experiment` once with `phase: "steering"`, the latest `revision`, a fresh `request_key`, and the chosen `comparison_repetitions`. Set a bounded `sweep`, such as `{"max_candidates": 3, "patience": 2}`. Omit `methods` to use the agent's integration.

This single job freezes the reviewed cases, completes the initial baseline, and continues into optimization. Each candidate and its fresh baseline use the same comparison count, frozen when comparison begins. Later candidates carry accepted improvements forward. A baseline score of 100% stops the search; otherwise the loop stops at 100%, its budget or candidate limits, or `patience` attempts without improvement.

Poll `get_experiment_job` with the returned `job_id` every 30–60 seconds (`get_operation_status` is for `scan_agent`, `classify_behaviors`, and `generate_probes`). After completion, inspect `get_experiment_report`, and pass IDs from `execution_index` to `get_experiment_execution` to read responses, tool traces, failed checks, and settings reported by the agent.

### Optional baseline review or manual comparison

Use `phase: "baseline"` separately only when the user wants to inspect baseline results before optimization or supply a manual profile. For a manual comparison, call `set_experiment_profiles` and then `run_experiment` with `phase: "comparison"`. Start runtime profiles from `get_experiment.runtime_baseline.values` when available. A tie cannot qualify for Promote.

## Retry, pause, and inspect

Retry a lost launch response with the **same `request_key` and identical arguments** to recover the original job. Use a new key only for a new intended launch, including an explicit resume.

`pause_experiment` pauses at the next safe boundary while retaining completed runs. Before an edit or explicit resume, read the latest `revision` and keep the frozen comparison and sweep settings.

## Promote

Call `get_promotion` for the report's winning `profile_id`. Only the best complete profile above both the original and its fresh baseline can qualify, and Promote requires a GitHub source (`collect_github_source`) plus a supported repository mapping. Report the returned reason when promotion is unavailable.

`preview_promotion` returns an immutable diff, score evidence, and `plan_id` without publishing. Present the diff and measurement limitations for review. When the user authorizes publication, call `publish_promotion` with that exact `plan_id` to open a draft GitHub PR (retrying the same `plan_id` recovers the PR if interrupted). VAIL never merges a PR or deploys the change.
