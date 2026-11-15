# Backend — API Design

## Backward compatibility
- Release a new API version for every breaking change: a removed or
  renamed response field, a changed field type, a switched auth scheme
- Treat as breaking, too, a changed verb or path, wire protocol or
  Content-Type, and business logic that changes observable results
- Never bump the API version for an additive change (MUST NOT): a new
  optional field, endpoint, verb or query parameter keeps `/v1/` and moves
  only the contract revision
