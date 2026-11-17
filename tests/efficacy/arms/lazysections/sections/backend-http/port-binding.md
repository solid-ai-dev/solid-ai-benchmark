# Backend — HTTP Conventions

## Port binding

- Read the port from an environment variable such as `PORT`; never
  hardcode it (MUST)
- Use a well-known default in development, and the port the platform
  assigns in production
