using System;

namespace RecycleGuard
{
    // One row of the operator's observation-timestamp panel.
    [Serializable] public class ZoneEvidence
    {
        public int id, observedAt, age;
        public string name, source, freshness, reading, stamp;
        public bool actionable;
    }
    // Outcome of the observation-only evidence check for one manual action.
    [Serializable] public class ActionPreflight
    {
        public string kind, violation;
        public int zone;
        public bool allowed;
    }

    // Presentation logic for observation timestamps. Like Simulation.cs, this file is compiled
    // unchanged by Unity and by the headless test host, so it can be tested without an Editor.
    // It reads observations only, never ground truth, and reuses Simulation.Freshness and
    // Simulation.EvidenceViolation so the panel cannot disagree with the validator about stale evidence.
    public static class ObservationTimeline
    {
        public const string Current = "current", Aged = "aged", Stale = "stale", Missing = "missing";
        public static readonly string[] Kinds = { "inspect", "evacuate", "isolate", "suppress", "wait" };

        public static string Classify(ZoneObservation z)
        {
            if (z == null || z.age < 0) return Missing;
            if (z.age == 0) return Current;
            return z.age <= Simulation.Freshness ? Aged : Stale;
        }
        // True when the reading is recent enough for evacuate, isolate or suppress to pass the evidence check.
        public static bool Actionable(ZoneObservation z)
        {
            string freshness = Classify(z);
            return freshness == Current || freshness == Aged;
        }
        private static string Value(int value) { return value < 0 ? "?" : value.ToString(); }
        public static string Reading(ZoneObservation z)
        {
            if (z == null) return "Heat ? | People ? | Isolation ?";
            string isolation = z.isolated < 0 ? "Isolation ?" : z.isolated == 1 ? "Isolated" : "Not isolated";
            return "Heat " + Value(z.heat) + " | People " + Value(z.people) + " | " + isolation;
        }
        public static string Stamp(ZoneObservation z, int tick)
        {
            string freshness = Classify(z);
            if (freshness == Missing) return "No reading at T+" + tick + " - inspect to observe";
            string age = z.age == 0 ? "current" : z.age + (z.age == 1 ? " tick old" : " ticks old");
            return "Observed T+" + z.observedAt + " | " + age + " | " + z.source + (freshness == Stale ? " - too old to act on" : "");
        }
        public static ZoneEvidence[] Describe(Observation o)
        {
            if (o == null || o.zones == null) return new ZoneEvidence[0];
            var rows = new ZoneEvidence[o.zones.Length];
            for (int i = 0; i < rows.Length; i++)
            {
                var z = o.zones[i];
                rows[i] = new ZoneEvidence { id = z.id, name = z.name, observedAt = z.observedAt, age = z.age, source = z.source, freshness = Classify(z), reading = Reading(z), stamp = Stamp(z, o.tick), actionable = Actionable(z) };
            }
            return rows;
        }
        // Evidence check for every manual action on one zone, from the observation alone.
        // A passing preflight is not a guarantee: the simulation revalidates against the real state.
        public static ActionPreflight[] Preflight(Observation o, int zone)
        {
            var rows = new ActionPreflight[Kinds.Length];
            for (int i = 0; i < Kinds.Length; i++)
            {
                int target = Kinds[i] == "wait" ? -1 : zone;
                string violation = Simulation.EvidenceViolation(o, new ActionCommand(Kinds[i], target, o == null ? 0 : o.revision));
                rows[i] = new ActionPreflight { kind = Kinds[i], zone = target, violation = violation, allowed = violation.Length == 0 };
            }
            return rows;
        }
        public static string ScenarioLabel(string scenario)
        {
            if (scenario == "reliable") return "Reliable";
            if (scenario == "delayed") return "Delayed";
            if (scenario == "dropout") return "Dropout";
            throw new ArgumentException("Unknown scenario");
        }
        // Operator-facing description of each telemetry model. tests/test_observation_timeline.py
        // checks these statements against the observations the simulation actually produces.
        public static string ScenarioSummary(string scenario)
        {
            if (scenario == "reliable") return "Reliable telemetry: every zone reports the current tick.";
            if (scenario == "delayed") return "Delayed telemetry: readings arrive 3 ticks late, past the " + Simulation.Freshness + "-tick evidence limit. Inspect a zone before acting on it.";
            if (scenario == "dropout") return "Intermittent dropout: readings are 1 tick old and zones drop out in rotation. Missing values show as ?, never as zero.";
            throw new ArgumentException("Unknown scenario");
        }
    }
}
