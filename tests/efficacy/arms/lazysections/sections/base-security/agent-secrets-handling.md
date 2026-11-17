# Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

## Agent secrets handling

- Never read, print, or cat files that may contain secrets (MUST NOT):
  `.env`, `credentials.json`, `*-key*`, `*.pem`, `*.key`,
  `serviceaccount.json`, `secrets.yaml`
- Never echo, log, or display environment variable values (MUST NOT)
- Check a variable's presence by its exact name without printing its value,
  and treat a set but empty variable as absent
- Never include secret values in commit messages, PR descriptions, or
  conversation output (MUST NOT)
- Warn the user (MUST) before committing files that commonly contain
  secrets (`.env`, `credentials.json`, private keys)
- Verify a secret's presence by a match count or an existence check,
  never by printing it
- Flag a secret exposed in a session to the user immediately: name the
  exposed secret, recommend immediate rotation, and note that session
  history may be cached or logged
