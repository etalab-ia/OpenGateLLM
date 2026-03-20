# Practical Checklists

## Before Coding

- [ ] I understand the requirement and success criteria.
- [ ] I know the first failing test to write.
- [ ] I am choosing the simplest implementation that could work.
- [ ] I am solving a real need, not a hypothetical future one.

## While Coding

- [ ] This unit still has one clear responsibility.
- [ ] Names reflect the domain and intent clearly.
- [ ] I am not introducing an abstraction before it is needed.
- [ ] Duplication is either temporary or ready to be refactored.
- [ ] Control flow stays shallow and readable.

## After Coding

- [ ] All relevant tests pass.
- [ ] Dead code and stale names are removed.
- [ ] Edge cases are covered or explicitly documented.
- [ ] The result is simpler than or equal to what was there before.
- [ ] Another developer could extend this without surprise.

## Code Review Checklist

- [ ] Behavior is correct for the happy path and likely edge cases.
- [ ] Tests prove the intended behavior and fail for the right reason.
- [ ] Responsibilities are well separated.
- [ ] The change avoids unnecessary coupling.
- [ ] The design is clear without relying on comments to explain basics.

## Red Flags

Stop and rethink when you see:

- Code added without a test or clear validation path
- A class accumulating multiple responsibilities
- A method growing through nested conditionals
- Raw primitives standing in for domain concepts
- New abstractions created "just in case"
- A small requirement forcing edits across many unrelated files
