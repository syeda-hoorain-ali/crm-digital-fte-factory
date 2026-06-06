---
category: troubleshooting
title: Integration Issues and Configuration
tags: [integrations, stripe, slack, troubleshooting, configuration]
---

# Integration Issues and Configuration

CloudStream integrates with popular third-party services to streamline your workflow. This guide covers common integration issues and their solutions.

## Stripe Integration

Stripe integration allows CloudStream to automatically sync invoices and payment information.

### Setting Up Stripe

**Configuration Steps:**
1. Log in to your CloudStream account
2. Navigate to Settings > Billing > Connect Stripe
3. Click "Connect Stripe Account"
4. You'll be redirected to Stripe's authorization page
5. Log in to your Stripe account and authorize CloudStream
6. You'll be redirected back to CloudStream with a success message

### Connection Failed Error

If you see a "Connection Failed" error when trying to connect Stripe:

**Check Permissions:** Ensure you have "Administrator" permissions in your Stripe account. Only Stripe administrators can authorize third-party integrations.

**How to Check Stripe Permissions:**
1. Log in to your Stripe Dashboard
2. Go to Settings > Team
3. Find your user account
4. Verify your role is "Administrator" (not "Developer" or "Analyst")

**Request Admin Access:** If you don't have administrator permissions, ask your Stripe account owner to either:
- Grant you administrator access, or
- Complete the CloudStream integration themselves

### Sync Issues

If invoices aren't syncing properly:

**Manual Sync:** Go to Settings > Billing > Stripe Integration and click "Sync Now"

**Check Webhook Status:** Ensure Stripe webhooks are properly configured. Go to Settings > Billing > Stripe Integration > Advanced and verify the webhook status shows "Active"

**Reconnect:** If sync issues persist, try disconnecting and reconnecting your Stripe account.

## Slack Integration

Slack integration provides real-time notifications when clients interact with your projects.

### Setting Up Slack

**Configuration Steps:**
1. Navigate to Settings > Integrations
2. Find "Slack" in the integrations list
3. Click "Connect Slack"
4. Select the Slack workspace you want to connect
5. Choose which channel should receive notifications
6. Authorize the integration

### Notification Types

CloudStream can send Slack notifications for:

**Client Approvals:** When a client approves a design in ClientBridge
**New Comments:** When a client leaves feedback on a file
**Project Updates:** When project status changes
**Time Tracking:** Daily summary of tracked time (optional)

**Configure Notifications:** Go to Settings > Integrations > Slack > Notification Settings to customize which events trigger Slack messages.

### Troubleshooting Slack

**Not Receiving Notifications:**
- Verify the Slack integration status shows "Connected"
- Check that notifications are enabled for the specific event type
- Ensure the CloudStream bot hasn't been removed from the notification channel
- Check Slack's notification settings (CloudStream notifications might be muted)

**Wrong Channel:** To change the notification channel, disconnect and reconnect the Slack integration, then select the correct channel during setup.
