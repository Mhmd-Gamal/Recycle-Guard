# RecycleGuard / UI system v2

## Source and design process

Applied the user-requested [UI UX Pro Max skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/main), read from `.claude/skills/ui-ux-pro-max/SKILL.md` at commit `6ae86f61f520d6ca229d2f40e070410638c908c5`.

Queries executed locally using the repository's `src/ui-ux-pro-max/scripts/search.py`:

- `industrial monitoring dashboard --design-system -p RecycleGuard --density 8 -f markdown`: verified operations-dashboard match, dark neutral palette, status colour guidance and technical typography.
- `data dense dashboard --domain style -n 2`: verified active `data-dense-dashboard` style, specifically applicable to operational dashboards.
- `keyboard focus feedback --domain ux -n 3`: visible focus, focus not obscured and keyboard interaction guidance.

The initial generator suggested glassmorphism and marketing sections. Those recommendations were not appropriate for an interactive simulation with dense evidence, so the final design uses the more specific data-dense-dashboard match: opaque surfaces, restrained borders, compact metrics and clear task hierarchy. The source project is plain HTML/CSS/JavaScript, not React or Tailwind; no unrelated stack was assumed or installed.

## Direction

Industrial incident workspace. Charcoal/slate surfaces; amber primary actions; blue evidence/selection; green contained/below-threshold status; amber unknown/elevated states; red rejection/failure feedback. Colour never carries status alone: text, icon, age and border style accompany it.

The working view prioritises scenario controls, incident metrics, facility observations, human decision support and audit history. Marketing hero space is removed. Footnotes retain research provenance without interrupting the decision loop.

## Tokens

| Role | Value |
|---|---|
| Canvas | `#10151c` |
| Surface | `#191f28` |
| Raised surface | `#222a35` |
| Primary text | `#edf1f7` |
| Secondary text | `#a5b1c2` |
| Muted text | `#8f9eb1` |
| Action | `#f2b86b` on `#201608` text |
| Evidence / focus | `#9bcaff` |
| Positive | `#83d8b2` |
| Warning / unknown | `#f2c47b` |
| Error | `#ffac9e` |
| Body | Segoe UI / Arial, system fonts for offline operation |
| Data | Cascadia Code / Consolas / monospace |
| Spacing | 4/8 px rhythm; 16–24 px panel padding |
| Targets | Primary controls at least 44 CSS px high |
| Motion | 150–220 ms state feedback; disabled under reduced motion |

System fonts deliberately replace the generated Fira webfont pairing: the portable offline build must not fetch fonts or scripts. SVG icons use a consistent custom outline vocabulary and are decorative where visible text provides the label.

## Interaction rules

- Selected zones expose `aria-pressed`; arrow keys move selection with a visible focus ring.
- Missing observations, delayed observations and recorded replay truth receive distinct labels. Age-one data is labelled delayed even if permitted by the permissive checker.
- Requesting advice, executing an action and backend failures have explicit feedback.
- Errors remain visible and dismissible. Seed validation is inline and focuses the field.
- Human acceptance is the single primary decision action; rejection and alternatives are secondary. Manual substitution names the exact selected action and zone.
- Conditional future steps use progressive disclosure. Evidence remains visible.
- Changing policy removes obsolete advice from the UI.
- Replay hides live recommendations, marks the whole view as debrief and provides previous/next buttons as alternatives to the slider.
- History has functional All / Decisions / Advice filters and event counts.
- No external assets, fabricated real-time telemetry or decorative charts.

## Validation scope

Run existing end-to-end operator workflow tests plus UI-specific regression tests for keyboard selection, inline errors, persistent service errors, filters, manual substitution labels, replay separation, reduced motion and responsive layouts at 375, 768, 1024 and 1440 px. Inspect screenshots. Backend policy and simulation behaviour remain unchanged, so prior numerical experiment results retain their source provenance.
