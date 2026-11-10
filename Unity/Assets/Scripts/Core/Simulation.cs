using System;
using System.Collections.Generic;

namespace RecycleGuard
{
    [Serializable] public class ActionCommand
    {
        public string kind = "wait";
        public int zone = -1;
        public int revision;
        public ActionCommand() { }
        public ActionCommand(string k, int z, int r) { kind = k; zone = z; revision = r; }
    }
    [Serializable] public class ZoneState
    {
        public int id, heat, people, isolated;
        public string name;
        public ZoneState Copy() { return (ZoneState)MemberwiseClone(); }
    }
    [Serializable] public class ZoneObservation
    {
        public int id, heat, people, isolated, observedAt, age;
        public string name, source;
    }
    [Serializable] public class Observation
    {
        public string schema = "recycleguard.observation.v1";
        public int seed, tick, revision, water, crews, horizon, damage;
        public string scenario, status;
        public ZoneObservation[] zones;
    }
    [Serializable] public class WorldSnapshot
    {
        public int tick, water, crews, damage, evacuated, invalidActions;
        public string status;
        public ZoneState[] zones;
    }
    [Serializable] public class StepResult
    {
        public bool accepted, advanced;
        public string reason;
        public Observation observation;
        public WorldSnapshot truth;
    }
    [Serializable] public class AuditEvent
    {
        public int tick;
        public string decision, note;
        public ActionCommand action;
        public bool accepted;
        public string reason;
        public WorldSnapshot after;
    }
    [Serializable] public class SessionLog
    {
        public string schema = "recycleguard.replay.v1";
        public int seed;
        public string scenario;
        public List<AuditEvent> events = new List<AuditEvent>();
    }

    // This file is compiled unchanged by both Unity and the headless experiment host.
    // Discrete, fictional training dynamics: these numbers are not fire physics or tactics.
    public sealed class Simulation
    {
        public const int Horizon = 32;
        public const int Freshness = 2;
        public readonly int Seed;
        public readonly string Scenario;
        public readonly SessionLog Log;
        private uint rng;
        private int tick, water = 18, damage, evacuated, invalid;
        private string status = "active";
        private readonly ZoneState[] zones = new ZoneState[4];
        private readonly List<int> releases = new List<int>();
        private readonly List<ZoneState[]> history = new List<ZoneState[]>();
        private readonly int[] reconUntil = { -1, -1, -1, -1 };
        public Simulation(int seed, string scenario)
        {
            if (scenario != "reliable" && scenario != "delayed" && scenario != "dropout")
                throw new ArgumentException("Unknown scenario");
            Seed = seed; Scenario = scenario; rng = unchecked((uint)seed) ^ 0x9e3779b9u;
            string[] names = { "Battery intake", "Sorting hall", "Materials store", "Loading yard" };
            for (int i = 0; i < 4; i++) zones[i] = new ZoneState { id = i, name = names[i], heat = i == 0 ? 48 + Next(13) : 5 + Next(9), people = 1 + Next(4), isolated = 0 };
            history.Add(CloneZones());
            Log = new SessionLog { seed = seed, scenario = scenario };
        }
        private int Next(int max) { rng = unchecked(1664525u * rng + 1013904223u); return (int)((rng >> 8) % (uint)max); }
        private ZoneState[] CloneZones() { var copy = new ZoneState[4]; for (int i = 0; i < 4; i++) copy[i] = zones[i].Copy(); return copy; }
        public WorldSnapshot Snapshot()
        { return new WorldSnapshot { tick = tick, water = water, crews = 2 - releases.Count, damage = damage, evacuated = evacuated, invalidActions = invalid, status = status, zones = CloneZones() }; }
        public Observation Observe()
        {
            var result = new Observation { seed = Seed, scenario = Scenario, tick = tick, revision = tick, water = water, crews = 2 - releases.Count, horizon = Horizon, damage = damage, status = status, zones = new ZoneObservation[4] };
            for (int i = 0; i < 4; i++)
            {
                bool recon = tick <= reconUntil[i];
                int at = recon || Scenario == "reliable" ? tick : Math.Max(0, tick - (Scenario == "delayed" ? 3 : 1));
                bool missing = !recon && Scenario == "dropout" && ((unchecked((uint)Seed) + (uint)(tick / 3) + (uint)i) % 3 == 0);
                var z = history[at][i];
                result.zones[i] = new ZoneObservation { id = i, name = z.name, heat = missing ? -1 : z.heat, people = missing ? -1 : z.people, isolated = missing ? -1 : z.isolated, observedAt = missing ? -1 : at, age = missing ? -1 : tick - at, source = recon ? "recon" : missing ? "unavailable" : "telemetry" };
            }
            return result;
        }
        public static string EvidenceViolation(Observation o, ActionCommand a)
        {
            if (o == null || a == null) return "MALFORMED: observation/action absent";
            if (o.status != "active") return "TERMINAL: incident ended";
            if (a.revision != o.revision) return "STALE_REVISION: request new advice";
            if (a.kind == "wait") return a.zone == -1 ? "" : "TARGET: wait requires zone -1";
            if (a.zone < 0 || a.zone >= o.zones.Length) return "TARGET: unknown zone";
            if (a.kind == "inspect") return "";
            if (a.kind != "evacuate" && a.kind != "isolate" && a.kind != "suppress") return "ACTION: unknown action";
            var z = o.zones[a.zone];
            if (z.age < 0 || z.age > Freshness) return "EVIDENCE: inspect missing/stale zone first";
            if (a.kind == "isolate") return z.isolated == 0 ? "" : "POWER: isolation not required or unknown";
            if (o.crews < 1) return "CREW: no crew available";
            if (a.kind == "evacuate") return z.people > 0 ? "" : "PEOPLE: no confirmed occupants";
            if (z.isolated != 1) return "POWER: confirmed isolation required";
            if (z.people != 0) return "PEOPLE: confirmed empty zone required";
            if (z.heat < 25) return "HEAT: no confirmed actionable heat";
            if (o.water < 2) return "WATER: two units required";
            return "";
        }
        public string TruthViolation(ActionCommand a)
        {
            string evidence = EvidenceViolation(Observe(), a);
            if (evidence.Length > 0) return evidence;
            if (a.kind == "wait" || a.kind == "inspect") return "";
            var z = zones[a.zone];
            if (a.kind == "evacuate" && z.people == 0) return "TRUTH: zone already empty";
            if (a.kind == "isolate" && z.isolated == 1) return "TRUTH: zone already isolated";
            if (a.kind == "suppress" && (z.people != 0 || z.isolated != 1 || z.heat < 25)) return "TRUTH: suppression precondition failed";
            return "";
        }
        public StepResult Step(ActionCommand action, string decision, string note)
        {
            int before = tick;
            string reason = TruthViolation(action);
            bool accepted = reason.Length == 0;
            // Stale requests do not consume time. Invalid current proposals cost one decision tick.
            bool advanced = status == "active" && action != null && action.revision == tick;
            if (advanced)
            {
                if (accepted)
                {
                    if (action.kind == "inspect") reconUntil[action.zone] = tick + 3;
                    if (action.kind == "isolate") zones[action.zone].isolated = 1;
                    if (action.kind == "evacuate") { evacuated += zones[action.zone].people; zones[action.zone].people = 0; releases.Add(tick + 2); }
                    if (action.kind == "suppress") { water -= 2; zones[action.zone].heat = Math.Max(0, zones[action.zone].heat - 38); releases.Add(tick + 2); }
                }
                else invalid++;
                Advance();
            }
            var snapshot = Snapshot();
            Log.events.Add(new AuditEvent { tick = before, decision = decision ?? "manual", note = note ?? "", action = action, accepted = accepted, reason = accepted ? "Applied" : reason, after = snapshot });
            return new StepResult { accepted = accepted, advanced = advanced, reason = accepted ? "Applied" : reason, observation = Observe(), truth = snapshot };
        }
        public void RecordDecision(string decision, string note)
        { Log.events.Add(new AuditEvent { tick = tick, decision = decision, note = note, accepted = false, reason = "No simulation time consumed", after = Snapshot() }); }
        private void Advance()
        {
            int[] old = new int[4]; for (int i = 0; i < 4; i++) old[i] = zones[i].heat;
            for (int i = 0; i < 4; i++)
            {
                int growth = old[i] >= 25 ? (zones[i].isolated == 1 ? 1 : 3) + Next(3) : -1;
                // Ring adjacency provides simple cascading risk without pretending to model physics.
                if (old[(i + 1) % 4] >= 75 || old[(i + 3) % 4] >= 75) growth += 5;
                zones[i].heat = Math.Max(0, Math.Min(100, old[i] + growth));
                if (zones[i].heat >= 80) damage += 1 + zones[i].people;
            }
            tick++;
            releases.RemoveAll(delegate(int release) { return release <= tick; });
            bool success = true; for (int i = 0; i < 4; i++) if (zones[i].people > 0 || zones[i].heat >= 25) success = false;
            if (success) status = "contained";
            else if (damage >= 45) status = "escalated";
            else if (tick >= Horizon) status = "timeout";
            history.Add(CloneZones());
        }
        public static Simulation Replay(SessionLog log)
        {
            if (log == null || log.schema != "recycleguard.replay.v1") throw new ArgumentException("Unsupported replay schema");
            var s = new Simulation(log.seed, log.scenario);
            foreach (var e in log.events)
            {
                if (e.tick != s.tick) throw new InvalidOperationException("Replay tick mismatch");
                if (e.action != null) s.Step(e.action, e.decision, e.note); else s.RecordDecision(e.decision, e.note);
                var actual = s.Snapshot();
                if (!Same(actual, e.after)) throw new InvalidOperationException("Replay state mismatch at tick " + e.tick);
            }
            return s;
        }
        public static bool Same(WorldSnapshot a, WorldSnapshot b)
        {
            if (a == null || b == null || a.tick != b.tick || a.water != b.water || a.crews != b.crews || a.damage != b.damage || a.evacuated != b.evacuated || a.invalidActions != b.invalidActions || a.status != b.status || b.zones == null || a.zones.Length != b.zones.Length) return false;
            for (int i = 0; i < a.zones.Length; i++) if (a.zones[i].heat != b.zones[i].heat || a.zones[i].people != b.zones[i].people || a.zones[i].isolated != b.zones[i].isolated) return false;
            return true;
        }
    }
}
