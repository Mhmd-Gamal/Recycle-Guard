# Measured evaluation results

Offline fixtures are NOT language models. Simulator guard rejects invalid actions in every arm; measured invalidity is attempted recommendations, not executed unsafe actions.

1200 completed episodes; 100 matched seeds per scenario/policy. All episode replays verified.

| Scenario | Policy | Invalid attempts | Contained | Mean damage | Mean ticks | Median policy ms |
|---|---|---:|---:|---:|---:|---:|
| reliable | scripted | 0.0% | 100.0% | 0.1 | 7.0 | 0.107 |
| reliable | offline_raw | 25.3% | 100.0% | 0.0 | 9.3 | 0.116 |
| reliable | offline_checked_permissive | 0.0% | 100.0% | 0.0 | 6.6 | 0.117 |
| reliable | offline_checked | 0.0% | 100.0% | 0.0 | 6.6 | 0.121 |
| delayed | scripted | 95.4% | 0.0% | 48.8 | 21.7 | 0.222 |
| delayed | offline_raw | 70.8% | 0.0% | 19.2 | 28.1 | 0.237 |
| delayed | offline_checked_permissive | 6.7% | 100.0% | 0.0 | 14.9 | 0.243 |
| delayed | offline_checked | 0.0% | 100.0% | 0.0 | 14.3 | 0.251 |
| dropout | scripted | 30.2% | 100.0% | 5.0 | 17.2 | 0.220 |
| dropout | offline_raw | 43.0% | 91.0% | 4.0 | 17.2 | 0.236 |
| dropout | offline_checked_permissive | 25.0% | 100.0% | 0.6 | 10.7 | 0.240 |
| dropout | offline_checked | 0.0% | 100.0% | 0.0 | 15.6 | 0.242 |

Invalid attempts are pooled across decisions; paired confidence intervals below use per-episode rates. Latency includes policy construction/checking only, excluding C# IPC, browser rendering and network calls in offline mode.

## Paired differences (checked minus raw)

- reliable: -24.43 percentage points; paired bootstrap 95% interval [-26.10, -22.86].
- delayed: -71.40 percentage points; paired bootstrap 95% interval [-72.28, -70.60].
- dropout: -40.41 percentage points; paired bootstrap 95% interval [-42.37, -38.21].

Equal-state probes: 5458; raw invalid 2964; shielded invalid 0. Each pair used the same proposal and observation.

## Interpretation limits

The checker explicitly encodes the validity rules, so lower invalidity is an expected engineering property, not evidence of novel AI reasoning. These synthetic fixtures cannot answer the proposed research question about LLM advisers. Closed-loop outcomes additionally reflect the fallback priority heuristic. No human performance, calibrated trust, operational safety or physical fidelity claims are supported. Run the configured real-model arms and a checker ablation before drawing LLM conclusions.
