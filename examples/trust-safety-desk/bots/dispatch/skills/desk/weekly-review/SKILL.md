---
name: weekly-review
description: "Run the desk's onboarding review: vet pending signups with Martin, check abuse with Ledger, then have Herald send the decisions the user makes."
version: 0.1.0
author: VAIL
metadata:
  hermes:
    tags: [VAIL, signups, coordination]
---

# Weekly onboarding review

Use when asked for the onboarding review, or to "go through the signups".

1. Ask **Martin** to list the pending organizations and vet each one, with a verdict and a
   recommendation per organization.
2. At the same time, ask **Ledger** for usage over the last 24 hours, by organization and by user,
   with every account that crosses a threshold or splits usage across organizations.
3. When both have answered, give the user one table: organization, Martin's verdict and
   recommendation, anything Ledger flagged about it. Then list Ledger's flags on active accounts.
4. Ask the user to decide for each pending organization: approve, decline, or ask for more
   information.
5. For the decisions the user made, ask **Herald** to email each applicant, one message per
   organization, naming the decision.
6. Report what Herald sent.
