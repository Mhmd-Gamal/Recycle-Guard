# UI/UX redesign / 10 November 2026

Applied [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/main), at upstream commit `6ae86f61f520d6ca229d2f40e070410638c908c5`. The design-system search and targeted style/accessibility searches are recorded in `design-system/recycleguard/MASTER.md`.

## Interface changes

- Dark industrial workspace with opaque slate surfaces, amber primary actions, blue evidence highlights and semantic status colours.
- Compact scenario configuration and metrics, navigable workspace sections and a facility schematic with native SVG illustrations.
- Explicit missing/delayed/current observation labels, selected-zone state and keyboard arrow navigation.
- Clearer recommendation hierarchy, visible evidence, expandable conditional plan and an exact action/zone label for manual substitution.
- Advice/decision history filters with event counts, keyboard-focusable scrolling and previous/next replay controls.
- Replay explicitly shows recorded truth and hides live advice; exporting while replaying exports that replay.
- Persistent dismissible errors, inline seed validation, loading feedback and focus recovery after actions.
- Responsive layouts, reduced-motion support and no external font, icon or script requests.

## Scope and verification

This redesign changes the runnable browser interface. The C# simulation, Python policy, API and previously measured experiments are unchanged. Existing Unity source remains unvalidated in Unity; this update does not establish Unity runtime behaviour.

The original end-to-end incident/replay test is retained. `tests/ux.cjs` adds 18 UI/UX checks, including axe-core scans at 375, 768, 1024 and 1440 CSS pixels. It also checks landscape layout, reduced motion and a narrow CSS viewport equivalent to 200% browser zoom on a 750-pixel viewport. The latter is a layout proxy, not a manual browser-zoom or screen-reader audit.

An initial axe scan identified a non-focusable scrolling history on mobile. The history is now a named, keyboard-focusable region with an inset focus indicator. See `artifacts/redesign/ux-results.json` for the final automated result; automated checks alone do not certify WCAG conformance.

The portable ZIP's static web assets are refreshed without modifying the tested Python/C# binaries. The final ZIP is extracted and the browser workflows rerun against it. Updated source, screenshots and demo footage are included in the source archive. The original PDF technical brief continues to describe the unchanged research model and results.
