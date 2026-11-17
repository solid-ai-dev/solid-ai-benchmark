# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Secrets in code

- Never hardcode secrets, API keys, tokens, or credentials in source files
- Keep local secret files out of version control
- Rotate a secret immediately if it is accidentally committed; removing it
  from git history is not sufficient, since the secret is compromised
