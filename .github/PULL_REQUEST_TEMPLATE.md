<!-- Title: the conventional commit title of the change, e.g. "fix(key): stop rejecting keys that contain sk- after the prefix" -->

## Overview

Closes #

<!-- Describe what this PR does and why, then the Definition of Done (DoD) criteria that apply to it. -->

- [ ] DoD 1
- ...

## Deployment and compatibility (for the release notes)

<!-- One line per change, in the imperative, for whoever deploys OpenGateLLM: each line must make sense without the context of this PR. -->

This PR:

- [ ] needs nothing at deployment, and breaks or deprecates nothing
- [ ] adds an Alembic migration to run:
  - …
- [ ] changes the configuration file:
  - …
- [ ] changes environment variables:
  - …
- [ ] introduces breaking changes:
  - …
- [ ] introduces deprecations: <!-- what replaces it, and the issue or release that removes it -->
  - …

## Check lists

### Review checklist

<!-- Before requesting a review, confirm each point. Explain briefly any box left unchecked. -->

- [ ] Updated or added documentation
- [ ] Updated or added unit tests
- [ ] Updated or added integration tests
- [ ] No debug logs or commented-out code left
- [ ] No secrets or environment variables committed in clear text
- [ ] Code is linted and formatted using the project pre-commit hooks

**If [`api/infrastructure/postgres/models.py`](https://github.com/etalab-ia/OpenGateLLM/blob/main/api/infrastructure/postgres/models.py) has been modified:**

- [ ] Alembic migration has been generated, following the [migration rules](https://docs.opengatellm.org/contributing/sql)
- [ ] The migration is an expand, or the contract of an expand shipped in release …
- [ ] The downgrade was run on a copy of real data, or loses nothing (see [rule 5](https://docs.opengatellm.org/contributing/sql#5-downgrades-that-run-and-say-what-they-lose))
- [ ] Each finding of the "Lint the migrations" job is answered in the description

## Additional Notes

<!-- Anything reviewers should focus on: complex logic, risky changes, performance-sensitive code. Delete this section if empty. -->
