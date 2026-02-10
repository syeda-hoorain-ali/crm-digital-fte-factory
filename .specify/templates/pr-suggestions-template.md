---
description: "Template for tracking and applying PR code review suggestions"
---

# PR #<PR_NUMBER> - Code Review Suggestions

**PR URL**: https://github.com/<GITHUB_USER>/<REPO_NAME>/pull/<PR_NUMBER>
**Branch**: `<BRANCH_NAME>`
**Generated**: <TIMESTAMP>
**Status**: ⏳ In Progress

---

## Overview

This document tracks code review suggestions from PR #<PR_NUMBER>. Each suggestion is marked with a checkbox and processed sequentially. Once all suggestions are applied, changes are committed and pushed back to the PR.

**Statistics:**
- **Total Suggestions**: <TOTAL_COUNT>
- **By Reviewer**:
  - <REVIEWER_1>: <COUNT_1> suggestions
  - <REVIEWER_2>: <COUNT_2> suggestions
- **Completed**: 0 / <TOTAL_COUNT>
- **Remaining**: <TOTAL_COUNT>

---

## Suggestions

### Suggestion S001
- [ ] **S001** Line <LINE_NUMBER> - @<REVIEWER_USERNAME>

**Suggestion:**
<SUGGESTION_BODY>

**Context:**
- **File**: `<FILE_PATH>`
- **Line**: <LINE_NUMBER>
- **Comment ID**: <COMMENT_ID>
- **Priority**: 🔴 High / 🟡 Medium / 🟢 Low

**Resolution Notes:**
<!-- Add notes here after applying the suggestion -->

---

### Suggestion S002
- [ ] **S002** Line <LINE_NUMBER> - @<REVIEWER_USERNAME>

**Suggestion:**
<SUGGESTION_BODY>

**Context:**
- **File**: `<FILE_PATH>`
- **Line**: <LINE_NUMBER>
- **Comment ID**: <COMMENT_ID>
- **Priority**: 🔴 High / 🟡 Medium / 🟢 Low

**Resolution Notes:**
<!-- Add notes here after applying the suggestion -->
---

## Final Summary

**Status**: ⏳ In Progress

**Completion Status:**
- [X] Suggestions fetched from PR
- [ ] All suggestions reviewed
- [ ] Changes applied to codebase
- [ ] Changes committed locally
- [ ] Changes pushed to remote
- [ ] Tracking file updated

**Skipped/Rejected:**
- None

**Commit Details:**
- **Commit Hash**: `<COMMIT_HASH>` (will be filled after commit)
- **Commit Message**: (will be filled after commit)
  ```
  <COMMIT_MESSAGE>
  ```

---

## Notes

<!-- Add any additional notes, concerns, or observations here -->

**Reviewers:**
<REVIEWER_LIST>
