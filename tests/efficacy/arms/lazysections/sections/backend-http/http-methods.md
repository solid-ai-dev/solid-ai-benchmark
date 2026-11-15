# Backend — HTTP Conventions

## HTTP methods

- Never let a GET or HEAD request change resource state; RFC 9110 defines
  both as safe
- Make every PUT and DELETE idempotent, as RFC 9110 defines them
