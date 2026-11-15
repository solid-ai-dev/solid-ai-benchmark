# Frontend — UX Principles

## Accessibility testing

Automated tools catch about 30–40% of WCAG issues, so AA takes manual
testing too.

### Automated (run in CI)

- Scan rendered pages or components with an automated accessibility
  checker in CI; merge on zero violations

### Manual (run before shipping new interactive components)

- Tab through the whole feature without a mouse: every action reachable,
  focus order logical, no focus trap but an intentional modal
- Test it with one screen reader, such as NVDA, VoiceOver or TalkBack, and
  check every content and state change is announced
- Zoom to 200%: nothing clipped or overlapping, and no horizontal scroll
  at a 1280px viewport
- Check Windows High Contrast or the forced-colors media query: no
  information lost when colours are overridden

### Criteria for done

A feature is not complete until:

- [ ] The automated accessibility check reports zero violations
- [ ] Keyboard navigation verified manually
- [ ] Screen reader walkthrough completed for new interactive elements
