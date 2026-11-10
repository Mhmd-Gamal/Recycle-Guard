using System;
using System.IO;
using System.Web.Script.Serialization;
using RecycleGuard;

public class Request
{
    public string op = "observe", scenario = "reliable", decision = "experiment", note = "";
    public int seed = 42;
    public ActionCommand action;
    public SessionLog log;
}
public class Program
{
    public static int Main(string[] args)
    {
        var json = new JavaScriptSerializer { MaxJsonLength = 16000000 };
        var sim = new Simulation(42, "reliable");
        string line;
        while ((line = Console.ReadLine()) != null)
        {
            try
            {
                var request = json.Deserialize<Request>(line);
                object result;
                switch (request.op)
                {
                    case "reset": sim = new Simulation(request.seed, request.scenario); result = sim.Observe(); break;
                    case "observe": result = sim.Observe(); break;
                    case "snapshot": result = sim.Snapshot(); break;
                    case "step": result = sim.Step(request.action, request.decision, request.note); break;
                    case "validate": result = new { evidence = Simulation.EvidenceViolation(sim.Observe(), request.action), truth = sim.TruthViolation(request.action) }; break;
                    case "log": result = sim.Log; break;
                    case "record": sim.RecordDecision(request.decision, request.note); result = sim.Observe(); break;
                    case "replay": sim = Simulation.Replay(request.log); result = sim.Snapshot(); break;
                    default: throw new ArgumentException("Unknown operation");
                }
                Console.WriteLine(json.Serialize(result));
            }
            catch (Exception e) { Console.WriteLine(json.Serialize(new { error = e.Message })); }
        }
        return 0;
    }
}
