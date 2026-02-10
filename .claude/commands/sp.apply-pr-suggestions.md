---
description: Fetch and apply code review suggestions from a GitHub PR, track progress in a suggestions file, and push changes back
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). Expected format: `<pr-number>` or leave empty to auto-detect.

## Outline

1. **Detect Repository Information**:
   ```bash
   # Get remote URL
   git remote get-url origin

   # Parse username and repo from URL
   # Format: https://github.com/<username>/<repo>.git
   # or: git@github.com:<username>/<repo>.git
   ```

   Extract `GITHUB_USER` and `REPO_NAME` from the remote URL.

2. **Determine PR Number**:
   - **If user provided PR number** in `$ARGUMENTS`: Use that number
   - **If no PR number provided**: Auto-detect from current branch:
     ```bash
     # Get current branch
     CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

     # Find PR for this branch
     gh pr list --head "$CURRENT_BRANCH" --json number --jq '.[0].number'
     ```

   Store as `PR_NUMBER`.

3. **Fetch PR Suggestions**:
   ```bash
   gh api "repos/$GITHUB_USER/$REPO_NAME/pulls/$PR_NUMBER/comments" \
     --jq '.[] | {path: .path, line: .line, body: .body, user: .user.login, id: .id}'
   ```

   Parse the JSON output and store all suggestions.

4. **Filter Bot Suggestions** (optional - based on user preference):
   - If user wants only specific bot (e.g., "gemini-code-assist"), filter by `user.login`
   - Default: Include all review comments

   Example filter:
   ```bash
   gh api "repos/$GITHUB_USER/$REPO_NAME/pulls/$PR_NUMBER/comments" \
     --jq '.[] | select(.user.login == "gemini-code-assist") | {path: .path, line: .line, body: .body, user: .user.login, id: .id}'
   ```

5. **Determine Feature Directory**:
   ```bash
   # Get current branch to find feature directory
   CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

   # Feature directory is specs/<branch-name>
   FEATURE_DIR="specs/$CURRENT_BRANCH"

   # Create directory if it doesn't exist
   mkdir -p "$FEATURE_DIR"
   ```

6. **Generate tasks.md**: Use `.specify.specify/templates/tasks-template.md

6. **Create PR Suggestions Tracking File**:
   - Create file: `$FEATURE_DIR/pr-suggestions.md`
   - Use `.specify/templates/pr-suggestions-template.md` as structure,
   - Fill it with correct details

7. **Apply Suggestions One by One**:

   For each suggestion in the tracking file:

   a. **Read the suggestion details**:
      - File path
      - Line number
      - Suggestion body
      - Reviewer username

   b. **Analyze the suggestion**:
      - Read the current file content
      - Understand the context around the specified line
      - Determine what change is being suggested

   c. **Apply the change**:
      - Open the file at the specified path
      - Make the necessary code changes
      - Ensure the change maintains code quality and doesn't break functionality

   d. **Mark as completed**:
      - Update the tracking file: Change `- [ ]` to `- [X]` for this suggestion
      - Write the updated tracking file to disk

   e. **Report progress**:
      ```text
      ✅ Applied suggestion S001 in <file-path> (Line <line>)
      ```

8. **Validate Changes**:
   - After applying all suggestions, review the changes:
     ```bash
     git status
     git diff
     ```
   - Check if any files have syntax errors or issues
   - If tests exist, optionally run them (ask user first)

9. **Commit and Push Changes**:

   a. **Stage all changes**:
      ```bash
      git add .
      ```

   b. **Generate commit message**:
      ```text
      fix: apply PR #<PR_NUMBER> code review suggestions

      Applied <count> code review suggestions from:
      - <reviewer-1>: <count> suggestions
      - <reviewer-2>: <count> suggestions

      Changes include:
      - <file-1>: <brief-description>
      - <file-2>: <brief-description>

      See pr-suggestions.md for details.
      ```

   c. **Commit**:
      ```bash
      git commit -m "<generated-message>"
      ```

   d. **Push to remote**:
      ```bash
      git push origin
      ```

10. **Update PR Tracking File Status**:
    - Update `pr-suggestions.md`:
      - Change status from "In Progress" to "Completed"
      - Update summary counts

11. **Final Report**:
    ```text
    ✅ PR Code Review Suggestions Applied Successfully

    📊 Summary:
      • PR Number: #<PR_NUMBER>
      • Total Suggestions: <count>
      • Applied: <count>
      • Failed: <count> (if any)
      • Tracking File: <path>/pr-suggestions.md

    📝 Changes Committed:
      • Commit: <commit-hash>
      • Files Modified: <count>

    🚀 Changes Pushed:
      • Branch: <branch-name>
      • Remote: origin

    🔗 View PR: https://github.com/<user>/<repo>/pull/<PR_NUMBER>
    ```

## Error Handling

- **If gh CLI not installed**: Provide manual instructions with direct API curl commands
- **If PR not found**: Show available PRs and ask user to specify
- **If no suggestions found**: Report and exit gracefully
- **If file doesn't exist**: Report which suggestion failed and continue with others
- **If git push fails**: Provide manual push instructions and report partial completion

## Advanced Options (Optional - based on user input)

- `--bot <bot-name>`: Filter suggestions by specific bot (e.g., "gemini-code-assist")
- `--auto-commit`: Skip manual review, apply all and commit automatically
- `--dry-run`: Show what would be applied without making changes
- `--file <file-path>`: Only apply suggestions for specific file

---

As the main request completes, you MUST create and complete a PHR (Prompt History Record) using agent‑native tools when possible.

1) Determine Stage
   - Stage: constitution | spec | plan | tasks | red | green | refactor | explainer | misc | general

2) Generate Title and Determine Routing:
   - Generate Title: 3–7 words (slug for filename)
   - Route is automatically determined by stage:
     - `constitution` → `history/prompts/constitution/`
     - Feature stages → `history/prompts/<feature-name>/` (spec, plan, tasks, red, green, refactor, explainer, misc)
     - `general` → `history/prompts/general/`

3) Create and Fill PHR (Shell first; fallback agent‑native)
   - Run: `.specify/scripts/bash/create-phr.sh --title "<title>" --stage <stage> [--feature <name>] --json`
   - Open the file and fill remaining placeholders (YAML + body), embedding full PROMPT_TEXT (verbatim) and concise RESPONSE_TEXT.
   - If the script fails:
     - Read `.specify/templates/phr-template.prompt.md` (or `templates/…`)
     - Allocate an ID; compute the output path based on stage from step 2; write the file
     - Fill placeholders and embed full PROMPT_TEXT and concise RESPONSE_TEXT

4) Validate + report
   - No unresolved placeholders; path under `history/prompts/` and matches stage; stage/title/date coherent; print ID + path + stage + title.
   - On failure: warn, don't block. Skip only for `/sp.phr`.


5) Commit this update:
   ```bash
   git add .
   git commit -m "docs: <commit message>"
   git push origin
   ```
