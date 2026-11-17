# Backend — API Design

## Protocol selection

| Protocol  | Use when                                                                                            |
|-----------|-----------------------------------------------------------------------------------------------------|
| REST      | Default. External APIs, browser/mobile clients, third-party integrations, ops/admin endpoints       |
| gRPC      | Internal service-to-service, performance-critical paths, streaming, polyglot teams sharing a schema |
| GraphQL   | Frontend-facing APIs where clients need flexible querying and over-fetching is a real problem       |
| WebSocket | Real-time push, bidirectional streams where HTTP polling is not viable                              |
| Messaging | Async, fire-and-forget, event-driven                                                                |

- Start with REST; deviate only with a reason in a decision record
- Combine REST for external and ops endpoints with gRPC for internal hot
  paths (MAY)
- Justify any other pair of API styles in one service in a decision
  record; two surfaces double the maintenance
- Never use gRPC as the primary interface for browser clients
