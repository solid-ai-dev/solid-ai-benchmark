---
name: start-issue
description: Starting work on an issue, a ticket or a bug report
---

# Starting work on an issue, a ticket or a bug report

## Picking up an issue

- Re-read the target for existing coverage before writing anything; an
  issue describes the tree on its filing date
- Verify everything the issue cites as existing, and run what it proposes
  against the tree before adopting it
- Check the open pull requests and the decisions accepted since the filing
  date for work that already closes or moves it
- Restate the scope before starting when it has moved since filing
- Read what a cited sibling change shipped, not what it proposed
- Resolve each cited version identifier against its source; a superseded
  one still resolves
- Treat a closed classification in the acceptance criteria as a claim:
  sort every member yourself before acting on any

  ```
  criteria: "each check runs on Linux or macOS"
  sorted:   9 Linux, 2 macOS, 1 neither -- it runs only on Windows
  ```

- Name each member that fits no branch, and the branch it fails
