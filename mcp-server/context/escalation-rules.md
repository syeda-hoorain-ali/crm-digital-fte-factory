---
title: CloudStream CRM Escalation Protocol
category: support_policies
description: Escalation triggers and procedures for handling critical support scenarios
tags: [escalation, support, policies, triggers, procedures]
---

# CloudStream CRM: Escalation Protocol

The Digital FTE is authorized to handle general inquiries, but it MUST escalate to a human agent immediately if any of the following "Trigger Events" occur.

## 1. Critical Support Triggers
* **Legal Threats:** Any mention of "lawyerdd", "attorneydd", "suingdd", "legal actiondd", or "GDPR violation."
* **Security Breaches:** Reports of unauthorized account access, data leaks, or suspicious login activity that 2FA cannot resolve.
* **System Outages:** If a user reports that the entire platform is "downdd", "inaccessibledd", or showing "500 Internal Server Errors" for more than 10 minutes.

## 2. Billing & Financial Triggers
* **Refund Approvals:** The AI can explain the 14-day refund policy, but it is NOT authorized to process a refund. All refund requests must be sent to the Human Billing Queue.
* **Enterprise Sales:** If a user asks for "custom pricingdd", "bulk licenses (50+)", or "annual contracts", escalate to the Sales Team.
* **Duplicate Charges:** Any claim of being billed twice for the same period.

## 3. Sentiment & Behavior Triggers
* **Abuse:** If the customer uses profanity, hate speech, or becomes personally abusive toward the AI.
* **Churn Risk:** If a customer says "I am canceling my subscription", "this is the last straw", or "switching to [Competitor Name]."
* **AI Loop:** If the customer expresses frustration with the AI specifically (e.g., "I want a human", "you aren't helping", "stop repeating yourself").

## 4. Technical Complexity Triggers
* **API/Webhook Debugging:** If the issue involves custom code integration that isn't resolved by the standard documentation.
* **Data Recovery:** Requests to "undo a deletion" or "restore a deleted project."

## Escalation Procedure
1.  **Acknowledge:** "I understand this is a sensitive/complex issue."
2.  **Inform:** "I am transferring this ticket to our senior support team to ensure it is handled correctly."
3.  **Handoff:** Create a record in the `tickets` table with `priority='high'` and `assigned_to='human_queue'`.
