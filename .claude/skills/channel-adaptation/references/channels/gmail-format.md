# Gmail Format Guide

## Style: Formal & Thorough

Professional, detailed, structured communication for email channel.

## Required Structure

```
Subject: [Brief summary of issue/resolution]

[Greeting]

[Body with clear paragraphs]

[Professional closing]

[Signature]
```

## Required Elements

### 1. Greeting
- "Hello [Customer Name]," (preferred)
- "Dear [Customer Name]," (for formal situations)
- Always use customer's name if available

### 2. Body
- **Clear paragraphs**: 2-4 sentences each
- **Numbered lists**: For multi-step instructions
- **Bullet points**: For feature lists or options
- **Bold important terms**: Use **bold** for action items
- **Include links**: Provide documentation or relevant resources

### 3. Closing
- "Best regards," (standard)
- "Kind regards," (alternative)
- Always include comma

### 4. Signature
- "CloudStream Support Bot" (standard)
- "The CloudStream Team" (alternative)

## Formatting Guidelines

### Paragraphs
- Keep paragraphs focused (one idea per paragraph)
- 2-4 sentences per paragraph
- Use line breaks between paragraphs

### Lists
**Numbered lists** for sequential steps:
```
1. Navigate to Settings > API Keys
2. Click "Regenerate Token"
3. Copy the new token
```

**Bullet points** for non-sequential items:
```
- Feature A is available on Pro plan
- Feature B requires Enterprise tier
- Feature C is included in all plans
```

### Links
- Always provide functional links
- Use descriptive link text: "upgrade here" not "click here"
- Include documentation links when relevant

## Complete Examples

### Example 1: Technical Issue Resolution

**Raw Response**:
"The Slack integration isn't syncing because the OAuth token expired. You need to reconnect your Slack workspace from the integrations page."

**Gmail Format**:
```
Subject: Slack Integration Sync Issue Resolved

Hello Sarah,

I've identified the issue with your Slack integration. The OAuth token has expired, which is preventing messages from syncing to your CloudStream workspace.

Here's how to reconnect:

1. Go to Settings > Integrations
2. Find "Slack" in your connected apps
3. Click "Reconnect Workspace"
4. Authorize CloudStream in the Slack popup

Once reconnected, your messages will sync automatically within 2-3 minutes. Historical messages from the past 7 days will also be imported.

If you continue to experience sync issues after reconnecting, please let me know and I'll escalate this to our technical team.

Best regards,
CloudStream Support Bot
```

### Example 2: Feature Request

**Raw Response**:
"The Gantt chart feature is only available on Professional and Enterprise plans. You're currently on the Starter plan. You can upgrade to access this feature."

**Gmail Format**:
```
Subject: Gantt Chart Feature Access

Hello Marcus,

Thank you for your interest in the Gantt chart feature. This feature is available on our Professional and Enterprise plans.

Your current Starter plan includes:
- Basic project timelines
- Task lists and dependencies
- Calendar view

To access Gantt charts, you can upgrade here: [upgrade link]

Once upgraded, the Gantt chart will appear in your Project Timeline view:
1. Navigate to your project dashboard
2. Click "Timeline" in the left sidebar
3. Select "Gantt View" from the dropdown

The Professional plan also includes advanced reporting, custom fields, and priority support. Let me know if you have any questions about the upgrade process.

Best regards,
CloudStream Support Bot
```

### Example 3: Urgent Issue with Empathy

**Raw Response**:
"Your project data is safe. The export failed due to a temporary server issue. I've manually triggered the export and it should complete in 5 minutes. You'll receive an email with the download link."

**Gmail Format**:
```
Subject: Project Export Issue Resolved - Data Safe

Hello Alex,

I understand how concerning this must be, especially with your client presentation coming up. I want to assure you that your project data is completely safe.

The export failure was caused by a temporary server issue on our end (now resolved). I've manually triggered your export, and it should complete within the next 5 minutes.

You'll receive an email at alex@agency.com with a secure download link. The export will include:
- All project files and assets
- Complete task history
- Team member comments
- Timeline data

If you don't receive the email within 10 minutes, please reply to this message and I'll investigate immediately. I've also flagged your account for priority monitoring to prevent this from happening again.

Best regards,
CloudStream Support Bot
```

## Edge Cases

### Long Technical Explanations
- Break into multiple paragraphs
- Use subheadings if needed (## Subheading)
- Provide summary at the top, details below

### Multiple Issues in One Message
- Address each issue in separate paragraphs
- Use headers to separate issues:
```
**Issue 1: Slack Integration**
[explanation]

**Issue 2: Export Functionality**
[explanation]
```

### Customer Used Technical Terms
- Mirror their language level
- If they say "API endpoint", you can use "endpoint"
- If they say "connection", use "connection" not "endpoint"

### First Contact vs Follow-up
**First contact**: More formal greeting
```
Hello [Name],

Thank you for contacting CloudStream support.
```

**Follow-up**: Acknowledge previous conversation
```
Hello [Name],

Thank you for following up on your Slack integration issue.
```

## Tone Adjustments by Situation

| Situation | Tone Adjustment |
|-----------|----------------|
| **Urgent/Blocking** | Lead with empathy: "I understand this is urgent..." |
| **Data Loss Concern** | Immediate reassurance: "Your data is safe..." |
| **Confusion** | Acknowledge: "I can see why this would be confusing..." |
| **Frustration** | Appreciate patience: "I appreciate your patience..." |
| **Feature Request** | Positive: "That's a great suggestion..." |

## Validation Checklist

Before sending Gmail response:
- [ ] Subject line present and descriptive
- [ ] Greeting with customer name
- [ ] Clear paragraph structure (2-4 sentences each)
- [ ] Numbered lists for sequential steps
- [ ] Bullet points for non-sequential items
- [ ] Important terms bolded
- [ ] Links included where relevant
- [ ] Professional closing ("Best regards,")
- [ ] Signature ("CloudStream Support Bot")
- [ ] Empathetic tone applied
- [ ] Proactive next steps included
- [ ] No forbidden language ("I am just an AI", "I don't know")
- [ ] Jargon replaced with user-friendly terms
