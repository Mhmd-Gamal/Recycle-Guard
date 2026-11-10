"""Observation-only policy. No simulator truth or hidden state enters this module."""
import json
import os
import time
import urllib.request
from .models import Action, Advice, AdviceRequest, Observation

KINDS = ("inspect", "evacuate", "isolate", "suppress")


def violation(o: Observation, a: Action) -> str:
    if o.status != "active": return "TERMINAL: incident ended"
    if a.revision != o.revision: return "STALE_REVISION: request new advice"
    if a.kind == "wait": return "" if a.zone == -1 else "TARGET: wait requires zone -1"
    if not 0 <= a.zone < 4: return "TARGET: unknown zone"
    if a.kind == "inspect": return ""
    if a.kind not in KINDS: return "ACTION: unknown action"
    z = o.zones[a.zone]
    if z.age < 0 or z.age > 2: return "EVIDENCE: inspect missing/stale zone first"
    if a.kind == "isolate": return "" if z.isolated == 0 else "POWER: isolation not required or unknown"
    if o.crews < 1: return "CREW: no crew available"
    if a.kind == "evacuate": return "" if z.people > 0 else "PEOPLE: no confirmed occupants"
    if z.isolated != 1: return "POWER: confirmed isolation required"
    if z.people != 0: return "PEOPLE: confirmed empty zone required"
    if z.heat < 25: return "HEAT: no confirmed actionable heat"
    if o.water < 2: return "WATER: two units required"
    return ""


def candidates(o):
    return [Action(kind=k, zone=z.id, revision=o.revision) for z in o.zones for k in KINDS] + [Action(kind="wait", zone=-1, revision=o.revision)]


def priority(o, a):
    if a.kind == "wait": return -100
    z = o.zones[a.zone]
    heat = max(30, z.heat) if z.age < 0 else z.heat
    if a.kind == "inspect": return 65 + heat / 2 if z.age < 0 or z.age > 2 else -20
    if a.kind == "evacuate": return 80 + heat + z.people * 3
    if a.kind == "isolate": return 60 + heat if heat >= 25 else 0
    if a.kind == "suppress": return 100 + heat
    return -1000


def shield_violation(o, a, strict=True):
    problem = violation(o, a)
    if problem: return problem
    if strict and a.kind in ("evacuate", "isolate", "suppress") and o.zones[a.zone].age != 0:
        return "CURRENT_EVIDENCE: operational action requires age 0; inspect first"
    return ""


def ranked(o, exclude=(), strict=False):
    blocked = {(a.kind, a.zone) for a in exclude}
    def score(a):
        if strict and a.kind == "inspect" and o.zones[a.zone].age != 0:
            return 65 + max(30, o.zones[a.zone].heat) / 2
        return priority(o, a)
    return sorted((a for a in candidates(o) if not shield_violation(o, a, strict) and (a.kind, a.zone) not in blocked), key=lambda a: (-score(a), a.zone, a.kind))


def scripted(o):
    # Fixed-priority baseline: evacuation, then heat response; no missing-data repair.
    for z in o.zones:
        if z.people > 0: return Action(kind="evacuate", zone=z.id, revision=o.revision)
    for z in o.zones:
        if z.heat >= 25:
            return Action(kind="isolate" if z.isolated == 0 else "suppress", zone=z.id, revision=o.revision)
    return Action(kind="wait", zone=-1, revision=o.revision)


def offline_proposal(o):
    # Deliberately fallible deterministic proposal generator. NOT an LLM or LLM proxy.
    # Used to exercise the shield under unsafe, stale and valid proposal conditions.
    choice = (o.seed + 7 * o.tick) % 5
    hot = max(o.zones, key=lambda z: (z.heat, -z.id))
    if choice == 0: return Action(kind="suppress", zone=hot.id, revision=o.revision)
    if choice == 1: return Action(kind="evacuate", zone=o.tick % 4, revision=o.revision)
    if choice == 2: return Action(kind="isolate", zone=hot.id, revision=o.revision)
    if choice == 3: return scripted(o)
    options = ranked(o)
    return options[0] if options else Action(kind="wait", zone=-1, revision=o.revision)


def llm_proposal(o):
    base = os.environ.get("RECYCLEGUARD_LLM_URL", "").rstrip("/")
    model = os.environ.get("RECYCLEGUARD_LLM_MODEL", "")
    if not base or not model:
        raise RuntimeError("LLM not configured. Set RECYCLEGUARD_LLM_URL and RECYCLEGUARD_LLM_MODEL; offline modes do not require credentials.")
    prompt = (
        "You advise a fictional discrete emergency-training simulation, not real operations. "
        "Return only JSON {\"kind\":\"inspect|evacuate|isolate|suppress|wait\",\"zone\":0,\"revision\":0}. "
        "Use the observation revision. wait requires zone -1. Others require 0..3. "
        "Goal: evacuate all people and reduce all heat below 25 before tick 32. "
        "Unknown values are -1. Operational actions need evidence age 0..2. inspect refreshes one zone for 3 ticks. "
        "evacuate needs people>0 and one crew. isolate needs isolated=0. suppress requires isolated=1, "
        "people=0, heat>=25, water>=2 and one crew. It reduces heat by 38. Each action costs one tick. "
        "Crews release after two ticks; isolate slows growth. Recommend one next action."
    )
    payload = {"model": model, "temperature": 0, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": o.model_dump_json()}]}
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("RECYCLEGUARD_LLM_API_KEY")
    if key: headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(base + "/chat/completions", json.dumps(payload).encode(), headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    content = data["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return Action.model_validate_json(content)


def advise(request: AdviceRequest) -> Advice:
    started = time.perf_counter()
    o, mode = request.observation, request.mode
    if o.status != "active": raise ValueError("Incident ended; reset to request advice")
    if mode == "scripted": proposal, provider = scripted(o), "fixed-priority script"
    elif mode.startswith("offline"):
        proposal, provider = offline_proposal(o), "deterministic fault-injection fixture (NOT an LLM)"
    else:
        proposal, provider = llm_proposal(o), os.environ["RECYCLEGUARD_LLM_MODEL"]
    checked = "checked" in mode
    strict = checked and not mode.endswith("permissive")
    problem = shield_violation(o, proposal, strict) if checked else violation(o, proposal)
    blocked = any((proposal.kind, proposal.zone) == (x.kind, x.zone) for x in request.exclude)
    violations = ([problem] if problem else []) + (["HUMAN: excluded recommendation"] if blocked else [])
    options = ranked(o, request.exclude, strict)
    replace = blocked or (checked and bool(violations))
    if replace and not options: raise ValueError("No unexcluded valid action remains")
    action = options[0] if replace else proposal
    z = o.zones[action.zone] if 0 <= action.zone < 4 else None
    evidence = [f"Tick/revision {o.tick}; available crews {o.crews}; water {o.water}"]
    if z:
        evidence.append(f"Zone {z.id} {z.name}: heat={z.heat}, people={z.people}, isolated={z.isolated}; source={z.source}, observedAt={z.observedAt}, age={z.age}")
    missing = [f"{x.name}: {'missing' if x.age < 0 else 'stale (' + str(x.age) + ' ticks)'}" for x in o.zones if x.age < 0 or x.age > 2]
    reasons = {"inspect": "Acquire current evidence before committing resources.", "evacuate": "Prioritise confirmed occupants using an available crew.", "isolate": "Remove the modelled power contribution to heat growth.", "suppress": "Reduce modelled heat after checking isolation, occupancy and resources.", "wait": "Advance one decision tick; reassess resource availability and telemetry."}
    explanation = reasons.get(action.kind, "Unsupported raw proposal; simulator will validate it.")
    if replace: explanation = "Proposal replaced: " + "; ".join(violations) + ". " + explanation
    elif violations: explanation = "Unchecked proposal; violations: " + "; ".join(violations)
    plan = [f"Now: {action.kind} / zone {action.zone} (requires human approval)."]
    if z:
        if z.people != 0 and action.kind != "evacuate": plan.append("Next subgoal: confirm and clear occupants, if present.")
        if z.isolated != 1 and action.kind != "isolate": plan.append("Next subgoal: confirm isolation before heat suppression.")
        if z.heat >= 25 and action.kind != "suppress": plan.append("Then: reassess suppression prerequisites and resources.")
    plan.append("Reobserve and replan after every action; future steps are conditional, not queued.")
    return Advice(revision=o.revision, mode=mode, provider=provider, proposal=proposal, recommendation=action,
                  intervention=replace, violations=violations, explanation=explanation,
                  evidence=evidence, missing=missing, alternatives=[a for a in options if (a.kind, a.zone) != (action.kind, action.zone)][:3],
                  latency_ms=round((time.perf_counter() - started) * 1000, 4),
                  uncertainty="Evidence completeness/freshness only; no calibrated probability of safety or success.", plan=plan)
