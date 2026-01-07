# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for OpenGateLLM.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## Format

Each ADR follows this structure:

- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Date**: When the decision was made
- **Context**: What is the issue that we're seeing that is motivating this decision or change
- **Decision**: What is the change that we're proposing and/or doing
- **Consequences**: What becomes easier or more difficult to do because of this change

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-clean-architecture-migration.md) | Migration to Clean Architecture | In Progress | 2025-01-07 |

## Creating a new ADR

1. Copy the template from the most recent ADR
2. Number it sequentially (e.g., `002-your-decision-title.md`)
3. Fill in the sections with your architectural decision
4. Update this README's index table
5. Submit for review via pull request

## References

- [ADR GitHub organization](https://adr.github.io/)
- [Documenting Architecture Decisions - Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)