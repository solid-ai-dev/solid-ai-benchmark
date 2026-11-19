# Frontend — UX Principles

## Accessibility — WCAG 2.1 AA

- Meet WCAG 2.1 AA
- Keep text contrast at 4.5:1 or more, 3:1 for large text
- Make every interactive element reachable and operable by keyboard
- Never put a click handler on a non-focusable element (MUST NOT); it adds
  no tab stop or keyboard activation
- Use a native interactive element for such a control instead: a button, a
  link or another native control
- Style focus with `:focus-visible`, not `:focus`, which also outlines
  mouse clicks
- Keep a visible focus indicator on every focusable element, links and nav
  links included (MUST); links often lack one even where buttons have it
- Never convey meaning by colour alone
- Give images descriptive `alt` text, and decorative ones `alt=""`
- Use semantic HTML: landmark elements and a correct heading hierarchy
- Give an icon-only or ambiguous control, such as a social link, a
  descriptive `aria-label`; never add one where visible text already names
  the control
- Make an accessible name contain the control's visible text, ideally at
  its start (WCAG 2.5.3, Label in Name)
- Close menus on Escape and restore focus
