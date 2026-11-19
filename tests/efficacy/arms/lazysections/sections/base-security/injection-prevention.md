# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Injection prevention

- Use parameterized queries for all database access; never concatenate user
  input into SQL strings
- Escape shell arguments when invoking external commands, or use API
  alternatives that do not invoke a shell
- Never pass user input to dynamic code execution, such as an `eval`
