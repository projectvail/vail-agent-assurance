# VAIL Assurance panel for Hermes Desktop

A Hermes Desktop page that shows what the [VAIL Agent Assurance Engine](https://agents.projectvail.com) knows about each of your Hermes profiles: the behavior risks VAIL found, how many probes test them, which risks have no probe yet, and whether a profile's SOUL, skills, or plugins changed since VAIL last scanned it.

It complements the `vail-agent-assurance` plugin, which gives the Hermes agent VAIL's tools and skills for scanning and fixing agents. This plugin is the view across all of them.

## Install

```sh
hermes plugins install projectvail/vail-agent-assurance/plugins/vail-assurance-panel --enable
hermes config set VAIL_TOKEN vail_pat_...
```

Then, in Hermes Desktop, switch on **VAIL Assurance Panel** under **Capabilities → Plugins** (a package's Desktop half is off until you turn it on), and open **Assurance** in the sidebar.

`VAIL_TOKEN` is the same personal access token the `vail-agent-assurance` plugin uses, created under **Access tokens** at agents.projectvail.com. It is stored in your profile's `.env`, never in `config.yaml`.

## Using it

Each profile is a row. Link a profile to its agent on VAIL (the panel suggests a Hermes agent whose name matches the profile), then **View risks** to see each risk with the tools involved and its probes. **Refresh** fetches current results from VAIL; otherwise results are cached for two minutes.

To use a local VAIL server instead of the hosted one, set `plugins.entries.vail-assurance-panel.settings.vail_url` (for example `http://127.0.0.1:8099/mcp`) and use that server's token.

## What it does on your machine

- **Network:** calls the VAIL MCP endpoint (`https://agents.projectvail.com/mcp` by default) with your token, to read your organization's agents, their status, behavior risks, and probes. It sends nothing about your profiles to VAIL.
- **Reads:** each profile's `SOUL.md` and `config.yaml`, and the file names and modification times under its `skills/` and `plugins/` directories, to show what the profile contains and whether it changed. It never reads `.env`, auth files, sessions, or memories.
- **Writes:** only `links.json` (profile name to VAIL agent id) in the plugin's own data directory.
- No background process, no shell commands, no telemetry.

## Layout

```text
plugin.yaml                 native manifest: settings (vail_url) and the VAIL_TOKEN secret
__init__.py                 required entry point; the agent half registers nothing
dashboard/manifest.json     declares the backend for Hermes's plugin API mount
dashboard/plugin_api.py     routes under /api/plugins/vail-assurance-panel/
dashboard/fleet.py          profiles, links, and VAIL summaries (no Hermes imports)
dashboard/vail_client.py    standard-library MCP client for VAIL
desktop/plugin.js           the Desktop page (plain ESM, Hermes plugin SDK only)
```
