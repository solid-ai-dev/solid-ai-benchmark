# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Encoding and line endings

- Encode every committed text file in UTF-8, with LF line endings (MUST)
- Keep identifiers ASCII (MUST); comments, docstrings, strings and
  documentation carry no charset restriction

```bash
pre-commit run check-ascii-identifiers --all-files --verbose
```

Pass condition: the inspected count is above zero and
`non-ASCII identifiers` is zero. The hook reads Python; `not applicable`
means the project tracks none.

- Set a program's output encoding explicitly, and pin its line ending where
  another program reads the output
- Commit a `.gitattributes` with `* text=auto`, adding `eol=lf` for hard
  LF
- Mark a text path exempt from LF with `-text` in `.gitattributes`
- Check line endings on every tracked file, whatever its name, exempting a
  `-text` file; count a file Git files `i/-text` as binary only when it
  holds a NUL byte
- Let a linter format on save, and keep manual style rules to a minimum
  (SHOULD)

```bash
seen=0 exempt=0 binary=0 bad=()
while IFS= read -r -d '' rec; do
  info=${rec%%$'\t'*} path=${rec#*$'\t'} seen=$((seen + 1))
  case " ${info#*attr/} " in *" -text "*) exempt=$((exempt + 1)); continue ;; esac
  case $info in "i/ "* | i/lf* | i/none*) continue ;; esac
  nuls=$(git cat-file blob ":0:$path" | tr -dc '\000' | wc -c)
  [[ $info == i/-text* && $nuls -gt 0 ]] && binary=$((binary + 1)) && continue
  bad+=("$path")
done < <(git ls-files -z --eol)
printf 'files inspected: %d\nexempt by -text: %d\n' "$seen" "$exempt"
printf 'binary by content: %d\nfiles not filed i/lf: %d\n' "$binary" "${#bad[@]}"
for f in "${bad[@]}"; do echo "  $f"; done
[ "$seen" -gt 0 ] && [ "${#bad[@]}" -eq 0 ]
```

Pass condition: exit zero, given only when the inspected count is above
zero and the not-`i/lf` count is zero. An empty `i/none` file passes; a
stray carriage return, filed `i/-text` with no NUL byte, still fails.
