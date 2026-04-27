[//]: # (TODO - Add automatically the title, the PR number, the issue number, and the source and target branches)
[//]: # (TODO - Add automatically the number of commits / commit messages summary in this PR)
[//]: # (# Pull Request Title: [Please insert the PR title here])

## Overview

*Please precise the issue that you are resolving and provide a summarized description of what was done in this PR. Then provide the Definition of Done (DoD) criteria that apply to this PR:*

- [ ] DoD 1
- [ ] DoD 2
- [ ] DoD 3
- [ ] ...

**Breaking changes:**

- [ ] No breaking changes
- [ ] This PR contains breaking changes (explain below)

## Check lists

### Review checklist

*Before requesting a review, please take a moment to confirm that the following aspects have been considered and addressed. This section helps ensure the PR is ready for review, safe to merge, and deployable. If any items are left unchecked, please add a brief explanation for context.*

- [ ] Updated or added documentation
- [ ] Updated or added unit tests
- [ ] Updated or added integration tests
- [ ] No debug logs or commented-out code left
- [ ] No secrets or environment variables committed in clear text
- [ ] Code is linted and formatted using the project pre-commit hooks


**If [`api/sql/models.py`](https://github.com/etalab-ia/OpenGateLLM/blob/main/api/sql/models.py) has been modified, please confirm that the following steps have been completed:**
- [ ] Alembic migration has been generated
- [ ] Alembic migration upgrade has been tested locally
- [ ] Alembic migration downgrade has been tested locally

## Deployment checklist

For each of the following items, please confirm if the PR concerns the deployment of the changes:

- [ ] Alembic migration has been generated
- [ ] Configuration file has been modified
- [ ] Environment variables have been modified

*If new or updated environment variables are required, please list them here, otherwise delete this part. If other special deployment steps are required, please describe them here, otherwise delete this part.*

## Additional Notes

*Please provide any additional information or context that may be relevant to this PR, otherwise delete this part. This could be any specific areas you would like the reviewers to focus on during their review of this PR (complex logic, risky changes, performance-sensitive code, etc.)*