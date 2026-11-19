# Backend — HTTP Conventions

## Handler design

- Keep handlers thin: decode request → call service → encode response
- Never put business logic in a handler; delegate it to a service layer
- Validate all incoming request data before processing
- Set a timeout on every outbound call (HTTP clients, database queries)
