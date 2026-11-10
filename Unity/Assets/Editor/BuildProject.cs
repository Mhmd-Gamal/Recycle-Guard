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
            Simulation.Replay(sim.Log);
        }
        Debug.Log("RECYCLEGUARD_CORE_VERIFIED");
    }
    [MenuItem("RecycleGuard/Build Windows demo")]
    public static void BuildWindows()
    {
        Prepare(); Verify();
        string output = Environment.GetEnvironmentVariable("RECYCLEGUARD_BUILD_DIR");
        if (string.IsNullOrEmpty(output)) output = Path.GetFullPath("../dist/UnityWindows");
        Directory.CreateDirectory(output);
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { "Assets/Scenes/IncidentLab.unity" }, locationPathName = Path.Combine(output, "RecycleGuard.exe"), target = BuildTarget.StandaloneWindows64, options = BuildOptions.Development });
        if (report.summary.result != BuildResult.Succeeded) throw new Exception("Unity build failed: " + report.summary.result);
        Debug.Log("RECYCLEGUARD_BUILD_VERIFIED: " + output);
    }
}
