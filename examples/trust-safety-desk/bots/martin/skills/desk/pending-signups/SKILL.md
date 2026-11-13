---
name: pending-signups
description: "List the organizations waiting for approval on the VAIL Assurance Engine, newest first."
version: 0.1.0
author: VAIL
metadata:
  hermes:
    tags: [VAIL, admin, signups]
---

# Pending signups

Use when someone asks what is waiting for approval, or for a regular check-in.

1. Call `list_pending_orgs`.
2. If there are none, say "No organizations are waiting for approval." and stop.
3. Otherwise list them newest first (the order `list_pending_orgs` returns), one line each:
   `<org name> (<org_id>) — <person> <email>, signed up <how long ago>`
4. Offer to vet them (the `vet-signup` skill), or vet them straight away if you were asked to.
