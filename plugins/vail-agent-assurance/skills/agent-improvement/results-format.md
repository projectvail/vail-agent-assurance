# The results file

A session's record lives in the agent's repository:

```text
.vail/improvement/<agent_id>/<run_id>/
  results.json
  cases/<test case id>.json      rendered test cases (from `render`)
  replies/<run id>/<n>.json      each repetition's raw output and converted reply
  diffs/<behavior id>.patch      the file changes of a fix
```

`run_id` is the run of AE's current results, as `get_behaviors` reports it.

## `results.json`

```json
{
  "schema_version": 1,
  "agent": {"agent_id": "...", "name": "...", "platform": "langgraph"},
  "ae": {"source_id": "...", "run_id": "...", "retrieved_at": "...", "grading_package_version": "..."},
  "local_setup": {"how_run": "...", "models": ["..."]},
  "position": {"stage": "triage | ordering | walkthrough | done", "current_behavior_id": "..."},
  "walkthrough_order": ["<behavior_id>", "..."],
  "results": [
    {
      "behavior_id": "...",
      "title": "...",
      "probe_ids": ["..."],
      "addressable": true,
      "addressability_reason": "...",
      "group": "tool: issue_refund",
      "other_components": ["..."],
      "decision": "pending | address | dismissed",
      "dismissal_reason": null,
      "approach": {"kind": "direct_fix | local_test", "description": "...", "approved": true},
      "tests": [
        {
          "test_id": "t1",
          "based_on_probe_id": "...",
          "own_checks": [
            {"check_id": "k1", "description": "...", "method": "code | judgment", "why": "..."}
          ],
          "adaptations": "...",
          "template_file": null,
          "test_cases": [
            {"test_case_id": "t1-c1", "file": "cases/t1-c1.json", "variant": "..."}
          ],
          "models": ["..."],
          "repetitions": 5,
          "planned_runs": 10
        }
      ],
      "runs": [
        {
          "run_id": "r1",
          "test_case_id": "t1-c1",
          "agent_state": "before_fix | after_fix",
          "model": "...",
          "reply_files": ["replies/r1/1.json", "replies/r1/2.json"],
          "grading_package_version": "...",
          "metric_results": [
            {"key": "...", "ae_grade": true, "final_grade": true, "override_reason": null}
          ],
          "own_check_results": [
            {"check_id": "k1", "passed": true, "notes": "..."}
          ]
        }
      ],
      "fix": {
        "status": "none | proposed | applied | declined",
        "description": "...",
        "diff_file": "diffs/<behavior_id>.patch",
        "regression_tests": ["tests/test_refunds.py"],
        "outside_files_changes": null,
        "approved": true
      },
      "conclusion": "fix_applied | no_fix | inconclusive",
      "notes": "...",
      "further_inquiry": null
    }
  ]
}
```

## Fields

- `results` holds every behavior risk, addressable or not. One that is not addressable has `addressable: false`, its reason, and nothing further.
- `walkthrough_order` is the order the user confirmed, empty until then. `position` is where the walkthrough stands.
- `group` is a short label for the part of the agent the behavior risk's group is defined by, such as `tool: issue_refund` or `skill: refunds`. The ranking of groups and the reasons shown to the user are not stored.
- A **run** is all the repetitions of one test case against one model and agent state, graded together.
- A test can use AE's metrics, checks of your own, or both:
  - AE's metrics are those in its test cases; their results go in `metric_results`, with `ae_grade` from the package and `final_grade` after any override.
  - Your own checks are defined in `own_checks`, saying how each is judged and why it was added; their results go in `own_check_results`.
- `template_file` names an edited template when a probe was adapted, or a template of your own that uses AE's metric types.
- A test with a message of your own has no `based_on_probe_id`. Without AE's metrics, its test cases are files you write, holding the message sent.
- `planned_runs` is the total number of messages the test sends (test cases × models × repetitions), the number the user approved.
- `agent_state` says whether a run was before or after the fix.
- `conclusion` is `fix_applied`, `no_fix` (dismissed, or tested without needing a fix), or `inconclusive`, with `further_inquiry` recommending what to look at next.

The format is provisional: record what the session needs even where a field is missing, under `notes`.
