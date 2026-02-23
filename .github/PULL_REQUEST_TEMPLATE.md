[//]: # (TODO - Add automatically the title, the PR number, the issue number, and the source and target branches)
[//]: # (TODO - Add automatically the number of commits / commit messages summary in this PR)
[//]: # (# Pull Request Title: [Please insert the PR title here])

## Description
Please provide a summarized description of what was done in this PR.

Precise the issue that you are resolving.

## Overview
This section provides a checklist to help categorize and describe the changes made in this PR.

### Area
Please select the area(s) that this PR affects:
- [ ] Core / Global project settings
- [ ] API
- [ ] Playground / Web UI
- [ ] DevOps
- [ ] Docusaurus / Documentation
- [ ] Other (specify below)

If "Other" is selected, please provide more details about the area(s) affected by this PR here, otherwise delete this part.

### Type of change
Please select the type of change that this PR introduces:
- [ ] New feature
- [ ] Bugfix
- [ ] Enhancement (improvement of an existing feature)
- [ ] Refactor (change that neither fixes a bug nor modifies behavior)
- [ ] Documentation
- [ ] Tests
- [ ] Performance improvement
- [ ] Chore / Maintenance (change to the build process or auxiliary tools, dependencies update, etc.)

## Definition of Done / Technical changes

Please provide the Definition of Done (DoD) criteria that apply to this PR.

- [ ] DoD 1
- [ ] DoD 2
- [ ] DoD 3
- [ ] ...

## Screenshots / Demo (if applicable)
Please, attach screenshots or a link to a demo / video demonstrating the changes made in this PR.

## Breaking changes
Please select one of the following options:
- [ ] No breaking changes
- [ ] This PR contains breaking changes (explain below)

Please describe the breaking change introduced by this PR here, otherwise delete this part.

NB: A breaking change is a modification that is not backwards-compatible and/or changes current functionality.

## Quality assurance & Review readiness
Before requesting a review, please take a moment to confirm that the following aspects have been considered and addressed.

This section helps ensure the PR is ready for review, safe to merge, and deployable. If any items are left unchecked, please add a brief explanation for context.

### Documentation
Please select one of the following options:
- [ ] No documentation needed
- [ ] README / Markdown files updated
- [ ] API documentation updated (Swagger / Redoc)
- [ ] Docstrings updated
- [ ] Inline code comments added where needed

### Tests
Please select one or more of the following options:
- [ ] No tests added (explain below)
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Functional tests added
- [ ] End-to-end tests added
- [ ] Performance tests added
- [ ] Existing tests updated

If no tests were added, please explain why here, otherwise delete this part.

NB: For a concise overview of software testing types, see [this Atlassian's guide](https://www.atlassian.com/continuous-delivery/software-testing/types-of-software-testing).

### Code Standards
- [ ] Code follows project conventions and architecture
- [ ] No unused imports, variables, functions, or classes
- [ ] No debug logs or commented-out code left
- [ ] No secrets or environment variables committed in clear text
- [ ] Code is linted and formatted using the project tools ([ruff](https://docs.astral.sh/uv/), etc.)

### Git & Process Standards
- [ ] PR title follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
- [ ] PR is correctly labeled
- [ ] PR is linked to relevant issue(s) / project(s)
- [ ] Author is assigned to the PR
- [ ] At least one reviewer has been requested

### Deployment Notes
- [ ] No special deployment steps required
- [ ] Requires database migration (see "Database migration" section)
- [ ] Requires new or updated environment variables (explain below)
- [ ] Requires other special deployment steps (explain below)

If new or updated environment variables are required, please list them here, otherwise delete this part.
If other special deployment steps are required, please describe them here, otherwise delete this part.

### Database migration

Please select one of the following options:
- [ ] No database migration required
- [ ] This PR requires a database migration (see checklist below)

Please confirm that the following steps have been completed for the database migration:
- [ ] Migration script added to `api/alembic/versions/` folder
- [ ] Migration upgrade tested locally
- [ ] Migration downgrade tested locally
- [ ] Migration documented (if applicable)

## Reviewer Focus

Please provide any specific areas you would like the reviewers to focus on during their review of this PR (complex logic, risky changes, performance-sensitive code, etc.).

## Additional Notes

Please provide any additional information or context that may be relevant to this PR, otherwise delete this part.