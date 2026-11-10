import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timezone

from adviser.core import Core, ROOT
from adviser.models import AdviceRequest, Observation
from adviser.policy import advise, violation


def percentile(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs)-1, int((len(xs)-1)*q))] if xs else 0


def bootstrap_mean(xs):
    rng = random.Random(20261110)
    samples = [statistics.mean(rng.choices(xs, k=len(xs))) for _ in range(2000)]
    return [percentile(samples, .025), percentile(samples, .975)]


def run(args):
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    modes = ["scripted", "llm_raw", "llm_checked"] if args.llm else ["scripted", "offline_raw", "offline_checked_permissive", "offline_checked"]
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/"Unity/Assets/Scripts/Core/Simulation.cs", ROOT/"adviser/policy.py", ROOT/"adviser/models.py", Path(__file__)]}
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "seeds": seeds, "scenarios": ["reliable", "delayed", "dropout"], "modes": modes,
                "python": sys.version, "platform": platform.platform(), "source_sha256": source_hashes,
                "llm_experiment": args.llm, "interpretation": "Offline fixtures are NOT language models. Simulator guard rejects invalid actions in every arm; measured invalidity is attempted recommendations, not executed unsafe actions.",
                "protocol": "Matched initial seeds; closed-loop policies diverge. Equal-state shield probes on raw-policy trajectories. No failed episodes removed. Episode-level paired bootstrap (2000 resamples, RNG 20261110)."}
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    rows, probes = [], []
    with Core() as core, (output/"traces.jsonl").open("w", encoding="utf-8") as traces:
        for scenario in manifest["scenarios"]:
            for seed in seeds:
                for mode in modes:
                    raw = core.call("reset", seed=seed, scenario=scenario)
                    invalid = interventions = steps = 0
                    latencies = []
                    while raw["status"] == "active":
                        o = Observation.model_validate(raw)
                        # Provider failures abort the run; never silently switch an LLM arm to a fixture.
                        a = advise(AdviceRequest(observation=o, mode=mode))
                        check = core.call("validate", action=a.recommendation.model_dump())
                        if mode == "offline_raw":
                            shielded = advise(AdviceRequest(observation=o, mode="offline_checked"))
                            truth = core.call("validate", action=shielded.recommendation.model_dump())["truth"]
                            probes.append({"scenario": scenario, "seed": seed, "tick": o.tick, "raw_invalid": bool(check["truth"]), "checked_invalid": bool(truth), "same_proposal": a.proposal == shielded.proposal})
                        result = core.call("step", action=a.recommendation.model_dump(), decision=mode, note=a.explanation)
                        if not result["advanced"]: raise RuntimeError("Policy did not advance; stale/malformed proposal")
                        invalid += int(not result["accepted"])
                        interventions += int(a.intervention); steps += 1; latencies.append(a.latency_ms)
                        traces.write(json.dumps({"seed": seed, "scenario": scenario, "mode": mode, "observation": raw, "advice": a.model_dump(), "result": result}, separators=(",", ":"))+"\n")
                        raw = result["observation"]
                    final = core.call("snapshot")
                    log = core.call("log")
                    assert core.call("replay", log=log) == final
                    if seed == seeds[0] and scenario == "dropout" and mode.endswith("checked"):
                        (output/"example-replay.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
                    rows.append({"scenario": scenario, "seed": seed, "mode": mode, "steps": steps, "invalid": invalid, "invalid_rate": invalid/steps, "interventions": interventions,
                                 "contained": int(final["status"] == "contained"), "status": final["status"], "damage": final["damage"], "evacuated": final["evacuated"], "water_remaining": final["water"],
                                 "latency_median_ms": statistics.median(latencies), "latency_p95_ms": percentile(latencies, .95)})
            print(f"Completed {scenario}: {len(seeds)*len(modes)} episodes", flush=True)
    with (output/"episodes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (output/"equal-state-probes.json").write_text(json.dumps(probes, indent=2), encoding="utf-8")
    summary = []
    for scenario in manifest["scenarios"]:
        for mode in modes:
            group = [r for r in rows if r["scenario"] == scenario and r["mode"] == mode]
            summary.append({"scenario": scenario, "mode": mode, "episodes": len(group), "attempted_invalid_pct": 100*sum(r["invalid"] for r in group)/sum(r["steps"] for r in group),
                            "contained_pct": 100*statistics.mean(r["contained"] for r in group), "mean_damage": statistics.mean(r["damage"] for r in group), "mean_steps": statistics.mean(r["steps"] for r in group),
                            "median_policy_latency_ms": statistics.median(r["latency_median_ms"] for r in group)})
    pairs = []
    for scenario in manifest["scenarios"]:
        deltas = []
        for seed in seeds:
            by_mode = {r["mode"]: r for r in rows if r["scenario"] == scenario and r["seed"] == seed}
            deltas.append(100*(by_mode[modes[-1]]["invalid_rate"]-by_mode[modes[1]]["invalid_rate"]))
        pairs.append({"scenario": scenario, "checked_minus_raw_invalid_rate_pp": statistics.mean(deltas), "bootstrap_95_ci_pp": bootstrap_mean(deltas)})
    (output/"summary.json").write_text(json.dumps({"groups": summary, "paired_episode_differences": pairs, "equal_state_probe_count": len(probes), "raw_invalid_probes": sum(p["raw_invalid"] for p in probes), "checked_invalid_probes": sum(p["checked_invalid"] for p in probes)}, indent=2), encoding="utf-8")
    lines = ["# Measured evaluation results", "", manifest["interpretation"], "", f"{len(rows)} completed episodes; {len(seeds)} matched seeds per scenario/policy. All episode replays verified.", "", "| Scenario | Policy | Invalid attempts | Contained | Mean damage | Mean ticks | Median policy ms |", "|---|---|---:|---:|---:|---:|---:|"]
    for r in summary: lines.append(f"| {r['scenario']} | {r['mode']} | {r['attempted_invalid_pct']:.1f}% | {r['contained_pct']:.1f}% | {r['mean_damage']:.1f} | {r['mean_steps']:.1f} | {r['median_policy_latency_ms']:.3f} |")
    lines += ["", "Invalid attempts are pooled across decisions; paired confidence intervals below use per-episode rates. Latency includes policy construction/checking only, excluding C# IPC, browser rendering and network calls in offline mode.", "", "## Paired differences (checked minus raw)", ""]
    for p in pairs: lines.append(f"- {p['scenario']}: {p['checked_minus_raw_invalid_rate_pp']:.2f} percentage points; paired bootstrap 95% interval [{p['bootstrap_95_ci_pp'][0]:.2f}, {p['bootstrap_95_ci_pp'][1]:.2f}].")
    if probes: lines += ["", f"Equal-state probes: {len(probes)}; raw invalid {sum(p['raw_invalid'] for p in probes)}; shielded invalid {sum(p['checked_invalid'] for p in probes)}. Each pair used the same proposal and observation."]
    lines += ["", "## Interpretation limits", "", "The checker explicitly encodes the validity rules, so lower invalidity is an expected engineering property, not evidence of novel AI reasoning. These synthetic fixtures cannot answer the proposed research question about LLM advisers. Closed-loop outcomes additionally reflect the fallback priority heuristic. No human performance, calibrated trust, operational safety or physical fidelity claims are supported. Run the configured real-model arms and a checker ablation before drawing LLM conclusions."]
    (output/"RESULTS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"Results: {output.resolve()}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=30)
    p.add_argument("--seed-start", type=int, default=1000)
    p.add_argument("--output", default="artifacts/evaluation")
    p.add_argument("--llm", action="store_true")
    args = p.parse_args()
    if args.seeds < 2 or args.seed_start < -2147483648 or args.seed_start + args.seeds > 2147483648: p.error("Use >=2 seeds within signed 32-bit range")
    run(args)
