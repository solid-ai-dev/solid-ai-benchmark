# Backend — API Design

## API contract
- Give every API the machine-readable contract of its kind, even when it
  runs over HTTP (MUST):
  - an OpenAPI specification for REST
  - protobuf for gRPC
  - a GraphQL schema
  - a message schema for messaging
- Keep the contract current (MUST); a stale contract is worse than none
- Cover every resource, operation, parameter, response schema, error
  response and authentication requirement in the contract
- Keep a changelog of API changes across versions
- Assert that the enums, operations and error codes in code match the
  contract, so drift fails a test, not a consumer
- Contract-test a running instance against cases generated from the
  contract
- Give the contract a revision of its own, apart from the package version
  and from the API version
- Bump the contract revision for every contract change, additive ones
  included; never bump it for a release that leaves the contract unchanged
