# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Isolation

- Test behaviour, not implementation details
- Set or clear every environment variable a test depends on, in that test;
  never rely on the ambient process state
- Treat a test that passes or fails by run order as an isolation bug
- Wait on a condition with a deadline, never a fixed sleep
- Never enumerate, signal or terminate a process the test did not start
  (MUST NOT)
- Never mutate host state outside the working directory: the process
  table, system services, the registry, the user's applications (MUST NOT)
- Stub every seam through which the code under test reaches a host
  resource the test does not own, even when its subject is already faked
- Keep the dependency an integration test covers real, isolated to that
  test, such as a throwaway container or a temporary database
- Investigate a failing test before anything else; never skip or suppress
  one without a documented reason
- Check the test's own logic first when it behaves unexpectedly
