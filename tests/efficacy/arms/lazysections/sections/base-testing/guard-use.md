# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Guard use

- Assert that the code under test takes a guard, not only that the guard
  works, where the guard exists for other code to take (MUST)
- Prefer a behavioural assertion, such as "a stopped component does no
  work"
- Otherwise wrap the real guard in a recorder that logs entry and exit, and
  assert the order of the work against it
- Pair every "does nothing" assertion with its "does something" control
- Sweep the module for sibling guards when one proves inert

```bash
MODULE=<module-under-review>
FIELD=<guard-field-name>
echo "references to $FIELD in $MODULE: $(grep -c "$FIELD" "$MODULE" || true)"
grep -n "$FIELD" "$MODULE" || true
```

Pass condition: the count is at least two and the listed lines include a
consumer. A count of one is the assignment alone: the guard is built and
never consulted.
