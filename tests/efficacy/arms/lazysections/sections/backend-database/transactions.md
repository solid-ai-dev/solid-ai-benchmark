# Backend — Database Conventions

## Transactions

- Wrap multi-step writes in a transaction — commit only after all writes
  succeed
- Never leave a transaction open across a request boundary
- Keep transactions short — do not call external services inside a transaction
- Use an isolation level stronger than the engine's default only when
  genuinely required
