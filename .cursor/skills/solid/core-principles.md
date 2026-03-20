# Core Principles

## Goal

Write software that is easy to discover, understand, change, test, debug, and remove.

## TDD Loop

Use Red -> Green -> Refactor:

1. Red: write the smallest failing test that describes behavior.
2. Green: write the simplest code that passes.
3. Refactor: improve names, structure, and duplication without changing behavior.

Three laws of TDD:

1. Do not write production code until a failing test requires it.
2. Do not write more test code than needed to fail.
3. Do not write more production code than needed to pass.

## SOLID Questions

Ask these for every class, function, or module:

| Principle | Question |
| --- | --- |
| SRP | Does this have one reason to change? |
| OCP | Can behavior vary without editing stable code? |
| LSP | Can substitutes behave safely anywhere the base is expected? |
| ISP | Are clients forced to depend on methods they do not use? |
| DIP | Do higher-level policies depend on abstractions, not details? |

## Clean Code Defaults

- Prefer domain language over technical filler names.
- Use the same term for the same concept everywhere.
- Keep methods short and focused.
- Prefer early returns over nested conditionals.
- Use `Object.hasOwn(...)` or `Object.prototype.hasOwnProperty.call(...)` for untrusted JS object key checks instead of `in`.
- Avoid broad "manager", "data", or "helper" abstractions.

## Responsibility And Object Design

Useful stereotypes:

- Information holder: stores validated data.
- Service provider: performs stateless work.
- Coordinator: orchestrates multiple collaborators.
- Controller: makes decisions and delegates.
- Interfacer: translates between systems or layers.

If a unit fits multiple stereotypes at once, it may be doing too much.

## Complexity Management

Separate:

- Essential complexity: required by the problem domain.
- Accidental complexity: introduced by the implementation.

Reduce accidental complexity with:

- KISS: simplest solution that works
- YAGNI: do not build hypothetical flexibility
- Rule of Three: abstract only after real repetition

## Architecture

- Organize around features and use cases when possible.
- Keep dependencies pointing toward higher-level policy.
- Infrastructure should depend on domain decisions, not the reverse.
- Prefer boundaries that reduce change amplification.

## Smells To Watch

- Long methods
- Large classes
- Long parameter lists
- Primitive obsession
- Divergent change
- Shotgun surgery
- Feature envy
- Speculative generality

Treat these as prompts to simplify, not as pattern-matching exercises.

## Testing Strategy

Prefer fast feedback:

1. Unit tests for single behaviors
2. Integration tests for collaborating pieces
3. End-to-end tests for user-visible flows

Use concrete test names, for example `when adding 2 and 3, returns 5`.
