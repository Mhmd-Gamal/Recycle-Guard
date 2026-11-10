import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from adviser.app import app
from adviser.models import Action, AdviceRequest, Observation
from adviser.policy import advise, violation


def test_shield_replaces_bad_proposal(core):
    o = Observation.model_validate(core.call("reset", seed=0))
    raw = advise(AdviceRequest(observation=o, mode="offline_raw"))
    checked = advise(AdviceRequest(observation=o, mode="offline_checked"))
    assert raw.proposal == checked.proposal
    assert violation(o, raw.recommendation)
    assert not violation(o, checked.recommendation)
    assert checked.intervention and "NOT an LLM" in checked.provider


@pytest.mark.parametrize("mode", ["offline_checked", "offline_raw", "scripted"])
def test_human_alternative_excludes_previous(core, mode):
    o = Observation.model_validate(core.call("observe"))
    first = advise(AdviceRequest(observation=o, mode=mode))
    second = advise(AdviceRequest(observation=o, mode=mode, exclude=[first.recommendation]))
    assert second.recommendation != first.recommendation
    assert "HUMAN" in " ".join(second.violations)


def test_bad_observation_rejected(core):
    raw = core.call("observe")
    raw["zones"][0]["observedAt"] = 9
    with pytest.raises(ValidationError): Observation.model_validate(raw)


def test_strict_checker_requires_current_evidence(core):
    from adviser.policy import shield_violation
    core.call("reset", seed=42, scenario="dropout")
    core.call("step", action={"kind": "evacuate", "zone": 1, "revision": 0})
    o = Observation.model_validate(core.call("observe"))
    a = Action(kind="evacuate", zone=1, revision=1)
    assert not violation(o, a)  # delayed observation still says occupied
    assert shield_violation(o, a).startswith("CURRENT_EVIDENCE")
    assert core.call("validate", action=a.model_dump())["truth"].startswith("TRUTH")


def test_no_hidden_state_in_advice(core):
    raw = core.call("observe")
    assert "truth" not in raw and "rng" not in raw
    raw["truth"] = core.call("snapshot")
    with pytest.raises(ValidationError): Observation.model_validate(raw)


def test_unconfigured_llm_not_silently_substituted(core, monkeypatch):
    monkeypatch.delenv("RECYCLEGUARD_LLM_URL", raising=False)
    with TestClient(app) as c:
        r = c.post("/v1/advice", json={"observation": core.call("observe"), "mode": "llm_checked"})
        assert r.status_code == 503


def test_operator_workflow_and_verified_replay():
    with TestClient(app) as c:
        data = c.post("/v1/sessions", json={"seed": 42, "scenario": "dropout"}).json()
        sid = data["id"]; path = "/v1/sessions/" + sid
        first = c.post(path+"/advice", json={}).json()
        assert first["advice"] and first["observation"]["tick"] == 0
        alternative = c.post(path+"/advice", json={"alternative": True}).json()
        assert alternative["advice"]["recommendation"] != first["advice"]["recommendation"]
        rejected = c.post(path+"/decision", json={"decision": "reject", "note": "Request clearer evidence"}).json()
        assert rejected["observation"]["tick"] == 0 and rejected["advice"] is None
        assert c.post(path+"/decision", json={"decision": "accept"}).status_code == 409
        for _ in range(32):
            data = c.post(path+"/advice", json={}).json()
            if "observation" not in data: break
            applied = c.post(path+"/decision", json={"decision": "accept", "note": "Reviewed"}).json()
            assert applied["result"]["accepted"]
            if applied["observation"]["status"] != "active": break
        log = c.get(path+"/replay").json()
        assert any(e["decision"] == "reject" for e in log["events"])
        assert c.post("/v1/replay/verify", json=log).json()["verified"]
        assert c.delete(path).status_code == 200
        assert c.get(path).status_code == 404


def test_manual_invalid_and_stale_actions_are_blocked():
    with TestClient(app) as c:
        sid = c.post("/v1/sessions", json={}).json()["id"]
        path = f"/v1/sessions/{sid}/decision"
        r = c.post(path, json={"decision": "manual", "action": {"kind": "suppress", "zone": 0, "revision": 0}}).json()
        assert not r["result"]["accepted"] and r["observation"]["water"] == 18
        r = c.post(path, json={"decision": "manual", "action": {"kind": "inspect", "zone": 0, "revision": 0}}).json()
        assert not r["result"]["advanced"] and r["observation"]["tick"] == 1


def test_cross_origin_writes_rejected():
    with TestClient(app) as c:
        assert c.post("/v1/sessions", json={}, headers={"Origin": "https://example.org"}).status_code == 403
