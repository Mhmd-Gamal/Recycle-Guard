# RecycleGuard: evidence-aware decision support in a discrete incident simulator

**Version 1.0 | 10 November 2026 | Research prototype**

## Abstract

RecycleGuard combines a deterministic C# emergency-training model, a Python decision-support service and human-controlled interfaces. It investigates whether explicit constraints and evidence-freshness requirements reduce invalid recommendations in a fictional resource-recovery facility. A Windows browser build is tested end to end; native Unity client source is supplied but not Unity-validated. The evaluation uses deterministic fault-injection fixtures rather than real LLM outputs. Across 1,200 held-out episodes, the strict checker recorded zero invalid attempts, while a permissive checker retained stale-action errors. These results establish limited engineering behaviour inside a synthetic model, not operational safety or improved human decisions.

## 1. Motivation and scope

An emergency adviser should expose the observations behind its recommendation and leave authority with the operator. This prototype makes uncertainty, prerequisites and human decisions inspectable. The fictional Northbank facility has four zones: battery intake, sorting hall, materials store and loading yard. Its heat units, resources and action semantics are arbitrary training abstractions. They must not be interpreted as instructions for real battery or facility fires.

The central engineering question is the effect of current versus aged evidence on action validity. A future research question is whether a similar checker improves real-LLM advice. The present fixture experiments cannot answer that latter question.

## 2. Architecture and authority

`Simulation.cs` defines the sole state-transition implementation. The file is shared unchanged by Unity and a compiled C# JSON-line host. The browser calls a local Python session adapter, which delegates state transitions to that host. The Unity client instead instantiates the C# model directly. The Python adviser receives only typed observations, with no true world state, random-generator state or direct action-execution access.

The loop is observe, propose, check, explain, obtain human decision, validate again in C#, execute, and log. A recommendation carries its revision, raw proposal, replacement decision, rule violations, source timestamps, missing evidence and conditional subgoals. There is no invented confidence percentage. Acceptance, rejection, alternatives and manual modification are explicit. Stale revision submissions cannot advance the incident. Exported replays rerun the action sequence and verify stored world snapshots before debriefing.

## 3. Model and policies

Each zone has integer heat (0-100), occupants (0-4 initially) and binary isolation. There are two crews and 18 suppression units. The episode horizon is 32 ticks. The initial battery-intake heat is 48-60; other zones start at 5-13. A seeded linear-congruential generator determines initial occupants and noise.

An active zone (heat >=25) grows by 3-5 units per tick when powered, or 1-3 when isolated. Inactive zones cool by one. An adjacent zone at heat >=75 adds five units of growth. Heat >=80 adds synthetic damage equal to one plus remaining occupants. These are transparent discrete rules, not physical equations. A policy can change random-draw consumption because only active growth draws noise; paired seeds mean matched initial conditions, not identical subsequent exogenous noise.

Actions: inspect, evacuate, isolate, suppress and wait. Inspection supplies current evidence for three post-action ticks. Evacuation clears modelled occupants and reserves a crew until tick+2. Isolation changes the power flag. Suppression requires an empty isolated zone, actionable heat, one crew and two resource units; it reduces heat by 38 and reserves a crew until tick+2. Every applied current decision costs one tick. Invalid current decisions also cost a tick, while spending no action resources. Stale requests and rejected advice consume no time.

Reliable telemetry is current. Delayed telemetry is three ticks old after the initial warm-up. Dropout has deterministic intermittent missing zones and one-tick delay elsewhere. Unknown fields are -1 with explicit missing source/timestamp values. Reconnaissance overrides these sensor conditions.

The execution guard accepts operational evidence aged up to two ticks, then checks true action prerequisites. The permissive adviser mirrors the observation-side rules. The strict adviser additionally requires age-zero evidence for operational actions; it can request inspection to achieve this. Replacement actions use an explicit priority heuristic, not an optimal search algorithm. Future subgoals are conditional and replanned after each action.

## 4. Evaluation

Development seeds 1000-1029 revealed redundant evacuation/isolation proposals from recently aged evidence. After selecting the strict checker, seeds 2000-2099 were run across three scenarios and four policies (script, raw fixture, permissive checker, strict checker): 1,200 held-out episodes. No completed episode was excluded; every episode was replay-verified. Provider failures would abort a real-model run rather than substitute fixture outputs.

| Scenario | Raw fixture invalid attempts | Permissive checker | Strict checker | Strict containment | Strict mean ticks |
|---|---:|---:|---:|---:|---:|
| Reliable | 25.3% | 0.0% | 0.0% | 100% | 6.6 |
| Delayed | 70.8% | 6.7% | 0.0% | 100% | 14.3 |
| Dropout | 43.0% | 25.0% | 0.0% | 100% | 15.6 |

Rates above pool attempts across decisions. The raw fixture contained 100%, 0% and 91% of episodes respectively. Under dropout, the permissive checker averaged 10.7 ticks versus 15.6 for the strict checker: current evidence costs additional inspection decisions. In 5,458 identical-observation/proposal probes from raw trajectories, the raw fixture had 2,964 invalid proposals and the strict checker had zero. All policies have an independent execution guard, so attempted invalidity does not mean unsafe actions were executed.

Paired per-episode invalid-rate differences (strict minus raw) were -24.43 percentage points for reliable telemetry, -71.40 for delayed, and -40.41 for dropout. Deterministic paired bootstrap 95% intervals were [-26.10,-22.86], [-72.28,-70.60], and [-42.37,-38.21]. These quantify variation over the synthetic generator only. Full script results, resource counts, latency, manifests and traces are provided in `artifacts/heldout-evaluation`.

Offline median policy times were sub-millisecond on this machine. They exclude C# IPC, rendering and model/network latency, and were measured in a non-isolated development environment; they are not a production performance benchmark.

## 5. Verification and limitations

Automated coverage includes deterministic seeds and replay, resource accounting, rejection of invalid and stale actions, telemetry uncertainty, C#/Python constraint parity across generated trajectories, state invariants, human alternatives/rejection, provider HTTP contracts and malformed provider outputs. Browser automation exercises complete incident containment, manual rejection, audit export, verified replay and narrow-screen layout. The portable Windows build is tested separately from the source server. See the validation inventory for exact evidence and pending checks.

The strict checker's zero-invalid result is partly by construction: it encodes the model's rules and demands current evidence. The fixture intentionally includes poor proposals and does not estimate any LLM's failure distribution. The scripted baseline is simple; the fallback heuristic confounds claims about filtering alone. Scenario realism, domain rules and human usefulness remain unvalidated. There are no real-LLM, FRV, firefighter, human-trust, calibrated-confidence or operational-safety results. The Unity source has not been compiled, run or visually checked in Unity.

## 6. Reproducibility, provenance and next steps

The release includes the shared C# source, Python code, Unity source, pinned direct dependencies, Windows demo, tests, experiment runner, raw traces, SHA-256 source manifests, replay example, browser video and build scripts. Run `python -m experiments.run --seeds 100 --seed-start 2000 --output artifacts/heldout-evaluation` after compiling the core. Source manifests identify the evaluated files. See `EXPERIMENT_PROTOCOL.md` for definitions and `UNITY_BUILD.md` for remote licensed-Editor builds.

Development provenance is recorded in [CONTRIBUTIONS.md](CONTRIBUTIONS.md). The next validation step is a Unity build and interaction test on a licensed machine. Subsequent steps are real-model equal-state cached-proposal evaluation, stronger baselines, noisy/delayed action acknowledgements, expert-reviewed scenarios and a properly designed human study.

## References

- Unity: [command-line Editor invocation](https://docs.unity.com/en-us/engine/6000.3/manual/unity-editor/command-line-arguments/run-unity), [UnityWebRequest](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Networking.UnityWebRequest.html), [JsonUtility](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/JsonUtility.html).
- Ollama: [compatible chat-completions endpoint](https://docs.ollama.com/api/openai-compatibility).
- Playwright: [recording test videos](https://playwright.dev/docs/videos).

These are implementation references, not scientific validation or endorsement.
