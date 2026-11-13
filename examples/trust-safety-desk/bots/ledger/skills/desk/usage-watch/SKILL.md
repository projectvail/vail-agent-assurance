---
name: usage-watch
description: "Count agents, scans and probe generations per VAIL organization and user, and flag accounts that look like abuse."
version: 0.1.0
author: VAIL
metadata:
  hermes:
    tags: [VAIL, admin, usage, abuse]
---

# Usage watch

Use when someone asks how much the engine is being used, by whom, or whether anyone is abusing it.

1. Call `get_usage` with `group_by: "org"` for the window asked about (24 hours if none was given),
   then with `group_by: "user"`.
2. Report the totals, then the busiest organizations and users.
3. Flag an account when any of these hold, and say which:
   - More than **10 agents created** or **20 scans** within an hour.
   - More than **20 probe generations** in a day.

     `get_usage` checks these two for you: each row's `thresholds_crossed` lists every threshold the
     account crossed, with the count. Report exactly those; do not re-derive them, and do not call an
     account clean when its list is not empty.
   - Several organizations whose users share an email domain or an address with a `+` tag
     (rick@x and rick+qa@x): one person splitting their usage across accounts. `get_usage` lists
     these in `cross_org_signals`. Before reporting one, call `get_org` for **each** of its
     org_ids to see their users.
   - Heavy use by an organization created in the last day (`org_created_at`).
4. For each flag, give the numbers and a recommendation for a person ("Recommend a closer look",
   "Recommend contacting the owner"). You cannot suspend or limit an account.

These thresholds are starting points. Normal use is a few agents and scans a day; say so when an
account is high but not past a threshold.
