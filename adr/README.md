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

| ADR                                                      | Title                                               | Status      | Date       |
|----------------------------------------------------------|-----------------------------------------------------|-------------|------------|
| [2026-01-07](2026-01-07-clean-architecture-migration.md) | Migration to Clean Architecture                     | In Progress | 2026-01-07 |
| [2026-01-30](2026-01-30-es-scaling.md)                   | Elasticsearch Scaling                               | Accepted    | 2026-01-30 |
| [2026-03-17](2026-03-17-integration-test-isolation.md)   | Integration Test Isolation via Transaction Rollback | Accepted    | 2026-03-17 |
| [2026-05-28](2026-05-28-refactoring-model-forwarding.md) | Refactoring model forwarding                        | —           | 2026-05-28 |
| [2026-07-01](2026-07-01-split-rag.md)                    | Extract RAG into OpenGateRAG (OGR)                  | Accepted    | 2026-07-01 |
| [2026-08-27](2026-08-27-datetime-handling.md)            | Datetime handling across API, domain and playground | Accepted    | 2026-08-27 |
| [2026-09-04](2026-09-04-response-schema-mapping.md)      | Mapping domain entities to response schemas         | Accepted    | 2026-09-04 |

## Creating a new ADR

1. Copy the template from the most recent ADR
2. Name it `YYYY-MM-DD-your-decision-title.md`, using the date the decision was made
3. Fill in the sections with your architectural decision
4. Update this README's index table
5. Submit for review via pull request

## References

- [ADR GitHub organization](https://adr.github.io/)
- [Documenting Architecture Decisions - Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)