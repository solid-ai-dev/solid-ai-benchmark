# Backend — API Design

## Versioning
- Keep every API version backward compatible (MUST)
- Version the API in the URI path prefix: `/v1/`, `/v2/`
- Start at `v1`; introduce `v2` only when a breaking change is unavoidable
- Use a custom request header (`Api-Version: 2`) where a path prefix does
  not fit
- Never version through the media type (MUST NOT)
