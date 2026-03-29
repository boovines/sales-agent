---
name: review
description: "Review current code changes like a principal-level engineer. Covers architecture, correctness, style, and consistency. Use when the user says \"review\", \"review my code\", \"code review\", or wants feedback on their current changes."
---

# Code Review

**Run as subagent.** Immediately spawn a Task agent (subagent_type: "general-purpose") with the full instructions below and the arguments `${ARGUMENTS:-}`. Pass the CLAUDE.md and app-specific CLAUDE.md content as context by telling the subagent to read them. Display the agent's returned review to the user verbatim — do not summarize or editorialize.

---

Review the current branch's changes as a principal-level engineer who cares about both the forest and the trees.

First, read any CLAUDE.md files in the project root and subdirectories to understand this repo's conventions.

## Scope

Determine what to review based on arguments:

- **No arguments (default)**: All changes vs main — unstaged, staged, AND committed-but-not-merged. This is the full picture of what would land in a PR.
- **`unstaged`**: Only unstaged working tree changes.
- **`staged`**: Only staged changes.
- **`committed`**: Only commits not yet on main (excludes working tree changes).

## Steps

### 0. Fetch latest main

```bash
git fetch origin main
```

This ensures all comparisons reflect the current state of main on the remote.

### 1. Gather the diff

Based on scope, run the appropriate commands:

**Default (everything vs main):**

```bash
# Combined diff: working tree + staged + committed, all vs main
git diff origin/main...HEAD
git diff HEAD
git log origin/main..HEAD --oneline
```

If `git diff HEAD` is empty and `git diff origin/main...HEAD` is also empty, tell the user there are no changes to review and stop.

**Unstaged only:**

```bash
git diff
```

**Staged only:**

```bash
git diff --staged
```

**Committed only:**

```bash
git diff origin/main...HEAD
git log origin/main..HEAD --oneline
```

Also run `git diff --stat origin/main...HEAD` (or the equivalent for the chosen scope) to get a high-level summary of files changed.

### 2. Read changed files in full

For every file that appears in the diff, read the full current version of the file (not just the diff hunks). You need full file context to judge architecture, naming patterns, and how the change fits into the surrounding code.

If more than 15 files changed, prioritize:
1. New files (most important to review thoroughly)
2. Files with the largest diffs
3. Test files (verify they're testing behavior, not implementation)

### 3. Understand the intent

Before writing any feedback, silently answer these questions:

- What is this change trying to accomplish? (there may be multiple goals)
- What are the distinct logical units of work?
- Does the scope make sense, or is it mixing unrelated concerns?
- Are there any changes that seem accidental or unintentional?

### 4. Produce the review

Structure the review in these sections. Skip any section that has nothing to report.

---

**Overview** (2-4 sentences)

What the change does and whether the approach is sound. State the distinct goals you identified.

---

**Architecture & Design**

Big-picture feedback. Examples of what to look for:

- Does the change respect the layered architecture? (routes -> services -> int -> utils)
- Are responsibilities in the right layer? (business logic in services, not routes)
- Is workspace isolation maintained? (workspace_id denormalization, composite FKs, RLS)
- Are new tables registered in models_registry.py?
- Does the frontend use server actions instead of direct API calls?
- Is there unnecessary coupling between modules?
- Are there missing abstractions — or premature abstractions?
- Does pagination use cursor-based `PaginatedResponse`?

---

**Correctness & Safety**

Bugs, edge cases, and security issues. Examples:

- Race conditions, missing null checks, off-by-one errors
- SQL injection, XSS, command injection, or other OWASP top 10
- Missing error handling at system boundaries
- Swallowed exceptions that will cause silent failures
- Missing workspace_id filtering (cross-tenant data leak risk)

---

**Testing**

Evaluate test quality and TDD compliance:

- Do tests exist for all new logic? (they MUST)
- Do tests define behavior or just mirror implementation?
- Are error paths and edge cases covered?
- Are fixtures named with `_fixture` suffix?
- Are mock paths correct after any refactoring?

---

**Style & Consistency**

Line-level nits in the context of THIS repo's conventions:

- **Python**: No nested functions. No type aliases for Response types. Full type annotations. `USQRouter` not `APIRouter`. `Transaction` not `AsyncSession`. Fixtures end with `_fixture`. No inline imports.
- **TypeScript/React**: Design system colors (surface-100, content-100, etc.), not hardcoded. Icons from lucide-react. `"use client"` has comment. No className outside app/ui/. Server actions for API calls. `LocalTime` for datetime display. snake_case API types used directly.
- **General**: No `eslint-disable` without explanation. No `type: ignore` (use runtime assertions). Money as strings with `_usd` suffix.
- Naming consistency with surrounding code
- Unnecessary comments or missing comments where logic is non-obvious
- Dead code, unused imports, leftover debug statements

---

**Nitpicks** (optional)

Minor suggestions that aren't blocking. Prefix each with "nit:" so they're clearly low-priority.

---

### 5. Prune pass

Before writing your final output, re-read every item in your draft review and **delete** any item that:

- Just says something "looks good", "is fine", "is well-structured", or "is correct" without identifying a problem. Compliments waste the reader's time.
- Describes a potential concern but then immediately dismisses it ("this is a race condition, but the window is small and consequences are minor, so it's acceptable"). If you wouldn't ask someone to change it, don't mention it.
- Points out a pattern or fact without a concrete action ("noting the dependency is well-handled"). If there's nothing to do, cut it.
- Restates what the code does without identifying an issue. The author already knows what their code does.

After pruning, if a section is empty, remove the section entirely. If ALL sections are empty, the review is: "No issues found."

The goal: every item that survives is something the author should either fix or consciously decide not to fix. Zero filler.

### 6. Format

- Use `file_path:line_number` references so the user can jump to each issue.
- Group feedback by file when there are many issues in one file.
- For each issue, briefly explain the "why" — don't just state the rule, explain the consequence of violating it.
- If the code is clean, say so. Don't manufacture feedback. A short "No issues found" is a valid review.
