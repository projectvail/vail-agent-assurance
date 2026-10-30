---
name: agent-improvement
description: Use VAIL Agent Assurance Engine results to fix and harden an AI agent locally. Use when the user asks to fix, improve, harden, or address an agent's VAIL or Assurance Engine results, behavior risks, or vulnerabilities, to test VAIL probes against a locally running agent, or to continue an earlier session of doing so.
---

# Improving an agent from its VAIL results

The VAIL Assurance Engine (AE) scans an agent's source and reports **behavior risks**: ways the agent could be led to do something harmful or unintended. This skill works through those risks with the user: deciding which can be tested and fixed here, testing them against the agent running locally, and fixing what the tests show.

The user decides what is worth addressing and approves every change. You propose, test, and implement.

Call them **behavior risks** in everything you show the user. AE's data calls them vulnerability behaviors: they are the `vulnerabilities` artifact from `get_behaviors`. Use AE's names only when referring to data fields.

This skill uses the `vail` MCP server's tools and the `agent-assurance` skill's setup. If the `vail` tools are missing or fail to authenticate, follow that skill's **Before you start**.

## Before you start

1. Call `get_identity` to confirm the organization, then choose the agent by `agent_id`, as in the `agent-assurance` skill.
2. Call `get_agent_status`. You need current behaviors. If there are none, or they are outdated, the agent must be scanned first (the `agent-assurance` skill covers that). Probes are useful but not required: a behavior risk with no probe can still be addressed.
3. Ask where the agent's source is locally, if it is not the current directory.
4. Look for a results file from an earlier session (see **The results file**). If one exists for this agent:
   - If its `ae.run_id` matches the run of AE's current results, summarize what was done and what is left, and offer to continue from `position`.
   - If it differs, AE's results have changed since then. Say so, keep the old file, and start a new one.

## Set up grading

AE grades probe replies with a Python package, `vail-grading`. Install the same version locally, so your grades match AE's.

1. Call `get_grading_package`. It returns a `version`, a `download` (with `url`, `filename`, `sha256`, and an expiry of 15 minutes), and `install` instructions.
2. Download the file under its own `filename`: `curl -sS -o <filename> "<download.url>"`. Check its SHA-256 (`shasum -a 256 <filename>`, or `sha256sum`) against `download.sha256`.
3. Install it into a virtual environment of its own, separate from the agent's, for example `.vail/grading/`, as `install` describes.
4. Run `python -m vail_grading examples` with that environment's Python. It lists worked examples for every metric type, a captured run for each supported platform, and a guide per platform to running the agent locally. Read the guide for the agent's platform before the first test.

If `get_grading_package` reports `grading_package_unavailable`, local grading is not available from this server right now: you can still make fixes that need no test, and tell the user.

The package supports LangGraph, Hermes, and OpenClaw agents. For an agent on another platform, local testing with AE's grading is not available yet: say so, and address only behavior risks that need no test.

## Read the results

1. `get_behaviors` and `get_probes` (as in the `agent-assurance` skill: inline, or a download to fetch and check). Keep the probe export as a file: rendering reads it.
2. Work only with the `vulnerabilities` artifact: those are the behavior risks. Control behaviors are not part of this.
3. Attach each probe to the behavior risks it tests, using its `behavior_ids`.

Each behavior risk has a `title`, `description`, `severity`, `testability`, `requirements` (each with the `violations` that would break it), and `evidence` pointing into the source: `document_paths`, `tool_names`, `subagent_names`.

## Decide what is addressable

For each behavior risk, decide whether it can be addressed here. AE's `testability` describes what AE can observe through a remote probe, which is narrower than what you can do with the source and a local agent: read it as information, not as the answer.

A behavior risk is **addressable** if either:

- **It can be fixed without running a test**, by changing the agent itself: a bug in a tool-calling function, a clear oversight in a skill or prompt, a schema inconsistency between two files.
- **How it would show up can be observed by testing the agent locally.** Where AE generated probes, base the test on them: the probe as is, or adapted for a meaningful local run.

It is **not addressable** here if testing it meaningfully needs any of:

- access to an external system, such as a production database
- running over a sustained period
- the production environment itself, such as how much traffic it can handle

Record the decision and the reason for each.

## Group and order

Group the addressable behavior risks by the part of the agent a fix would change. A group is one of:

- a single tool
- a single skill
- a single subagent
- the main instructions or system prompt
- configuration, such as model settings or permissions
- changes outside the files, such as the environment or deployment

To place a behavior risk:

1. Start from its evidence: the tools, subagents, and files it points to.
2. Read those files to find where the fix would most likely go. That is not always where the risk shows up: a bad tool call may come from a skill's instructions rather than the tool.
3. Put it in exactly one group, the one where its main fix would be. Mention the other parts involved when you reach it.

A group of one is fine.

Order the groups by how important their part of the agent is, most important first. Judge importance by how central it is to the agent's purpose, how often the agent uses it, and what it can affect: a tool that sends, writes, or deletes matters more than one that only reads. Within a group, any order.

**Stop.** Show the user the groups, their order, and a one-line reason for each group's place, and wait for them to confirm or change the order.

## Walk through each behavior risk

In the confirmed order, for each behavior risk:

1. **Ask whether to address it. Stop for the answer.** If the user is fine leaving it, record it as dismissed with their reason, and move on.
2. **Propose an approach. Stop for approval.** Either a clear fix that needs no test, or a local test first. Say which and why.
3. **If testing, agree the test plan before running anything. Stop for approval.** The plan says:
   - what is tested, and how it differs from AE's probe, if at all
   - how many repetitions: if the outcome may vary between runs (as it usually does with a model), run it several times, and consider variants, such as other option-pool cases
   - which models: ask whether to run against other models the agent already supports, to see how the result depends on the model's capability and personality
   - whether the test will be run again after a fix, to compare
   - **the total number of runs** (test cases × models × repetitions, including any rerun after a fix)

   Then run it (see **Running a test locally**).
4. **Propose fixes. Stop for approval of every change.**
   - Propose only changes that are highly likely to work.
   - A fix may include tests for the user's own test suite, to guard against regressions, written in that suite's conventions. Not every fix needs one, and they do not use the grading package.
   - A fix may be partly or wholly outside the files, such as an environment or deployment setting. Describe it; record the description.
   - If the test was inconclusive, do not guess at a fix: recommend a further line of inquiry.
   - If the approved plan includes a rerun after the fix, run it, so the record shows both states.
5. **Record the outcome, and move on.**

Update the results file after every decision and every run.

## Running a test locally

### The agent

Work out how to run the agent locally, from its source and the platform's guide in the grading package. Ask the user whenever it is unclear: how they run it, which model and credentials it uses, what it may safely do. Never point a test at production systems, and never let a test take actions with real side effects; ask the user when a tool would.

### Parameterized probes

Many AE probes are templates. Their message, and the expected values in their metrics, hold placeholders such as `{{customer.name}}` that draw from **option pools** of cases. A case is a coherent set of related values: a customer's name, ID, and limit that belong together. AE varies them so that a pass is not a coincidence of one example. The pools come with the probe export (`option_pools`).

### One test, step by step

With the grading environment's Python:

1. **Render a test case:** `python -m vail_grading render --probes <probe export> --probe-id <id> --out cases/<test case id>.json`. It fills the message and the metrics from the same case, adds AE's response-format instructions to a JSON probe's message, and records the cases used.
2. **Send the test case's `message`** to the local agent once per repetition, a fresh conversation each time, capturing each run's raw output as the platform's guide describes.
3. **Convert** each capture: `python -m vail_grading convert --platform <platform> <raw file> --out <reply file>`.
4. **Grade** the repetitions together: `python -m vail_grading grade <test case> <reply 1> <reply 2> ...`. Each metric's `result.passed` is true, false, or null when it could not be judged (the reason is in `result.details`). Leave out a repetition whose run failed, and record the failure.
5. **Record the run** in the results file.

### Keeping the message and the metrics consistent

- **Repetitions repeat one test case**: the same message, graded by the same metrics.
- **A variant is a new render**: other cases (`--case <binding>=<case id>`, or another `--seed`), or a whole case of your own (`--case-values <file>`, as `{"<binding>": {"<field>": value}}`; it must hold every value the probe uses).
- **To adapt a probe, edit its template and render it again** with `--template <file>` (a rendered test case's `template` is a good start). Never hand-edit a rendered message or its metrics: that is how they fall out of step.

### Your judgment

The package is the default, because its grades match AE's. It is not a requirement. You may:

- override a metric's grade, with a reason
- add checks of your own alongside AE's metrics, graded by code you write or by your own judgment of the replies
- test and grade entirely your own way when the package does not fit: a behavior risk with no probe, a check no metric type expresses, a multi-turn test

Whatever you choose, record which checks came from AE and which from you, and why.

## The results file

Keep a record in the agent's repository, in `.vail/improvement/<agent_id>/<run_id>/`, where `run_id` is the run of AE's current results. The format is in [results-format.md](results-format.md).

It can hold agent replies and internal data. Before writing it the first time, check whether git already ignores `.vail/` (`git check-ignore -q .vail/`). If it does not, ask the user whether to add `.vail/` to `.gitignore`, and recommend it. If it does, say so, and confirm with the user that they want it kept out of version control.

Write it after every user decision and every test run, so an interrupted session loses at most the step in progress. It is also how a later session picks up where this one stopped.

## What to tell the user

- Local results are evidence about this agent, with these models, in this environment, not proof. Say how many runs a conclusion rests on.
- AE's behavior risks are hypotheses from source. A risk that a fair test never triggers may not be real; say so rather than forcing a fix.
- When you are done, summarize what was fixed, dismissed, inconclusive, and not addressable, and where the results file is. Don't suggest scanning the updated source again or comparing against a new scan.
