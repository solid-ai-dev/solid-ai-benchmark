# Backend — HTTP Conventions

## Error responses

- Use consistent error response shape across all endpoints
- Never return stack traces, internal paths, or implementation details to the
  client
- Use 4xx for client errors, 5xx for server errors — never use 200 for errors
- Carry a gRPC or GraphQL error the way its protocol defines instead: a
  gRPC status code over HTTP 200, a GraphQL `errors` array under
  GraphQL-over-HTTP's status rules
- Set an explicit `Content-Type` on every JSON response
