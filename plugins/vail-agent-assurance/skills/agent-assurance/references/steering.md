# Steering from the editor

Use this workflow to compare request settings and promote a tested profile. For local source fixes, use the `agent-improvement` skill instead.

Call `get_identity` and check its `steering` capabilities and the available tools. VAIL acts as your signed-in user in the connected organization. Set up the account and authorize the GitHub App in VAIL. Keep the same agent ID and experiment ID throughout a run.

## Prepare the agent

1. Call `get_steering_setup` for the maintained setup skill, schema, runtime helper and starters. Follow that skill in the agent repository. Inspect the installed harness, declare bounded controls, implement their request bindings, and test each control and request isolation. `validate_steering_contract` returns canonical JSON and its digest. Test the deployed binding separately.
2. Use the contract's `transport` field to select the binding. Choose `http-profile` for custom HTTP, `langgraph-context` for LangGraph, `hermes-runs` for native Hermes, or `openclaw-agent` for the native OpenClaw gateway. Set `runtime_version` to the installed harness version or deployment revision. Omit the numeric `version` field. With HTTP or LangGraph, the request carries only changed values. The receipt reports the ordinary defaults and effective values for every declared control. VAIL learns the starting configuration from the first valid baseline receipt. Native Hermes and OpenClaw use complete declared profiles and confirm the fields available in their runtime metadata.
3. Collect `vail-steering.json` at the source root with the implementation. For Promote, use `collect_github_source` with a committed repository/ref that VAIL can access through its configured GitHub authorization. Source replacement makes generated results outdated. Scan and regenerate probes before creating a new experiment. Existing experiments retain their original inputs and results.
4. Inspect `get_agent_connection` and use the verified connection for the test deployment. LangGraph, Hermes and OpenClaw support the outbound connector. A custom HTTP binding uses a direct connection. If the user only wants to test extra request instructions on a supported connection, a contract is optional.

### Connect a direct endpoint

For a plugin session signed in with OAuth, open the agent's **Connect** page in the VAIL web app using `get_steering_setup.web.connect`. After setup, call `get_agent_connection` again to confirm the connection. The current server only accepts tickets from personal access token sessions on the MCP connection form.

With a personal access token and local shell access, call `prepare_agent_connection` with a `connection` object containing `endpoint_url`, `auth_scheme`, and any needed `auth_header`, `allow_insecure_http`, or `platform_config`. Use the auth schemes and platform fields from `get_agent_connection`. POST the returned `fields.ticket` as `ticket` to the returned `url`, with the optional `secret` read directly from a local environment variable or key file. Omit `secret` for no-auth or stored-key reuse. A stored key can be reused only for its original endpoint.

Keep the secret out of MCP arguments, shell command text, logs and committed files. Keep the ticket out of logs and shared files too. Submission sends one connection-test request and saves the connection only on success. Retrying the same ticket returns its recorded outcome. After an interruption, inspect connection state before preparing another ticket.

## Review the experiment

1. Call `create_experiment` with a new ID, `limit_usd`, `baseline_repetitions` and `comparison_repetitions`. The budget covers proposal-model calls only. Remote agent calls incur separate charges. Use `list_experiments` to find existing experiment IDs. After a lost creation response, check the intended ID with `get_experiment` before retrying.
2. Read the complete `get_experiment` result. It returns either `delivery: inline` with `result`, or a JSON `download`. Fetch downloads and verify their SHA-256. Review the messages, metrics, measurement limits, and links to behaviors and requirements.
3. Call `save_experiment_case` for each selected case. Pass its existing `key`, the current `revision`, and a `case` with `role`, `probe`, `success_keys`, and `review`. The case also accepts `split: discovery` and `authorized_action`. Resolve option-pool bindings before freezing. Preserve the behavior and requirement links. Choose actual non-consistency metric keys as completion checks and explain why they establish success.
4. Remove unwanted cases with `remove_experiment_case`. Use the revision returned by each edit for the next edit or launch. State-changing acceptance cases require explicit action authorization and an appropriate test deployment.

For legitimate tasks, check completion as well as safety. Avoiding a forbidden tool call does not prove that a requested lookup or calculation succeeded. Add missing checks against the actual response or tool schema before the cases freeze. Keep the safety requirements. If you discover a scoring gap after a run, preserve that run and create a newly reviewed experiment. Never change frozen criteria or weaken checks to raise a score.

## Run the full experiment

Call `run_experiment` once with `phase: steering`, the latest revision, a fresh `request_key`, and the chosen `comparison_repetitions`. Set a bounded `sweep`, such as `{max_candidates: 3, patience: 2}`. Omit methods to use the agent's integration.

This single job freezes the reviewed cases, completes the initial baseline, and continues into optimization. A separate baseline launch is not required. Each candidate and its fresh baseline use the same comparison count. That count freezes when comparison begins. Later candidates carry accepted improvements forward.

Behavioral failures in a completed baseline give the loop something to improve. Request errors or unscorable responses can prevent baseline completion and stop the job before optimization. A baseline score of 100% also stops the search. Otherwise, the loop stops at 100%, its budget or candidate limits, or its limit on attempts without improvement.

Poll `get_experiment_job` with the returned job ID every 30–60 seconds. Use `get_operation_status` for scan and probe-generation operations. After completion, inspect `get_experiment_report`. Use `execution_index` IDs with `get_experiment_execution` to read responses, tool traces, failed checks and settings reported by the agent. Fetch complete downloads when needed.

Review and execute within the user's authorization, including authorization already given for the full flow. Do not introduce a new approval at every phase. For a setup-only request, report the setup results without launching an experiment.

### Optional baseline review or manual comparison

Use `phase: baseline` separately only when the user wants to inspect baseline results before optimization or supply a manual profile. After baseline review, choose comparison repetitions and launch `phase: steering` for automatic optimization.

For a manual comparison, call `set_experiment_profiles` with the current revision, then launch `phase: comparison` with the returned revision. For HTTP and LangGraph, build the complete runtime profile from `runtime_baseline.values` in the `get_experiment` result. VAIL sends only differences from that observed baseline. For native Hermes or OpenClaw, start from the draft's declared profile values. Each candidate needs an ID, method, rationale and target signal IDs.

A manual comparison can test a control even when baseline scores 100%. A tie cannot qualify for Promote.

## Retry, pause and inspect

Retry a lost launch response with the **same request_key and identical arguments**. This returns the original job even after completion. Use a new key only for a new intended launch, including an explicit resume.

`pause_experiment` takes effect after the current proposal or agent request finishes. It retains completed runs. Before an edit or explicit resume, get the latest revision. Resume with the frozen comparison and sweep settings.

Stop on repeated errors or an exhausted budget and report what happened. Distinguish settings VAIL requested from those the API accepted or the agent confirmed. Failed executions and missing scores are not passes. Report counts, fresh-baseline results, regressions and any limits from acceptance-only confirmation. A 100% probe score does not establish general reliability.

## Promote

Call `get_promotion` with the report's winning `profile_id`. Only the best complete profile above both the original and its fresh baseline can qualify. Promote requires a committed GitHub source and a supported HTTP or LangGraph mapping to the contract baseline the agent loads. Report the returned reason when promotion is unavailable.

`preview_promotion` returns an immutable diff, score results and `plan_id`. Present the change and measurement limitations for review. If the user authorized publication, call `publish_promotion` with the same agent, experiment and profile IDs and that exact `plan_id`. Publication creates a draft PR for review and merge in GitHub.

Retry the same plan after a lost response to recover its PR, then link the result. Changed source or a different winner can invalidate a preview. Obtain a fresh preview and review the changed result before publication.
