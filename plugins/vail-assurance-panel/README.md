# VAIL Assurance panel for Hermes Desktop

A Hermes Desktop page for assuring every Hermes profile with the [VAIL Agent Assurance Engine](https://agents.projectvail.com): scan a profile in one click, then see the behavior risks VAIL found, how many probes test them, which risks have no probe yet, and whether the profile's SOUL, skills, or plugins changed since its last scan.

It complements the `vail-agent-assurance` plugin, which gives the Hermes agent VAIL's tools and skills for scanning and fixing agents. This plugin is the view across all of them.

![Every Hermes profile with its VAIL results; Herald fixed locally](docs/team-overview.png)

## Install

```sh
hermes plugins install projectvail/vail-agent-assurance/plugins/vail-assurance-panel --enable
hermes config set VAIL_TOKEN vail_pat_...
```

Then, in Hermes Desktop, switch on **VAIL Assurance Panel** under **Capabilities → Plugins** (a package's Desktop half is off until you turn it on), and open **Assurance** in the sidebar.

`VAIL_TOKEN` is the same personal access token the `vail-agent-assurance` plugin uses, created under **Access tokens** at agents.projectvail.com. It is stored in your profile's `.env`, never in `config.yaml`.

## Using it

Each profile is a row.

- **Scan with VAIL** packages the profile, shows you exactly which files would be uploaded (and what is left out, and any values it redacted), and after you confirm, creates a Hermes agent for it on VAIL, uploads the files, scans them, and generates probes. The row shows progress; a scan takes a few minutes. **Rescan** does the same for a linked profile, replacing its agent's source; it is highlighted when the profile changed since the last scan.
- **Link** connects a profile to an agent that is already on VAIL (the panel suggests a Hermes agent whose name matches).
- **View risks** lists each risk with the tools involved and its probes.
- **Local test results.** When you test and fix a profile with the `vail-agent-assurance` plugin's `agent-improvement` skill, it keeps a record in the profile (`.vail/improvement/`). The row then shows how many risks were fixed locally and probes passing before and after the fix, and each risk is marked fixed, tested, or not addressed yet. A fix changes the profile, so the row asks you to rescan to confirm with VAIL.

**Refresh** fetches current results from VAIL; otherwise results are cached for two minutes.

![A profile's risks, each marked with what the improvement loop did about it](docs/risks-and-local-fixes.png)

![The review before a scan: exactly which files are uploaded](docs/scan-review.png)

### What a scan uploads

An allowlist: `SOUL.md`, `AGENTS.md`, `config.yaml`, the profile's own skills (skills bundled with Hermes are left out), and its plugins' source, as UTF-8 text files only. Never `.env` or any hidden file, auth or credential files, sessions, memories, logs, or databases. Every uploaded file is searched for token-shaped strings (VAIL, OpenAI, Anthropic, AWS, GitHub, Slack, Google and Telegram tokens, private keys, bearer tokens), and `config.yaml` values under secret-looking keys are replaced; both become `<redacted>`. `${VAR}` references are kept, since they name a secret without containing it. The review dialog shows the result before anything is sent.

To use a local VAIL server instead of the hosted one, set `plugins.entries.vail-assurance-panel.settings.vail_url` (for example `http://127.0.0.1:8099/mcp`) and use that server's token.

## What it does on your machine

- **Network:** calls the VAIL MCP endpoint (`https://agents.projectvail.com/mcp` by default) with your token, to read your organization's agents, their status, behavior risks, and probes. Only when you start a scan and confirm the review does it upload that profile's files (see above) to VAIL, which stores them as the agent's source.
- **Reads:** each profile's `SOUL.md`, `AGENTS.md`, `config.yaml`, skills, and plugins, to show what the profile contains, whether it changed, and to build the upload. It never reads `.env`, auth files, sessions, or memories.
- **Writes:** only `links.json` (profile name to VAIL agent id) in the plugin's own data directory.
- **Background work:** while a scan runs, a thread in the Hermes gateway checks VAIL's progress every 15 seconds and starts probe generation when the scan finishes; it ends with the scan (at most 45 minutes). No shell commands, no telemetry.

## Layout

```text
plugin.yaml                 native manifest: settings (vail_url) and the VAIL_TOKEN secret
__init__.py                 required entry point; the agent half registers nothing
dashboard/manifest.json     declares the backend for Hermes's plugin API mount
dashboard/plugin_api.py     routes under /api/plugins/vail-assurance-panel/
dashboard/fleet.py          profiles, links, and VAIL summaries (no Hermes imports)
dashboard/package.py        builds a profile's upload: allowlist and redaction (no Hermes imports)
dashboard/scan.py           create, upload, scan, generate probes
dashboard/vail_client.py    standard-library MCP client for VAIL
desktop/plugin.js           the Desktop page (plain ESM, Hermes plugin SDK only)
```
