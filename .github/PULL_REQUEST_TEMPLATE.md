<!-- Title: the conventional commit title of the change, e.g. "fix(key): stop rejecting keys that contain sk- after the prefix" -->

## Overview

<!-- The shortest text a human can read to know what this PR is for and whether it deserves their attention: one to three sentences, written or approved by you, not pasted from an agent. Add a screenshot if it shows the change faster. -->

Closes #

<!-- The Definition of Done (DoD) criteria that apply to this PR. -->

- [ ] DoD 1
- ...

<!-- The full description (problem, solution, how it was verified) goes in the block below. Name the summary after its author: the model and effort level if an agent wrote it ("Claude Opus 5.5 Medium"), "Details" otherwise. Keep the blank line after </summary>, or GitHub does not render the Markdown inside. Delete the block if the opener says it all. -->

<details>
<summary>Details</summary>

…

</details>

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
