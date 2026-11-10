# Validation inventory

This inventory separates observed execution from supplied but unexecuted code. Evidence was produced on Windows 10 x64 using Python 3.12, the Windows .NET Framework C# compiler and installed Chrome.

## Executed

| Layer | Evidence | Outcome |
|---|---|---|
| Shared C# core | `scripts/build-core.ps1` | Compiled successfully without Unity. |
| Core, policy, API and provider adapter | `artifacts/test-results.xml` | 39 tests passed. Provider tests use a local HTTP stub, not a real LLM. |
| Development evaluation | Seeds 1000-1029 | Used to discover/refine evidence-freshness behaviour; not treated as held-out. |
| Final evaluation | `artifacts/heldout-evaluation/manifest.json`, `episodes.csv`, `traces.jsonl`, `summary.json` | 1,200 episodes; every completed episode replay-verified. |
| Equal-state probes | `artifacts/heldout-evaluation/equal-state-probes.json` | 5,458 pairs; raw invalid 2,964; strict checked invalid 0. |
| Browser controls | `artifacts/browser/results.json` and screenshots | Full 17-step checked incident, invalid action block, alternatives, rejection, export, verified replay and mobile layout passed. |
| Portable build | `dist/RecycleGuard-Windows.zip` | PyInstaller executable launched without invoking a system Python interpreter; the same browser flow passed against it. |
| Demonstration | `artifacts/demo/RecycleGuard-browser-demo.webm` | Paced recording of the actual browser app and C# simulation, explicitly labelled non-Unity footage. |

Initial browser packaging verification exposed a test timing race: the test read the decision trail after the tick changed but before its asynchronous refresh completed. The test now waits for the full UI transaction before asserting. No simulation result was altered to make the test pass.

## Not executed / not established

- Unity Editor import, C# compilation against Unity assemblies, actual scene rendering and player build.
- Unity HTTP integration and standalone-player interaction.
- Any genuine LLM experiment; local stub HTTP tests establish adapter behaviour only.
- Expert validation of scenario assumptions or action rules.
- Human decision-quality, usability, workload, trust or calibration studies.
- Performance benchmarking on isolated hardware or cross-platform portability beyond this Windows environment.
- GitHub-hosted CI execution. Workflow files are provided, not run.

## Unity acceptance checklist (must be completed on a licensed machine)

- Record Editor patch version, OS, hardware, source commit and clean import/build logs.
- Create the incident scene; verify all four zones, labels, camera framing and resizing at 1280x720 and 1600x900.
- Change seeds and all three scenarios; verify missing/stale observations are distinguishable.
- Select each zone and apply every manual action, including invalid resource/prerequisite cases.
- Start the Python service; accept/reject/modify/request alternatives and inspect logs.
- Stop the service and verify an explicit error while manual simulation remains available.
- Verify stale advice cannot execute after the world changes.
- Export and load a replay, scrub events, and verify the debrief/truth label.
- Run the player with `-rgSmoke`; inspect `unity-smoke.json`, the screenshot and player log.
- Record a genuine player walkthrough. Do not replace the browser provenance label until actual Unity footage exists.

## Interpretation discipline

Zero invalid attempts in a finite synthetic test set is not a universal guarantee. The checker encodes the rules under evaluation; the purpose of these tests is to demonstrate an inspectable engineering implementation. Report all fixture/baseline assumptions, and keep operational and human-performance claims out of the submission until there is suitable evidence.
