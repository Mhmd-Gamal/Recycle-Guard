import copy
import random
import pytest
from adviser.models import Action, AdviceRequest, Observation
from adviser.policy import advise, candidates, violation


@pytest.mark.parametrize("scenario", ["reliable", "delayed", "dropout"])
@pytest.mark.parametrize("seed", [0, 1, 42, -7, 2147483647])
def test_determinism_and_replay(core, scenario, seed):
    def run():
        o = core.call("reset", seed=seed, scenario=scenario)
        snapshots = []
        while o["status"] == "active":
            a = advise(AdviceRequest(observation=Observation.model_validate(o)))
            r = core.call("step", action=a.recommendation.model_dump())
            snapshots.append(r["truth"])
            o = r["observation"]
        log = core.call("log")
        assert core.call("replay", log=log) == snapshots[-1]
        return snapshots
    assert run() == run()


def test_unsafe_suppression_does_not_spend_resources(core):
    o = core.call("reset")
    r = core.call("step", action=dict(kind="suppress", zone=0, revision=0))
    assert not r["accepted"] and r["advanced"]
    assert r["truth"]["water"] == 18 and r["truth"]["crews"] == 2
    assert r["truth"]["invalidActions"] == 1 and r["truth"]["tick"] == 1


def test_stale_request_cannot_advance(core):
    core.call("step", action=dict(kind="inspect", zone=0, revision=0))
    before = core.call("snapshot")
    r = core.call("step", action=dict(kind="evacuate", zone=0, revision=0))
    assert not r["accepted"] and not r["advanced"]
    assert r["truth"] == before


def test_crew_commitment_and_release(core):
    r = core.call("step", action=dict(kind="evacuate", zone=0, revision=0))
    assert r["truth"]["crews"] == 1
    assert r["truth"]["zones"][0]["people"] == 0
    r = core.call("step", action=dict(kind="evacuate", zone=1, revision=1))
    assert r["truth"]["crews"] == 1  # first crew returned, second remains committed
    r = core.call("step", action=dict(kind="wait", zone=-1, revision=2))
    assert r["truth"]["crews"] == 2


def test_inspection_repairs_delayed_evidence(core):
    core.call("reset", scenario="delayed")
    for tick in range(3): core.call("step", action=dict(kind="wait", zone=-1, revision=tick))
    before = core.call("observe")
    assert before["zones"][0]["age"] == 3
    a = dict(kind="evacuate", zone=0, revision=3)
    assert core.call("validate", action=a)["evidence"].startswith("EVIDENCE")
    r = core.call("step", action=dict(kind="inspect", zone=0, revision=3))
    assert r["observation"]["zones"][0]["age"] == 0
    assert r["observation"]["zones"][0]["source"] == "recon"


def test_missing_values_never_encoded_as_safe_zero(core):
    o = core.call("reset", seed=42, scenario="dropout")
    missing = [z for z in o["zones"] if z["source"] == "unavailable"]
    assert missing
    for z in missing:
        assert [z[k] for k in ("heat", "people", "isolated", "age", "observedAt")] == [-1] * 5


def test_truth_tampering_detected(core):
    core.call("step", action=dict(kind="wait", zone=-1, revision=0))
    log = core.call("log")
    log["events"][0]["after"]["water"] = 0
    with pytest.raises(ValueError, match="mismatch"): core.call("replay", log=log)


@pytest.mark.parametrize("scenario", ["reliable", "delayed", "dropout"])
def test_python_csharp_constraint_parity_and_resource_invariants(core, scenario):
    rng = random.Random(2026)
    for seed in range(8):
        raw = core.call("reset", seed=seed, scenario=scenario)
        while raw["status"] == "active":
            o = Observation.model_validate(raw)
            actions = candidates(o) + [Action(kind="bad", zone=0, revision=o.revision), Action(kind="wait", zone=2, revision=o.revision), Action(kind="suppress", zone=99, revision=o.revision), Action(kind="inspect", zone=0, revision=o.revision+1)]
            for a in actions:
                assert core.call("validate", action=a.model_dump())["evidence"] == violation(o, a)
            r = core.call("step", action=rng.choice(candidates(o)).model_dump())
            assert 0 <= r["truth"]["water"] <= 18
            assert 0 <= r["truth"]["crews"] <= 2
            assert all(0 <= z["heat"] <= 100 and z["people"] >= 0 for z in r["truth"]["zones"])
            raw = r["observation"]


def test_terminal_state_is_immutable(core):
    for tick in range(32):
        r = core.call("step", action=dict(kind="wait", zone=-1, revision=tick))
        if r["truth"]["status"] != "active": break
    before = core.call("snapshot")
    r = core.call("step", action=dict(kind="inspect", zone=0, revision=before["tick"]))
    assert not r["advanced"] and not r["accepted"] and r["truth"] == before
