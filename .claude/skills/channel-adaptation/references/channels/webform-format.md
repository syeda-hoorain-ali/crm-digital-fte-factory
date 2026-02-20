# Web Form Format Guide

## Style: Direct & Functional

Neutral, ultra-clear, informative communication for web form channel.

## Required Structure

```
**[Header]**

[Direct answer with clear formatting]

[Call-to-action]
```

## Required Elements

### 1. Confirmation (Optional)
Brief acknowledgment if needed:
- "Issue resolved"
- "Request received"
- Usually skip for direct answers

### 2. Body
- **Direct answer**: Get straight to the point
- **Markdown formatting**: Use headers, bold, bullets
- **Clear structure**: Organize with headers and lists
- **Functional language**: Neutral, informative tone

### 3. Call-to-Action (Required)
Always end with:
- "Was this helpful?" (standard)
- "Let us know if you have further questions." (alternative)
- "Need more help? Contact us here: [link]" (with escalation option)

## Formatting Guidelines

### Markdown Elements

**Headers**:
```markdown
**Main Header** (bold for primary header)
## Secondary Header (for subsections)
```

**Bold**:
```markdown
**important term** or **action item**
```

**Bullet Points**:
```markdown
- Item 1
- Item 2
- Item 3
```

**Numbered Lists**:
```markdown
1. First step
2. Second step
3. Third step
```

**Links**:
```markdown
[descriptive text](URL)
```

### Structure Patterns

**Simple Answer**:
```
**[Topic]**

[Direct answer in 1-2 sentences]

**Was this helpful?**
```

**Multi-Step Instructions**:
```
**[Topic]**

[Brief explanation]

**Steps:**
1. Step one
2. Step two
3. Step three

**Was this helpful?**
```

**Multiple Options**:
```
**[Topic]**

[Brief explanation]

**Option 1:** [Description]
**Option 2:** [Description]

**Was this helpful?**
```

## Complete Examples

### Example 1: Technical Issue Resolution

**Raw Response**:
"The Slack integration isn't syncing because the OAuth token expired. You need to reconnect your Slack workspace from the integrations page. Go to Settings > Integrations, find Slack, and click Reconnect Workspace."

**Web Form Format**:
```
**Slack Integration Sync Issue**

Your OAuth token has expired, preventing messages from syncing.

**Resolution Steps:**
1. Navigate to Settings > Integrations
2. Find "Slack" in your connected apps
3. Click "Reconnect Workspace"
4. Authorize CloudStream in the Slack popup

Messages will sync automatically within 2-3 minutes after reconnecting.

**Was this helpful?** Let us know if you have further questions.
```

### Example 2: Feature Request

**Raw Response**:
"The Gantt chart feature is only available on Professional and Enterprise plans. You're currently on the Starter plan. You can upgrade to access this feature. Once upgraded, it will appear in your Project Timeline view."

**Web Form Format**:
```
**Gantt Chart Feature Access**

The Gantt chart feature is available on Professional and Enterprise plans. Your current Starter plan does not include this feature.

**To access Gantt charts:**
- Upgrade to Professional plan: [upgrade link]
- Navigate to Project Timeline
- Select "Gantt View" from the dropdown

**Current plan includes:**
- Basic project timelines
- Task lists and dependencies
- Calendar view

**Was this helpful?** Contact us if you need assistance with upgrading.
```

### Example 3: Urgent Issue with Empathy

**Raw Response**:
"Your project data is safe. The export failed due to a temporary server issue. I've manually triggered the export and it should complete in 5 minutes. You'll receive an email with the download link."

**Web Form Format**:
```
**Project Export Issue Resolved**

Your project data is completely safe. The export failure was caused by a temporary server issue (now resolved).

**Status:**
- Export manually triggered
- Completion time: ~5 minutes
- Download link will be sent to: your-email@example.com

**Export includes:**
- All project files and assets
- Complete task history
- Team member comments
- Timeline data

**Was this helpful?** If you don't receive the email within 10 minutes, please contact us immediately.
```

### Example 4: Multiple Issues

**Raw Response**:
"I've resolved both issues. The Slack integration is now reconnected and syncing. For the export issue, I've manually triggered it and you'll receive the download link via email in 5 minutes."

**Web Form Format**:
```
**Issues Resolved**

Both issues have been addressed:

## Slack Integration
- Status: Reconnected and syncing
- Messages will sync within 2-3 minutes
- Historical messages from past 7 days will be imported

## Project Export
- Status: Manually triggered
- Completion time: ~5 minutes
- Download link will be sent via email

**Was this helpful?** Let us know if you experience any further issues.
```

### Example 5: Feature Comparison

**Raw Response**:
"You have two options: Upgrade to Professional plan for $49/month to access Gantt charts, or use the Timeline view which is included in your current plan and provides similar functionality."

**Web Form Format**:
```
**Gantt Chart Access Options**

**Option 1: Upgrade to Professional**
- Cost: $49/month
- Includes: Gantt charts, advanced reporting, custom fields
- Upgrade here: [link]

**Option 2: Use Timeline View (Current Plan)**
- Cost: Free (included in Starter plan)
- Features: Basic timeline visualization, task dependencies
- Access: Project Dashboard > Timeline

**Feature Comparison:**
| Feature | Timeline View | Gantt Chart |
|---------|--------------|-------------|
| Task visualization | ✓ | ✓ |
| Dependencies | ✓ | ✓ |
| Critical path | ✗ | ✓ |
| Resource allocation | ✗ | ✓ |
| Export to PDF | ✗ | ✓ |

**Was this helpful?** Contact us if you need help deciding.
```

## Edge Cases

### Long Technical Explanations
**Structure with collapsible sections or provide link**:
```
**[Topic]**

[Brief summary]

**Quick Fix:**
[Immediate solution]

**Detailed Explanation:**
For complete technical details, see our guide: [link]

**Was this helpful?**
```

### Multiple Issues in One Message
**Use headers to separate**:
```
**Multiple Issues Addressed**

## Issue 1: [Name]
[Resolution]

## Issue 2: [Name]
[Resolution]

**Was this helpful?**
```

### Customer Used Technical Terms
**Mirror their language level**:
```
Customer: "My API endpoint is returning 401 errors"
Response:
**API Authentication Error**

Your API endpoint is returning 401 errors due to an expired authentication token.

**Resolution:**
1. Regenerate token in Settings > API Keys
2. Update your endpoint configuration
3. Test the endpoint

**Was this helpful?**
```

### No Clear Solution Available
**Provide escalation path**:
```
**[Issue Name]**

This issue requires further investigation by our technical team.

**Next Steps:**
- Your request has been escalated (Ticket #12345)
- Technical team will respond within 24 hours
- You'll receive updates via email

**In the meantime:**
[Workaround if available]

**Need immediate assistance?** Contact us at support@cloudstream.com
```

## Tone Adjustments by Situation

| Situation | Web Form Approach |
|-----------|------------------|
| **Urgent/Blocking** | Lead with "**Urgent Issue Resolved**" header |
| **Data Loss Concern** | Start with "Your data is safe" in first sentence |
| **Confusion** | Use clear headers and step-by-step instructions |
| **Frustration** | Acknowledge briefly, focus on solution |
| **Feature Request** | Present options in structured format with comparison |

## Formatting Best Practices

### Use Headers for Organization
```
**Main Topic**

## Subtopic 1
[Content]

## Subtopic 2
[Content]
```

### Use Tables for Comparisons
```
| Feature | Plan A | Plan B |
|---------|--------|--------|
| Item 1  | ✓      | ✓      |
| Item 2  | ✗      | ✓      |
```

### Use Bullet Points for Lists
```
**Features included:**
- Feature A
- Feature B
- Feature C
```

### Use Numbered Lists for Steps
```
**Setup Instructions:**
1. First step
2. Second step
3. Third step
```

### Use Bold for Emphasis
```
**Important:** This action cannot be undone.
**Note:** Changes take effect immediately.
```

## Common Patterns

### Status Update
```
**[Issue Name]**

**Status:** Resolved

**Details:**
[Explanation]

**Was this helpful?**
```

### How-To Guide
```
**How to [Action]**

**Steps:**
1. Step one
2. Step two
3. Step three

**Additional Resources:**
- [Link to documentation]
- [Link to video tutorial]

**Was this helpful?**
```

### Feature Availability
```
**[Feature Name]**

**Availability:** [Plan level]

**To access this feature:**
- [Upgrade instructions or access path]

**Alternative options:**
- [Other features that might help]

**Was this helpful?**
```

### Error Resolution
```
**[Error Name]**

**Cause:** [Brief explanation]

**Resolution:**
1. [Step one]
2. [Step two]
3. [Step three]

**Prevention:**
[How to avoid this in future]

**Was this helpful?**
```

## Validation Checklist

Before sending Web Form response:
- [ ] Direct and functional tone (not too casual, not too formal)
- [ ] Clear header present
- [ ] Markdown formatting applied correctly
- [ ] Structured with headers/bullets/numbered lists
- [ ] CTA included ("Was this helpful?" or similar)
- [ ] Links functional and relevant
- [ ] No unnecessary filler or preamble
- [ ] Empathetic acknowledgment (if applicable)
- [ ] Proactive next steps included
- [ ] No forbidden language
- [ ] Jargon replaced with user-friendly terms
- [ ] Information organized logically
- [ ] Easy to scan and read quickly

## Accessibility Considerations

### Use Semantic Markdown
- Headers create proper document structure
- Lists are properly formatted
- Links have descriptive text (not "click here")

### Keep It Scannable
- Short paragraphs (2-3 sentences max)
- Bullet points for easy scanning
- Bold for important terms
- White space between sections

### Provide Context
- Don't assume user saw previous messages
- Include all necessary information
- Provide links to additional resources

## Common Mistakes to Avoid

❌ **Too casual**: "Hey! So here's the deal..."
✅ **Correct**: "**Issue Resolved** Your authentication..."

❌ **Too verbose**: Long paragraphs without structure
✅ **Correct**: Short paragraphs with headers and bullets

❌ **Missing CTA**: Ending without "Was this helpful?"
✅ **Correct**: Always include CTA at the end

❌ **Poor formatting**: Plain text without Markdown
✅ **Correct**: Use headers, bold, bullets, lists

❌ **Unclear structure**: Information scattered randomly
✅ **Correct**: Logical flow with clear sections

## Word Count Guidelines

Unlike WhatsApp, Web Form has no strict word limit, but:
- **Keep it concise**: Don't ramble
- **Be thorough**: Include all necessary information
- **Use structure**: Break up long content with headers
- **Provide links**: For very detailed explanations

**Ideal length**: 50-150 words for simple issues, 150-300 words for complex issues
