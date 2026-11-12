# Validation inventory

This inventory separates observed execution from supplied but unexecuted code. Evidence was produced on Windows 10 x64 using Python 3.12, the Windows .NET Framework C# compiler and installed Chrome. Unity evidence was produced on 11-12 November 2026 on the same machine with Unity 6000.6.8f1, an NVIDIA GeForce 920M and Direct3D 11.

## Executed

| Layer | Evidence | Outcome |
|---|---|---|
| Shared C# core | `scripts/build-core.ps1` | Compiled successfully without Unity. |
| Core, policy, API and provider adapter | `artifacts/test-results.xml` | 52 tests passed. Provider tests use a local HTTP stub, not a real LLM. |
| Observation-timestamp panel logic | `tests/test_observation_timeline.py` (13 of the 52 tests) | `ObservationTimeline.cs` compiled into the headless host. Panel freshness agreed with the C# evidence check on every zone and tick; preflight matched the validator; rows showed lagged observations, never ground truth. |
| Development evaluation | Seeds 1000-1029 | Used to discover/refine evidence-freshness behaviour; not treated as held-out. |
| Final evaluation | `artifacts/heldout-evaluation/manifest.json`, `episodes.csv`, `traces.jsonl`, `summary.json` | 1,200 episodes; every completed episode replay-verified. |
| Equal-state probes | `artifacts/heldout-evaluation/equal-state-probes.json` | 5,458 pairs; raw invalid 2,964; strict checked invalid 0. |
| Browser controls | `artifacts/browser/results.json` and screenshots | Full 17-step checked incident, invalid action block, alternatives, rejection, export, verified replay and mobile layout passed. |
| Portable build | `dist/RecycleGuard-Windows.zip` | PyInstaller executable launched without invoking a system Python interpreter; the same browser flow passed against it. |
| Browser demonstration | `artifacts/demo/RecycleGuard-browser-demo.webm` | Paced recording of the actual browser app and C# simulation, explicitly labelled non-Unity footage. |
| Unity compile and build | Batch-mode `BuildProject.BuildWindows`, Unity 6000.6.8f1 | All scripts compiled against Unity assemblies. The Editor-side core and timestamp-panel checks passed (`RECYCLEGUARD_CORE_VERIFIED`). A Windows x64 development player was built. |
| Unity player, automated check | `artifacts/unity/unity-smoke.json` and three screenshots | `-rgSmoke` exited 0 at 1280x720: scene start, working surface and label shaders, unsafe suppression blocked, replay verified, and every timestamp-panel row consistent with the evidence check in the reliable, delayed and dropout scenarios. The screenshots were inspected by eye. |
| Unity player, real mouse clicks | `tests/unity_clicks.py`; pictures in `artifacts/unity/clicks` | Operating-system clicks at 1152x648: scenario control and new incident, zone picked in the 3D view, zone picked from a panel card, wait three times, evacuate on stale evidence (blocked, one tick spent), inspect (row refreshed). The pictures were inspected by eye. |
| Unity adviser integration | `artifacts/demo/RecycleGuard-unity-demo.webm`; click picture 6 | With the service running, the player requested, displayed and accepted live HTTP advice in `offline_checked` and `offline_raw` modes. With the service stopped, it showed "Adviser unavailable" and manual actions kept working. |
| Unity demonstration | `artifacts/demo/RecycleGuard-unity-demo.webm` | 116-second captioned walkthrough (`-rgDemo`). The frames were rendered and saved by the player itself; the walkthrough calls the client's methods rather than clicking. Stills from it were inspected by eye. |

Initial browser packaging verification exposed a test timing race: the test read the decision trail after the tick changed but before its asynchronous refresh completed. The test now waits for the full UI transaction before asserting. No simulation result was altered to make the test pass.

The first Unity build exposed two defects that the automated check did not catch. Every scene primitive rendered magenta, because the scene is built from code and the player build had stripped the lit shader that no asset referenced; and the zone labels were only a few pixels high. Both were found by looking at the screenshots while `-rgSmoke` reported a pass. The build now creates a material asset that keeps the shader, the labels were resized, and `-rgSmoke` now fails when a zone or label material has no working shader. A first attempt to record the walkthrough by copying the window from the desktop produced only the Unity splash screen and was discarded; the player now saves its own frames.

## Not executed / not established

- Unity Editor Play mode and interactive Editor use. The client was built in batch mode and run only as a standalone player.
- In the Unity player, with real clicks: reject, request alternative, export, the replay slider and seed entry. The walkthrough exercises export and replay through code only.
- Unity window resizing, the `llm_checked` and `llm_raw` modes, other graphics hardware, other Windows versions and Unity versions other than 6000.6.8f1. The project was written against 6000.3.0f1 and has not been built with it.
- Any genuine LLM experiment; local stub HTTP tests establish adapter behaviour only.
- Expert validation of scenario assumptions or action rules.
- Human decision-quality, usability, workload, trust or calibration studies.
- Performance benchmarking on isolated hardware or cross-platform portability beyond this Windows environment.
- GitHub-hosted CI execution. Both Unity workflows and the test workflow are provided; no run has started a job.

## Unity acceptance checklist

Done on the machine described above:

- Editor version, OS, graphics device and API recorded in `unity-smoke.json`; build log checked for compiler errors.
- Incident scene created by the build; all four zones, labels and camera framing checked at 1280x720 and 1152x648.
- All three scenarios run; current, aged, stale and missing readings are visibly different in the panel and on the zone labels.
- Zone selection in the 3D view and from the panel; wait, evacuate and inspect applied by click, including a blocked action.
- Adviser service running: advice requested, shown with its evidence and gaps, and accepted. Service stopped: explicit error, manual simulation still available.
- Replay exported, verified and stepped in debrief with the truth label (through the walkthrough).
- `-rgSmoke` run; `unity-smoke.json`, the three screenshots and the player log inspected.
- Genuine player footage recorded.

Still open:

- Isolate and suppress by click, including the resource and prerequisite failure cases.
- Reject, modify and request alternative by click; verify stale advice cannot execute after the world changes.
- Scrub the replay slider by hand.
- Resize the window, including 1600x900 on a larger display.
- Repeat on a second machine or graphics device.

## Interpretation discipline

Zero invalid attempts in a finite synthetic test set is not a universal guarantee. The checker encodes the rules under evaluation; the purpose of these tests is to demonstrate an inspectable engineering implementation. A passing automated check is only as good as what it looks at: the magenta scene passed until a person looked at the picture. Report all fixture/baseline assumptions, and keep operational and human-performance claims out of the submission until there is suitable evidence.
