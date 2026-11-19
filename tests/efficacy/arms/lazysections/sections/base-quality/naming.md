# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Naming

- Name a function with a verb, a class or module with a noun, and a boolean
  with `is`, `has` or `can`
- Rename a name that needs a comment to explain it
- Use the same name for the same concept in every module
- Name a public enum member, CLI flag or result discriminator for the
  capability it offers, never the library behind it: `Transport.HEADED`,
  not `Transport.PLAYWRIGHT` (MUST). A private symbol MAY name its library
