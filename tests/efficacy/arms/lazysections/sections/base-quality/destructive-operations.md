# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Destructive operations

- Delete, truncate, overwrite or kill only what the operation can prove it
  created: process ancestry, a key scheme, a filename prefix, a marker file
  or an ownership tag; never a path, a configuration value or a file
  extension
- Find nothing where the proof is unavailable: no error, no prompt, no
  guess
- Validate the input as well: reject an empty configuration value, and
  match the key scheme
- Apply this to every reaper: a cache clean, an output-directory clear, a
  log rotation, a temp-file sweep

```
match on ".html"              wrong directory -> README.html deleted
match on "[0-9a-f]{16}.html"  wrong directory -> nothing matched
```
