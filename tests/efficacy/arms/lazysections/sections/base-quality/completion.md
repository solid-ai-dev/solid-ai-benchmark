# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Completion

Adding pagination, for example, ends with bounded results, their tests and
an updated contract. It does not end with a rewrite of the service layer.

- Finish a task when the requested behaviour works through the entry point
  its user or caller reaches, and the checks that prove it pass
- Report a check that could not run as not run, never as a pass
- Add an abstraction, infrastructure or a process step only when a stated
  requirement, a demonstrated defect or a material risk justifies it
- Report a problem found outside the task, or file it as its own task,
  rather than fixing it in the same change (SHOULD)
