# AI implement — oh-my-pi + graphify

You are running headlessly in GitHub Actions for OpenGateLLM.

**Issue:** #{{ISSUE_NUMBER}} — {{ISSUE_TITLE}}
**Author:** @{{ISSUE_AUTHOR}}
**Triggered by label:** `ai-implement`
**Repository:** {{REPO}}
**Base branch:** {{BASE_BRANCH}}
**Working branch (create/use):** `{{BRANCH_NAME}}`

## Issue body

{{ISSUE_BODY}}

## Goal

Resolve this issue end-to-end and open a pull request. Use the keyword **workflowz** so you build a deterministic multi-subagent workflow, and **ultrathink** for careful reasoning.

## Mandatory pipeline

### 1) Graphify context

- Prefer querying the existing knowledge graph under `graphify-out/` before broad file searches.
- Useful commands:
  - `graphify query "<question about the issue>"`
  - `graphify explain "<symbol or concept>"`
  - `graphify path "<from>" "<to>"`
- If the graph is missing or clearly stale for needed paths, rebuild with:
  - `graphify . --no-viz`
- Ground the plan in graph facts (files, symbols, call/import edges). Quote `source_location` when citing.

### 2) Plan

- Enter / use plan mode. Produce a concrete implementation plan with:
  - scope and non-goals
  - files/modules to touch (from graphify)
  - step-by-step todos
  - test strategy (unit and/or integration under `api/tests/`)
  - risks / migrations / config impact
- Keep the plan proportional to the issue. Do not over-engineer.

### 3) Implement with subagents

- After the plan is approved (auto in this CI run), execute it with subagents via the `task` / workflow tools.
- Parallelize independent work; keep sequential barriers for dependent steps.
- Follow existing project patterns (clean architecture in `api/`, pytest layout, pre-commit expectations).
- Prefer focused diffs. Do not refactor unrelated code.
- Do not commit secrets, `.env`, or generated junk (`graphify-out/`, `.venv`, coverage artifacts).

### 4) Review

- Run a dedicated review pass (subagent or workflow stage) against the diff:
  - correctness vs issue acceptance criteria
  - tests added/updated when behavior changes
  - no debug leftovers / commented-out code
  - Alembic migration checklist if `api/sql/models.py` changed
  - lint/format sanity (`ruff`/`pre-commit` if available; otherwise fix obvious issues)
- Fix review findings before opening the PR.

### 5) Git + Pull Request

1. Ensure you are on branch `{{BRANCH_NAME}}` (create from `{{BASE_BRANCH}}` if needed).
2. Stage only relevant source changes.
3. Commit with a conventional message referencing the issue, e.g. `fix: … (#{{ISSUE_NUMBER}})` or `feat: … (#{{ISSUE_NUMBER}})`.
4. Push the branch to `origin`.
5. Create a PR with `gh pr create` (or the github tool) targeting `{{BASE_BRANCH}}`.
6. **PR body MUST follow `.github/PULL_REQUEST_TEMPLATE.md` exactly** — fill every section honestly:
   - Overview + DoD checkboxes relevant to this change
   - Breaking changes
   - Review checklist
   - Models/Alembic checklist when applicable
   - Deployment checklist
   - Additional notes (link the issue with `Fixes #{{ISSUE_NUMBER}}` or `Closes #{{ISSUE_NUMBER}}`)
7. Leave unchecked items unchecked when not done; briefly explain why in Additional Notes if needed.

## Constraints

- Only work needed to resolve #{{ISSUE_NUMBER}}.
- Do not remove the `ai-implement` label.
- Do not merge the PR.
- If the issue is ambiguous or blocked (missing product decision, credentials, external system), stop after posting a clear comment on the issue explaining what is blocked — do not open an empty/junk PR.
- When finished successfully, comment on the issue with the PR URL and a short summary of what changed.

## Success criteria

- Branch pushed
- PR opened with filled PR template
- Issue linked from the PR
- Implementation addresses the issue (or a clear blocked comment if not possible)
