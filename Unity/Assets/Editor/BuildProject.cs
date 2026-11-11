using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using RecycleGuard;

public static class BuildProject
{
    [MenuItem("RecycleGuard/Create and open incident scene")]
    public static void Prepare()
    {
        Directory.CreateDirectory("Assets/Scenes");
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        new GameObject("RecycleGuard incident lab").AddComponent<IncidentLab>();
        EditorSceneManager.SaveScene(scene, "Assets/Scenes/IncidentLab.unity");
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene("Assets/Scenes/IncidentLab.unity", true) };
        PlayerSettings.companyName = "RecycleGuard Research";
        PlayerSettings.productName = "RecycleGuard";
        PlayerSettings.defaultScreenWidth = 1600; PlayerSettings.defaultScreenHeight = 900;
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
        PlayerSettings.resizableWindow = true;
        // An unattended smoke run has no focused window; the player must keep stepping regardless.
        PlayerSettings.runInBackground = true;
        AssetDatabase.SaveAssets();
    }
    [MenuItem("RecycleGuard/Verify C# core")]
    public static void Verify()
    {
        foreach (string scenario in new[] { "reliable", "delayed", "dropout" })
        {
            var sim = new Simulation(42, scenario);
            var result = sim.Step(new ActionCommand("suppress", 0, 0), "test", "");
            if (result.accepted || result.truth.water != 18) throw new Exception("Constraint invariant failed");
            // The observation-timestamp panel must agree with the evidence check on every zone and tick.
            for (int tick = 1; tick < 8; tick++)
            {
                var observation = sim.Observe();
                if (observation.status != "active") break;
                var rows = ObservationTimeline.Describe(observation);
                if (rows.Length != observation.zones.Length) throw new Exception("Timestamp panel row count mismatch");
                for (int i = 0; i < rows.Length; i++)
                {
                    string check = Simulation.EvidenceViolation(observation, new ActionCommand("isolate", i, observation.revision));
                    if (check.StartsWith("EVIDENCE", StringComparison.Ordinal) == rows[i].actionable) throw new Exception("Timestamp panel disagrees with the evidence check: " + scenario + " zone " + i + " tick " + tick);
                }
                foreach (var preflight in ObservationTimeline.Preflight(observation, 0))
                    if (preflight.allowed != (preflight.violation.Length == 0)) throw new Exception("Preflight invariant failed");
                // Inspect once so reconnaissance rows are covered as well as telemetry rows.
                sim.Step(tick == 4 ? new ActionCommand("inspect", 1, observation.revision) : new ActionCommand("wait", -1, observation.revision), "test", "");
            }
            Simulation.Replay(sim.Log);
        }
        Debug.Log("RECYCLEGUARD_CORE_VERIFIED");
    }
    // Output location, in order: RECYCLEGUARD_BUILD_DIR, the player path a CI builder passes
    // as -customBuildPath (GameCI), then ../dist/UnityWindows.
    private static string PlayerPath()
    {
        string output = Environment.GetEnvironmentVariable("RECYCLEGUARD_BUILD_DIR");
        if (string.IsNullOrEmpty(output))
        {
            string[] args = Environment.GetCommandLineArgs();
            int custom = Array.IndexOf(args, "-customBuildPath");
            if (custom >= 0 && custom + 1 < args.Length && args[custom + 1].EndsWith(".exe", StringComparison.OrdinalIgnoreCase)) return Path.GetFullPath(args[custom + 1]);
            output = Path.GetFullPath("../dist/UnityWindows");
        }
        return Path.Combine(output, "RecycleGuard.exe");
    }
    [MenuItem("RecycleGuard/Build Windows demo")]
    public static void BuildWindows()
    {
        Prepare(); Verify();
        string player = PlayerPath();
        Directory.CreateDirectory(Path.GetDirectoryName(player));
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { "Assets/Scenes/IncidentLab.unity" }, locationPathName = player, target = BuildTarget.StandaloneWindows64, options = BuildOptions.Development });
        if (report.summary.result != BuildResult.Succeeded) throw new Exception("Unity build failed: " + report.summary.result);
        Debug.Log("RECYCLEGUARD_BUILD_VERIFIED: " + player + " / Unity " + Application.unityVersion);
    }
}
