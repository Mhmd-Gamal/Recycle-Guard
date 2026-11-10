# Evaluation protocol

## Questions

Engineering question tested here: how do explicit action constraints and evidence-freshness requirements affect attempted invalid actions, simulated outcomes and resource use in a small partially observed incident model?

Future research question, not answered by the offline runs: does constraint-checked agentic planning reduce invalid recommendations from a real LLM under incomplete information, and at what cost to task performance and latency?

## Arms

1. `scripted`: fixed zone-order evacuation, then isolation/suppression. No active missing-evidence repair.
2. `offline_raw`: a deterministic fault-injection fixture selects among direct suppression, fixed-zone evacuation, isolation, the script and a valid priority action. It intentionally mixes valid and invalid proposals. **It is not a model of LLM error frequencies.**
3. `offline_checked_permissive`: the same fixture with observation constraints matching the execution guard's maximum observation age of two ticks and priority repair.
4. `offline_checked`: the same fixture with an additional age-zero requirement for operational actions. Inspection, waiting and conditional subgoal planning remain available. The checker preserves valid proposals, replacing only invalid/excluded ones.

For real-model runs: script, `llm_raw`, `llm_checked`. The two LLM arms receive the same prompt and observation schema and request temperature zero. They run on diverging closed-loop trajectories. To isolate a checker effect on identical model outputs, additionally cache one raw proposal per observation and apply both checkers to that same cached output. The shipped equal-state probe implementation currently does this for the deterministic fixture only.

## Development and final evaluation

- Development seeds: 1000-1029. Used to identify stale-evidence duplicate actions and to design the stricter checker. Their results are not treated as an untouched test set.
- Held-out seeds: 2000-2099, selected after fixing the checker and before executing the final run. Three scenarios, four policies, 1,200 episodes.
- Dynamics and scenario parameters are shared by all policies. Only the initial PRNG seed is paired. The simulator consumes random draws on active heat growth, so policies can induce different draw consumption; these are matched initial conditions, not identical exogenous noise trajectories.
- Each episode ends at containment, damage >=45, or tick 32. All completed episodes remain in the metrics. Provider errors abort a real-model run and must be reported, not discarded as successes.
- Every completed episode is exported internally and replay-verified against the authoritative C# core.

## Metrics

- **Attempted invalid-action rate:** C# rejections divided by attempted decisions. Includes rule/evidence/resource violations and redundant actions inconsistent with truth. This is not a count of executed unsafe actions: the guard rejects invalid actions in every arm.
- **Containment:** all zones have zero occupants and heat below 25 before the horizon/failure condition.
- **Damage:** accumulated synthetic damage units; not casualties, monetary loss or a physical hazard estimate.
- **Decision ticks, evacuated count, water remaining:** recorded per episode.
- **Interventions:** number of proposals replaced by the checker, including human exclusions when present. Automated runs have no human exclusions.
- **Latency:** policy function wall time; offline figures exclude simulator IPC, UI and network. Real-provider latency includes its HTTP round trip.

Tables pool invalid attempts across decisions. Paired effects compute each episode's invalid rate, subtract raw from strict checked for the same seed/scenario, and report the mean difference. A deterministic percentile bootstrap samples paired seed-level differences with replacement 2,000 times (RNG seed 20261110). The 95% intervals quantify variability over this generator, not generalisation to real emergencies.

Equal-state probes apply raw and strict fixture policies to exactly the same observations on the raw arm's trajectories. The invariant `same_proposal` is stored. Check validity against C# truth before either action executes. This separates local filtering from closed-loop trajectory effects.

## Threats to validity

The guard and checker implement intentionally related constraints; lower invalidity is partly a construction property. The strict checker can avoid stale-action errors by paying for inspection, at the cost of more ticks. The fixed-priority script is a basic control, not an expert baseline. The fixture was intentionally designed to fail and must not be called an LLM surrogate. Four zones, stationary occupants, deterministic policy, simple heat growth and easy containment cases restrict external validity. No user study, expert review, FRV data, calibration study or physical simulation is included.

Recommended next experiments: real-model equal-state cached proposals; multiple model families and sampling seeds; sensor-noise and inspection-cost sweeps; delayed action outcomes and command acknowledgements; stronger scripted and search baselines; independent rule specifications; domain-expert scenario review. Human studies require an appropriate study design and approvals before recruitment or claims.
