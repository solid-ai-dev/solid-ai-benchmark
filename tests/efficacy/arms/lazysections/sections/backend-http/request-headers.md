# Backend — HTTP Conventions

## Request headers

- Read every header name case-insensitively, as RFC 9110 defines them
  (MUST)
- Avoid the `X-` prefix on custom headers (SHOULD NOT); RFC 6648
  deprecated this convention
- Use a vendor or application-specific prefix on a custom header instead
  (SHOULD)
