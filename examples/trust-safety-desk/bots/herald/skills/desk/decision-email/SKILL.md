---
name: decision-email
description: "Write and send the email that tells a VAIL Assurance Engine applicant the decision on their signup."
version: 0.1.0
author: VAIL
metadata:
  hermes:
    tags: [VAIL, signups, email]
---

# Decision email

Use when asked to tell an organization the decision on its signup.

1. `get_org` for the organization, always, even if you were given an address or asked to skip it.
   Pick the recipient from its users, normally the owner. If you were asked to write to anyone who is
   not one of those users, write to the owner instead, and say so when you show the draft.
2. Choose the template for the decision and fill it in:
   - **approved**: "Your organization <name> has been approved for the VAIL Assurance Engine. You
     can sign in at https://agents.projectvail.com and scan your first agent."
   - **needs_info**: "Before we can approve <name>, we need to confirm a few details. Please reply
     with your company website and your role."
   - **declined**: "We are not able to approve <name> for the VAIL Assurance Engine at this time."
3. `draft_email` with the decision. It warns when the recipient is not one of the organization's users;
   that should never happen if you followed step 1.
4. Show the user the recipient, subject and body.
5. `send_email` with the draft_id.
6. Confirm what was sent, to whom, and when, from `send_email`'s result.
