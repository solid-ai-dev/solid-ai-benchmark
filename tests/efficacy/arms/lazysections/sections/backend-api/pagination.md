# Backend — API Design

## Pagination
- Paginate every collection endpoint (MUST); never return an unbounded list
- Use `limit` and `offset` (or cursor-based) pagination
- Include navigation links or cursors (`next`, `prev`) in the response
