# Backend — API Design

## Statelessness
- Keep APIs stateless (MUST): store no client context on the server
  between requests
- Carry everything a request needs in the request itself (MUST)
- Keep session state in the client or a dedicated session store, never in
  the API service
