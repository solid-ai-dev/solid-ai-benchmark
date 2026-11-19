# Backend — HTTP Conventions

## Query parameters

- Parse a typed query parameter explicitly so you can distinguish three
  states: absent (use the default), present-and-valid (use it), and
  present-but-invalid (raise 400)
- Never rely on a parsing helper that returns the default on a malformed
  value; it silently turns a client error into a successful default-valued
  200
