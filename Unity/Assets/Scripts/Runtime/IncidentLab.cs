using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using RecycleGuard;

[Serializable] public class AdvicePayload
{
    public Observation observation;
    public string mode;
    public ActionCommand[] exclude;
}
[Serializable] public class AdviceResponse
{
    public string schema, mode, provider, explanation, uncertainty;
    public int revision;
    public ActionCommand proposal, recommendation;
    public bool intervention;
    public string[] violations, evidence, missing, plan;
    public ActionCommand[] alternatives;
    public float latency_ms;
}

// Scene composition, operator interaction and replay are native Unity/C#.
// Only recommendations cross HTTP; the Python adviser cannot mutate this world.
public class IncidentLab : MonoBehaviour
{
    public string adviserUrl = "http://127.0.0.1:8765/v1/advice";
    private Simulation sim;
    private Observation observation;
    private AdviceResponse advice;
    private int selected, scenarioIndex, modeIndex, replayIndex;
    private string seedText = "42", note = "", message = "Select a zone, inspect evidence, then request advice.";
    private bool busy, replayMode;
    private SessionLog replay;
    private readonly string[] scenarios = { "reliable", "delayed", "dropout" };
    private readonly string[] modes = { "offline_checked", "offline_raw", "scripted", "llm_checked", "llm_raw" };
    private readonly List<ActionCommand> exclusions = new List<ActionCommand>();
    private readonly List<string> trail = new List<string>();
    private readonly GameObject[] blocks = new GameObject[4];
    private readonly GameObject[] hazards = new GameObject[4];
    private readonly TextMesh[] labels = new TextMesh[4];
    private readonly Material[] zoneMaterials = new Material[4];
    private Camera view;
    private GUIStyle title, heading, body, small, button, field;
    private Vector2 trailScroll, adviceScroll;
    private int generation;
    private string ReplayPath { get { return Path.Combine(Application.persistentDataPath, "last-session.json"); } }

    private void Awake()
    {
        Application.targetFrameRate = 60;
        BuildFacility(); ResetIncident();
        if (Array.IndexOf(Environment.GetCommandLineArgs(), "-rgSmoke") >= 0) StartCoroutine(Smoke());
    }
    private Material Material(Color color)
    {
        Shader shader = Shader.Find("Standard");
        if (shader == null) shader = Shader.Find("Unlit/Color");
        var material = new Material(shader); material.color = color; return material;
    }
    private GameObject Cube(string name, Vector3 position, Vector3 size, Color color)
    {
        var obj = GameObject.CreatePrimitive(PrimitiveType.Cube); obj.name = name;
        obj.transform.position = position; obj.transform.localScale = size;
        obj.GetComponent<Renderer>().material = Material(color); return obj;
    }
    private TextMesh Text(string text, Vector3 position, float size)
    {
        var go = new GameObject("Label"); go.transform.position = position;
        go.transform.rotation = Quaternion.Euler(70, 0, 0);
        var t = go.AddComponent<TextMesh>(); t.text = text; t.fontSize = 48; t.characterSize = size;
        t.anchor = TextAnchor.MiddleCenter; t.color = new Color(.15f, .25f, .22f); return t;
    }
    private void BuildFacility()
    {
        view = new GameObject("Incident camera").AddComponent<Camera>();
        view.transform.position = new Vector3(0, 25, -22); view.transform.LookAt(new Vector3(0, 0, 0));
        view.orthographic = true; view.orthographicSize = 13; view.backgroundColor = new Color(.83f, .88f, .85f);
        view.clearFlags = CameraClearFlags.SolidColor;
        view.rect = new Rect(0, .23f, .65f, .59f);
        var light = new GameObject("Daylight").AddComponent<Light>(); light.type = LightType.Directional;
        light.transform.rotation = Quaternion.Euler(55, -25, 0); light.intensity = 1.2f;
        RenderSettings.ambientLight = new Color(.65f, .7f, .68f);
        Cube("Facility pad", new Vector3(0, -.3f, 0), new Vector3(26, .4f, 21), new Color(.7f, .77f, .71f));
        Cube("Service lane", new Vector3(0, -.04f, 0), new Vector3(26, .1f, 2), new Color(.35f, .42f, .38f));
        Cube("Central lane", new Vector3(0, -.03f, 0), new Vector3(2, .1f, 21), new Color(.35f, .42f, .38f));
        for (int j = -5; j < 6; j++) Cube("Lane marking", new Vector3(j * 2.2f, .04f, 0), new Vector3(1, .04f, .08f), new Color(.88f, .87f, .65f));
        for (int i = 0; i < 4; i++)
        {
            float x = (i % 2 == 0 ? -6 : 6), z = (i < 2 ? 5 : -5);
            blocks[i] = Cube("Zone " + i, new Vector3(x, .15f, z), new Vector3(9, .35f, 7), Color.white);
            zoneMaterials[i] = blocks[i].GetComponent<Renderer>().material;
            Cube("Back wall " + i, new Vector3(x, 1, z + 3.4f), new Vector3(9, 2, .16f), new Color(.55f, .65f, .58f));
            Cube("Side wall " + i, new Vector3(x - 4.4f, 1, z), new Vector3(.16f, 2, 7), new Color(.6f, .7f, .63f));
            for (int j = 0; j < 5; j++)
            {
                Cube("Material stack " + i + "-" + j, new Vector3(x - 2.7f + (j % 3) * 2, .8f, z + (j < 3 ? 1.8f : 0)), new Vector3(1.2f, 1.2f, 1.1f), new Color(.38f + .03f * j, .48f + .02f * j, .43f));
            }
            Cube("Conveyor " + i, new Vector3(x, .6f, z - 1.5f), new Vector3(6, .3f, .65f), new Color(.2f, .27f, .24f));
            hazards[i] = GameObject.CreatePrimitive(PrimitiveType.Sphere); hazards[i].name = "Observed heat marker " + i;
            hazards[i].transform.position = new Vector3(x + 2, 2, z + 1);
            hazards[i].GetComponent<Renderer>().material = Material(new Color(.95f, .4f, .15f));
            Destroy(hazards[i].GetComponent<Collider>());
            labels[i] = Text("", new Vector3(x, .6f, z - 3.1f), .07f);
        }
        Text("NORTHBANK / RESOURCE RECOVERY", new Vector3(0, 0, 10), .085f);
        Cube("Command vehicle", new Vector3(-10, .5f, -9), new Vector3(2.5f, 1, 1.2f), new Color(.1f, .37f, .3f));
    }
    private void ResetIncident()
    {
        int seed;
        if (!int.TryParse(seedText, out seed)) { message = "Enter a valid 32-bit seed."; return; }
        generation++; sim = new Simulation(seed, scenarios[scenarioIndex]); advice = null; exclusions.Clear();
        replayMode = false; busy = false; trail.Clear(); observation = sim.Observe();
        message = "New seeded incident. The simulation advances only when you apply an action."; Refresh();
    }
    private void Refresh()
    {
        observation = sim.Observe();
        for (int i = 0; i < 4; i++)
        {
            var z = observation.zones[i];
            int heat = replayMode ? replay.events[replayIndex].after.zones[i].heat : z.heat;
            int people = replayMode ? replay.events[replayIndex].after.zones[i].people : z.people;
            zoneMaterials[i].color = i == selected ? new Color(.52f, .76f, .65f) : heat < 0 ? new Color(.66f, .66f, .6f) : heat >= 25 ? new Color(.89f, .7f, .48f) : new Color(.8f, .85f, .79f);
            hazards[i].SetActive(heat >= 25); hazards[i].transform.localScale = Vector3.one * (.5f + Math.Max(0, heat) / 55f);
            labels[i].text = z.name + "\nHeat " + (heat < 0 ? "?" : heat.ToString()) + " | People " + (people < 0 ? "?" : people.ToString());
        }
    }
    private void Update()
    {
        if (Input.GetMouseButtonDown(0) && Input.mousePosition.x < Screen.width * .65f && Input.mousePosition.y > Screen.height * .23f && Input.mousePosition.y < Screen.height * .82f)
        {
            RaycastHit hit;
            if (Physics.Raycast(view.ScreenPointToRay(Input.mousePosition), out hit))
            {
                Vector3 p = hit.point;
                selected = (p.x < 0 ? 0 : 1) + (p.z > 0 ? 0 : 2); Refresh();
            }
        }
    }
    private IEnumerator RequestAdvice(bool alternative)
    {
        if (busy || replayMode || observation.status != "active") yield break;
        if (alternative && advice != null) { exclusions.Add(advice.recommendation); sim.RecordDecision("alternative", JsonUtility.ToJson(advice)); }
        busy = true; int requestGeneration = generation;
        var payload = new AdvicePayload { observation = observation, mode = modes[modeIndex], exclude = exclusions.ToArray() };
        using (var request = new UnityWebRequest(adviserUrl, "POST"))
        {
            request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(JsonUtility.ToJson(payload)));
            request.downloadHandler = new DownloadHandlerBuffer(); request.SetRequestHeader("Content-Type", "application/json"); request.timeout = 35;
            yield return request.SendWebRequest();
            if (requestGeneration != generation) yield break;
            busy = false;
            if (request.result != UnityWebRequest.Result.Success) { message = "Adviser unavailable: " + request.error + ". Start scripts/start.ps1. Manual simulation remains available."; yield break; }
            AdviceResponse parsed = null;
            try { parsed = JsonUtility.FromJson<AdviceResponse>(request.downloadHandler.text); }
            catch (Exception e) { message = "Invalid advice JSON: " + e.Message; }
            if (parsed == null || parsed.schema != "recycleguard.advice.v1" || parsed.recommendation == null || parsed.revision != observation.revision)
            { message = "Malformed or stale advice discarded."; yield break; }
            advice = parsed; sim.RecordDecision("advice", JsonUtility.ToJson(advice));
            trail.Add("T+" + observation.tick + " ADVICE: " + advice.recommendation.kind + " / " + advice.explanation);
            message = "Recommendation ready. Review the evidence before accepting.";
        }
    }
    private void Apply(ActionCommand command, string decision)
    {
        if (replayMode || busy) return;
        var result = sim.Step(command, decision, note); message = result.reason;
        trail.Add("T+" + (result.truth.tick - (result.advanced ? 1 : 0)) + " " + decision.ToUpper() + " " + command.kind + " / " + result.reason);
        advice = null; if (result.advanced) exclusions.Clear(); Refresh();
    }
    private void Export()
    {
        File.WriteAllText(ReplayPath, JsonUtility.ToJson(sim.Log, true)); message = "Saved replay: " + ReplayPath;
    }
    private void LoadReplay()
    {
        try
        {
            replay = JsonUtility.FromJson<SessionLog>(File.ReadAllText(ReplayPath)); Simulation.Replay(replay);
            if (replay.events.Count == 0) throw new Exception("No events in replay");
            replayMode = true; replayIndex = 0; Refresh(); message = "Verified replay. Displaying recorded truth for debrief, not adviser observations.";
        }
        catch (Exception e) { message = "Replay failed verification: " + e.Message; }
    }
    private void Styles()
    {
        if (title != null) return;
        title = new GUIStyle(GUI.skin.label) { fontSize = 30, fontStyle = FontStyle.Bold, normal = { textColor = new Color(.1f, .22f, .18f) } };
        heading = new GUIStyle(title) { fontSize = 20 };
        body = new GUIStyle(GUI.skin.label) { fontSize = 16, wordWrap = true, normal = { textColor = new Color(.16f, .27f, .22f) } };
        small = new GUIStyle(body) { fontSize = 13 };
        button = new GUIStyle(GUI.skin.button) { fontSize = 14, wordWrap = true, padding = new RectOffset(12, 12, 8, 8) };
        field = new GUIStyle(GUI.skin.textField) { fontSize = 16 };
    }
    private void Box(Rect rect, Color color) { var before = GUI.color; GUI.color = color; GUI.DrawTexture(rect, Texture2D.whiteTexture); GUI.color = before; }
    private void OnGUI()
    {
        if (sim == null) return; Styles(); GUI.matrix = Matrix4x4.TRS(Vector3.zero, Quaternion.identity, new Vector3(Screen.width / 1600f, Screen.height / 900f, 1));
        Box(new Rect(0, 0, 1600, 163), new Color(.95f, .97f, .94f));
        GUI.Label(new Rect(28, 20, 700, 46), "RecycleGuard / Incident Lab", title);
        GUI.Label(new Rect(30, 68, 960, 28), "UNITY + C# SIMULATION  /  HUMAN AUTHORITY  /  REPRODUCIBLE RESEARCH", small);
        var s = replayMode ? replay.events[replayIndex].after : sim.Snapshot();
        GUI.Label(new Rect(30, 112, 970, 36), string.Format("{0}     TICK {1}/32     CREWS {2}/2     WATER {3}     DAMAGE {4}", s.status.ToUpper(), s.tick, s.crews, s.water, s.damage), heading);
        GUI.Label(new Rect(1055, 18, 470, 24), "Fictional training model. Not operational guidance.", small);
        seedText = GUI.TextField(new Rect(1055, 54, 90, 34), seedText, field);
        GUI.enabled = !busy;
        if (GUI.Button(new Rect(1155, 54, 200, 34), scenarios[scenarioIndex], button)) scenarioIndex = (scenarioIndex + 1) % scenarios.Length;
        if (GUI.Button(new Rect(1365, 54, 205, 34), "New incident", button)) ResetIncident();
        if (GUI.Button(new Rect(1055, 100, 245, 34), "Export replay", button)) Export();
        if (GUI.Button(new Rect(1310, 100, 260, 34), replayMode ? "Return to live" : "Verify / replay last", button))
        { if (replayMode) { replayMode = false; Refresh(); } else LoadReplay(); }
        Box(new Rect(1040, 163, 560, 737), new Color(.97f, .98f, .96f));
        GUI.Label(new Rect(1060, 180, 510, 33), "Decision support", heading);
        if (GUI.Button(new Rect(1060, 220, 510, 34), modes[modeIndex] + "  (click to change)", button)) { modeIndex = (modeIndex + 1) % modes.Length; advice = null; }
        GUI.Label(new Rect(1060, 262, 510, 40), "Offline mode uses deterministic fault-injection fixtures, NOT an LLM.", small);
        GUI.enabled = !busy && !replayMode && observation.status == "active";
        if (GUI.Button(new Rect(1060, 308, 510, 40), busy ? "Requesting..." : "Request recommendation", button)) StartCoroutine(RequestAdvice(false));
        GUI.enabled = true;
        GUILayout.BeginArea(new Rect(1060, 363, 510, 352)); adviceScroll = GUILayout.BeginScrollView(adviceScroll);
        if (advice == null) GUILayout.Label("No action executes automatically. Request advice, inspect its evidence, then accept, reject or modify it.", body);
        else
        {
            GUILayout.Label(advice.recommendation.kind.ToUpper() + " / zone " + advice.recommendation.zone, heading);
            GUILayout.Label(advice.intervention ? "CONSTRAINT CHECK INTERVENED" : "POLICY: " + advice.mode, small);
            GUILayout.Label(advice.explanation, body);
            GUILayout.Space(12); GUILayout.Label("EVIDENCE", heading);
            foreach (string evidence in advice.evidence) GUILayout.Label(evidence, small);
            foreach (string missing in advice.missing) GUILayout.Label("GAP: " + missing, small);
            if (advice.plan != null) foreach (string step in advice.plan) GUILayout.Label(step, small);
            GUILayout.Space(12); GUILayout.Label(advice.uncertainty, small);
            GUILayout.Label("Provider: " + advice.provider + " / " + advice.latency_ms.ToString("F2") + " ms", small);
        }
        GUILayout.EndScrollView(); GUILayout.EndArea();
        GUI.enabled = advice != null && !busy && !replayMode;
        if (GUI.Button(new Rect(1060, 730, 245, 38), "Accept and execute", button)) Apply(advice.recommendation, "accept");
        if (GUI.Button(new Rect(1315, 730, 255, 38), "Reject", button))
        { sim.RecordDecision("reject", note); exclusions.Add(advice.recommendation); advice = null; trail.Add("T+" + observation.tick + " REJECT: " + note); message = "Rejected. No time consumed."; }
        if (GUI.Button(new Rect(1060, 778, 510, 36), "Request alternative", button)) StartCoroutine(RequestAdvice(true));
        GUI.enabled = true; GUI.Label(new Rect(1060, 826, 510, 62), "Modify: choose a zone and use a manual action. Every action is revalidated by the C# simulation.", small);
        Box(new Rect(0, 693, 1040, 207), new Color(.93f, .96f, .93f));
        GUI.Label(new Rect(24, 698, 990, 28), message, small);
        if (replayMode)
        {
            int index = Mathf.RoundToInt(GUI.HorizontalSlider(new Rect(30, 750, 960, 25), replayIndex, 0, replay.events.Count - 1));
            if (index != replayIndex) { replayIndex = index; Refresh(); }
            GUI.Label(new Rect(30, 785, 960, 42), "DEBRIEF TRUTH / event " + (replayIndex + 1) + " of " + replay.events.Count + " / " + replay.events[replayIndex].decision, body);
        }
        else
        {
            GUI.Label(new Rect(24, 730, 240, 26), observation.zones[selected].name, heading);
            note = GUI.TextField(new Rect(280, 730, 730, 28), note, 500, field);
            GUI.enabled = !busy && observation.status == "active";
            string[] kinds = { "inspect", "evacuate", "isolate", "suppress", "wait" };
            for (int i = 0; i < kinds.Length; i++) if (GUI.Button(new Rect(24 + 198 * i, 772, 188, 36), kinds[i], button)) Apply(new ActionCommand(kinds[i], kinds[i] == "wait" ? -1 : selected, observation.revision), advice == null ? "manual" : "modify");
            GUI.enabled = true;
            GUILayout.BeginArea(new Rect(24, 819, 990, 75)); trailScroll = GUILayout.BeginScrollView(trailScroll);
            for (int i = trail.Count - 1; i >= 0; i--) GUILayout.Label(trail[i], small);
            GUILayout.EndScrollView(); GUILayout.EndArea();
        }
    }
    private IEnumerator Smoke()
    {
        yield return new WaitForEndOfFrame();
        var rejected = sim.Step(new ActionCommand("suppress", 0, 0), "test", "Unsafe action must be blocked");
        if (rejected.accepted) throw new Exception("Smoke test accepted unsafe action");
        Simulation.Replay(sim.Log);
        Refresh();
        yield return new WaitForEndOfFrame();
        string path = Path.Combine(Application.persistentDataPath, "unity-smoke.png");
        ScreenCapture.CaptureScreenshot(path);
        yield return null; yield return null;
        File.WriteAllText(Path.Combine(Application.persistentDataPath, "unity-smoke.json"), "{\"passed\":true,\"scope\":\"scene startup, unsafe action rejection, replay, screenshot request\"}");
        Application.Quit(0);
    }
}
