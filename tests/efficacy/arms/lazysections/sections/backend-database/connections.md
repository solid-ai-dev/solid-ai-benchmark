# Backend — Database Conventions

## Connections

- Use a connection pool — never open a new connection per request
- Inject the database session/connection as a dependency — no global DB
  handles
- Set the pool size explicitly from the instance count and the
  database's connection cap, so all instances together stay under it
- Monitor pool exhaustion — alert when pool wait time exceeds threshold
