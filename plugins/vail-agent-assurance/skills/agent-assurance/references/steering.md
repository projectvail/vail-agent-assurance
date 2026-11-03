# Steering from the editor

Use this workflow to compare request settings and promote a tested profile. For local source fixes, use the `agent-improvement` skill instead.

Call `get_identity` and inspect the available tools first. They act as the token's person within their organization. Account/token setup and initial GitHub authorization remain in VAIL. Keep the same agent ID and experiment ID throughout a run.

## Prepare the agent

1. Call `get_steering_setup` for the maintained setup skill, schema, runtime helper and starters. Follow that skill in the agent repository. Inspect the installed harness, declare bounded controls, implement their request bindings, and test each control and request isolation. `validate_steering_contract` returns canonical JSON and its digest. Static validation does not prove that the deployed agent applies settings.
2. For new HTTP/LangGraph bindings, follow the version-3 override protocol. Send only changed settings and keep runtime defaults for omitted controls. The response must report the declared settings the agent actually used and its defaults before overrides. Never report secrets or merely echo the requested values. VAIL learns its starting settings from a valid baseline response, not from source defaults.
3. Collect `vail-steering.json` at the source root with the implementation. For Promote, use `collect_github_source` with a committed repository/ref that VAIL can access through its configured GitHub authorization. Uploads work for local development but do not establish a PR destination. Source replacement makes generated results outdated. Scan and regenerate probes before creating a new experiment. Existing experiments retain their original inputs and results.
4. Inspect `get_agent_connection`. Use an existing verified direct connection or connector, or prepare a new direct connection as described below. Contract setup alone does not authorize production changes, probe execution or PR publication. Use the deployment the user authorized.

### Connect a direct endpoint

Call `prepare_agent_connection` with the endpoint, auth scheme and platform fields listed by `get_agent_connection`. It returns a fixed URL and a short-lived ticket. POST JSON `{ticket, secret}` to that URL with an HTTP client. Read `secret` directly from a local environment variable or key file. Omit it for no-auth or stored-key reuse. A stored key can be reused only for its original endpoint.

Keep the secret out of MCP arguments, shell command text, logs and committed files. Keep the ticket out of logs and shared files too. Submission sends one connection-test request and saves the connection only on success. Retrying the same ticket returns its recorded outcome. After an interruption, inspect connection state before preparing another ticket.

## Review the experiment

1. Call `create_experiment` with a new ID, `limit_usd`, `baseline_repetitions` and `comparison_repetitions`. The budget covers proposal-model calls only. Remote agent calls incur separate charges. After a lost creation response, inspect that ID with `get_experiment` before retrying.
2. Read the complete `get_experiment` result. It returns either `delivery: inline` with `result`, or a JSON `download`. Fetch downloads and verify their SHA-256. Review the messages, metrics, measurement limits, and links to behaviors and requirements.
3. Call `save_experiment_case` for each selected case. Pass its existing key, current revision, and complete case fields: `role`, `split`, `fixture_set`, `probe`, `success_keys`, `review`, and `authorized_action`. Preserve the behavior and requirement links. Choose actual non-consistency metric keys as completion checks and explain why they establish success.
4. Remove unwanted cases with `remove_experiment_case`. Use the revision returned by each edit for the next edit or launch. State-changing acceptance cases require explicit action authorization and an appropriate test deployment.

For legitimate tasks, check completion as well as safety. Avoiding a forbidden tool call does not prove that a requested lookup or calculation succeeded. Add missing checks against the actual response or tool schema before the cases freeze. Keep the safety requirements. If you discover a scoring gap after a run, preserve that run and create a newly reviewed experiment. Never change frozen criteria or weaken checks to raise a score.

## Run the full experiment

Call `run_experiment` once with `phase: steering`, the latest revision, a fresh `request_key`, and the chosen `comparison_repetitions`. Set a bounded `sweep`, such as `{max_candidates: 3, patience: 2}`. Omit methods to use the agent's integration.

This single job freezes the reviewed cases, completes the initial baseline, and continues into optimization. A separate baseline launch is not required. Each candidate and its fresh baseline use the same comparison count. That count freezes when comparison begins. Later candidates carry accepted improvements forward.

Behavioral failures in a completed baseline give the loop something to improve. Request errors or unscorable responses can prevent baseline completion and stop the job before optimization. A baseline score of 100% also stops the search. Otherwise, the loop stops at 100%, its budget or candidate limits, or its limit on attempts without improvement.

Poll `get_experiment_job` with the returned job ID every 30–60 seconds. Scan and probe-generation operation IDs use `get_operation_status` instead. After completion, inspect `get_experiment_report`. Use `execution_index` IDs with `get_experiment_execution` to read responses, tool traces, failed checks and settings reported by the agent. Fetch complete downloads when needed.

Review and execute within the user's authorization, including authorization already given for the full flow. Do not introduce a new approval at every phase. For a setup-only request, report the setup results without launching an experiment.

### Optional baseline review or manual comparison

Use `phase: baseline` separately only when the user wants to inspect baseline results before optimization or supply a manual profile. After baseline review, choose comparison repetitions and launch `phase: steering` for automatic optimization.

For a manual comparison, call `set_experiment_profiles`, then run `phase: comparison`. Runtime profiles contain complete values. Start from `get_experiment.runtime_baseline.values` when available, or the draft's profile values for legacy contracts. Version-3 source defaults are not the observed baseline. The runner sends only changes from that baseline.

A manual comparison can test a control even when baseline scores 100%. A tie cannot qualify for Promote.

## Retry, pause and inspect

Retry a lost launch response with the **same request_key and identical arguments**. This returns the original job even after completion. Use a new key only for a new intended launch, including an explicit resume.

`pause_experiment` takes effect after the current proposal or agent request finishes. It retains completed runs. Before an edit or explicit resume, get the latest revision. Resume with the frozen comparison and sweep settings.

Stop on repeated errors or an exhausted budget and report what happened. Distinguish settings VAIL requested from those the API accepted or the agent confirmed. Failed executions and missing scores are not passes. Report counts, fresh-baseline results, regressions and any limits from acceptance-only confirmation. A 100% probe score does not establish general reliability.

## Promote

Call `get_promotion` for the report's winning profile. Only the best complete profile above both the original and its fresh baseline can qualify. Promote requires a GitHub source and a supported mapping to a settings file the agent loads. Direct Hermes/OpenClaw API fields and extra request instructions have no supported mapping. Report the returned reason when promotion is unavailable.

`preview_promotion` returns an immutable diff, score results and plan ID. Present the change and measurement limitations for review. If the user authorized publication, including earlier in the task, call `publish_promotion` with that exact plan ID. Otherwise, request authorization against the concrete preview. Publication creates a draft PR. VAIL never merges it or deploys the change.

Retry the same plan after a lost response to recover its PR, then link the result. Changed source or a different winner can invalidate a preview. Obtain a fresh preview and review the changed result before publication.
