# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Output encoding (XSS)

- Encode dynamic data for its rendering context at the point of output:
  HTML, URL, JavaScript, SQL, shell
- Encode on output, not on input — store the raw value, encode when
  rendering
- Use the encoding the framework or template engine provides
- Never insert user-supplied data through a raw-HTML path that bypasses
  auto-escaping
- Apply the encoding that matches each context; HTML encoding does not
  prevent URL injection
