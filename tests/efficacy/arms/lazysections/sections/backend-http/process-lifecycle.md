# Backend — HTTP Conventions

## Process lifecycle

- Start fast — keep initialisation short (MUST)
- Shut down gracefully on a stop signal (`SIGTERM`) in order: stop
  accepting new requests, let in-flight ones finish until the drain
  deadline, cancel what remains, wait up to a bounded cancellation period,
  release resources, then exit (MUST)
- Release resources when the cancellation period ends, even when some
  cancelled work is still running
- Force-exit when the whole shutdown, from draining to releasing
  resources, passes its hard deadline (MUST)
- Set the drain deadline plus the cancellation period below the hard
  deadline, leaving time to release resources
- Fit the hard deadline inside the grace period the platform allows
  before it kills the process
- Recover cleanly when a process is killed without warning (`SIGKILL`,
  power loss) (MUST)
- Keep no state in process memory that a restart cannot rebuild; put it in
  an external store, so any instance can be replaced
