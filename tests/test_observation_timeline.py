"""Observation-timestamp panel logic (ObservationTimeline.cs), exercised through the C# host.

The Unity client draws these rows. The tests check that the panel reads observations only,
and that it never disagrees with the C# evidence check about which readings are too old.
"""
import random
import pytest

SCENARIOS = ["reliable", "delayed", "dropout"]
FRESHNESS = 2  # Simulation.Freshness
TELEMETRY_LAG = {"reliable": 0, "delayed": 3, "dropout": 1}
TARGETED = ("evacuate", "isolate", "suppress")
KINDS = ["inspect", "evacuate", "isolate", "suppress", "wait"]


def expected_freshness(age):
    if age < 0: return "missing"
    if age == 0: return "current"
    return "aged" if age <= FRESHNESS else "stale"


def random_step(core, o, rng):
    kind = rng.choice(["wait", "inspect", "inspect", "evacuate", "isolate"])
    zone = -1 if kind == "wait" else rng.randrange(4)
    return core.call("step", action=dict(kind=kind, zone=zone, revision=o["revision"]))["observation"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_panel_freshness_agrees_with_evidence_check(core, scenario):
    rng = random.Random(77)
    seen = set()
    for seed in range(6):
        o = core.call("reset", seed=seed, scenario=scenario)
        while o["status"] == "active":
            rows = core.call("timeline")
            assert [r["id"] for r in rows] == [0, 1, 2, 3]
            for z, row in zip(o["zones"], rows):
                freshness = expected_freshness(z["age"])
                seen.add(freshness)
                assert row["freshness"] == freshness
                assert row["actionable"] == (freshness in ("current", "aged"))
                assert (row["name"], row["observedAt"], row["age"], row["source"]) == (z["name"], z["observedAt"], z["age"], z["source"])
                # The panel and the validator must agree on every zone, every tick.
                for kind in TARGETED:
                    evidence = core.call("validate", action=dict(kind=kind, zone=z["id"], revision=o["revision"]))["evidence"]
                    assert evidence.startswith("EVIDENCE") == (not row["actionable"])
                # The scenario summaries shown to the operator describe these lags.
                if z["source"] == "telemetry": assert z["age"] == min(o["tick"], TELEMETRY_LAG[scenario])
                if z["source"] == "recon": assert z["age"] == 0
            o = random_step(core, o, rng)
    expected = {"reliable": {"current"}, "delayed": {"current", "aged", "stale"}, "dropout": {"current", "aged", "missing"}}
    assert seen == expected[scenario]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_preflight_matches_validator_for_every_manual_action(core, scenario):
    rng = random.Random(5)
    blocked = 0
    for seed in (3, 42):
        o = core.call("reset", seed=seed, scenario=scenario)
        while o["status"] == "active":
            for zone in range(4):
                rows = core.call("preflight", zone=zone)
                assert [r["kind"] for r in rows] == KINDS
                for row in rows:
                    target = -1 if row["kind"] == "wait" else zone
                    assert row["zone"] == target
                    evidence = core.call("validate", action=dict(kind=row["kind"], zone=target, revision=o["revision"]))["evidence"]
                    assert row["violation"] == evidence
                    assert row["allowed"] == (evidence == "")
                    blocked += not row["allowed"]
            o = random_step(core, o, rng)
    assert blocked  # the check is not vacuous


def test_panel_shows_lagged_observation_not_ground_truth(core):
    core.call("reset", seed=42, scenario="delayed")
    for tick in range(3): core.call("step", action=dict(kind="wait", zone=-1, revision=tick))
    o, truth, rows = core.call("observe"), core.call("snapshot"), core.call("timeline")
    assert truth["zones"][0]["heat"] != o["zones"][0]["heat"]  # the fire moved on while telemetry lagged
    for z, row in zip(o["zones"], rows):
        assert row["reading"].startswith(f"Heat {z['heat']} | People {z['people']} | ")
        assert row["freshness"] == "stale" and not row["actionable"]
        assert row["stamp"] == "Observed T+0 | 3 ticks old | telemetry - too old to act on"
    assert f"Heat {truth['zones'][0]['heat']} " not in rows[0]["reading"]


def test_missing_reading_is_shown_as_unknown(core):
    o = core.call("reset", seed=42, scenario="dropout")
    rows = core.call("timeline")
    missing = [row for z, row in zip(o["zones"], rows) if z["source"] == "unavailable"]
    assert missing
    for row in missing:
        assert row["freshness"] == "missing" and not row["actionable"]
        assert row["reading"] == "Heat ? | People ? | Isolation ?"
        assert row["stamp"] == "No reading at T+0 - inspect to observe"
        assert not any(ch.isdigit() for ch in row["reading"])


def test_inspection_refreshes_row_until_recon_expires(core):
    core.call("reset", seed=42, scenario="delayed")
    for tick in range(3): core.call("step", action=dict(kind="wait", zone=-1, revision=tick))
    assert core.call("timeline")[0]["freshness"] == "stale"
    core.call("step", action=dict(kind="inspect", zone=0, revision=3))
    for tick in (4, 5, 6):
        row = core.call("timeline")[0]
        assert (row["freshness"], row["source"], row["observedAt"]) == ("current", "recon", tick)
        assert row["stamp"] == f"Observed T+{tick} | current | recon"
        assert core.call("timeline")[1]["freshness"] == "stale"  # only the inspected zone is repaired
        core.call("step", action=dict(kind="wait", zone=-1, revision=tick))
    row = core.call("timeline")[0]
    assert (row["freshness"], row["source"]) == ("stale", "telemetry")


def test_scenario_summaries_and_unknown_scenario(core):
    labels = {s: core.call("scenario_summary", scenario=s) for s in SCENARIOS}
    assert [labels[s]["label"] for s in SCENARIOS] == ["Reliable", "Delayed", "Dropout"]
    assert "3 ticks late" in labels["delayed"]["summary"] and f"{FRESHNESS}-tick evidence limit" in labels["delayed"]["summary"]
    assert "1 tick old" in labels["dropout"]["summary"] and "never as zero" in labels["dropout"]["summary"]
    with pytest.raises(ValueError, match="Unknown scenario"): core.call("scenario_summary", scenario="foggy")


@pytest.mark.parametrize("scenario,allowed", [("reliable", {"current"}), ("delayed", {"stale"}), ("dropout", {"aged", "missing"})])
def test_unity_smoke_sequence_assumptions_hold_in_core(core, scenario, allowed):
    """The Unity player's -rgSmoke run performs this exact sequence and asserts the same outcome."""
    core.call("reset", seed=42, scenario=scenario)
    r = core.call("step", action=dict(kind="suppress", zone=0, revision=0), decision="test")
    assert not r["accepted"] and r["truth"]["water"] == 18
    for tick in (1, 2): r = core.call("step", action=dict(kind="wait", zone=-1, revision=tick), decision="test")
    assert r["truth"]["status"] == "active" and r["truth"]["tick"] == 3
    assert {row["freshness"] for row in core.call("timeline")} == allowed
    core.call("replay", log=core.call("log"))
