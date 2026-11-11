# Building the Unity client on a remote machine

There is no compiled Unity player in this release. C# compilation and browser testing do not establish Unity runtime compatibility. A licensed Editor must execute somewhere to produce genuine Unity evidence.

## Existing licensed machine or cloud runner

1. Use a Windows x64 machine with an activated Unity 6 LTS Editor and Windows Mono build support. Licensing and cloud-machine costs are the owner's responsibility; this project does not bypass activation.
2. Copy or clone this repository to a short path. Run `scripts/build-unity.ps1` with the exact Editor path.
3. Archive `unity-build.log`, the player directory, the exact Editor version, source commit and OS/GPU information.
4. Start the Python service, launch the player, and follow the Unity checklist in `VALIDATION.md`.
5. Capture real player footage and replace the browser-only submission evidence only after checking it.

The manually dispatched workflow `unity-licensed-runner.yml` uses labels `self-hosted`, `Windows`, `X64`, `unity6`. Set `UNITY_EDITOR` in that runner's environment to its activated Editor executable. This can run on a remote machine. It is not a hosted service that works without a license or runner configuration.

## GitHub-hosted runner with your own Unity licence (GameCI)

`.github/workflows/unity-gameci.yml` needs no Editor on your own machine. It builds the Windows player inside a GameCI container on a GitHub-hosted Linux runner, then runs the built player with `-rgSmoke` on a GitHub-hosted Windows runner. The licence is yours; the workflow only reads it from repository secrets.

1. Create a Unity account and install Unity Hub (the Hub alone is enough; no Editor download is needed). Sign in, then choose **Preferences > Licenses > Add > Get a free personal license**.
2. Find the licence file the Hub created: `C:\ProgramData\Unity\Unity_lic.ulf` on Windows.
3. In the GitHub repository, open **Settings > Secrets and variables > Actions** and add three repository secrets: `UNITY_LICENSE` (the whole contents of the `.ulf` file), `UNITY_EMAIL` and `UNITY_PASSWORD` (the Unity account's sign-in details). Never commit these values.
4. Run **Actions > Unity build and player smoke test > Run workflow**, or push a change under `Unity/`.
5. Download the `unity-windows-player` and `unity-smoke-evidence` artifacts. The run summary lists the Unity version, graphics device and the timestamp-panel rows the player reported.

The Editor version comes from `Unity/ProjectSettings/ProjectVersion.txt`; GameCI must publish a `windows-mono` image for that exact version. Hosted runners have no GPU, so the smoke run renders with the WARP software rasteriser. It checks that the player starts and behaves correctly, not how it performs on real graphics hardware.

## Automated player check

`-rgSmoke` runs the same sequence in all three telemetry scenarios with seed 42: it blocks an unsafe suppression, advances to T+3, verifies the replay, checks that every row of the observation-timestamp panel agrees with the C# evidence check, and saves one screenshot per scenario. It then writes `unity-smoke.json` (pass or fail, Unity version, platform, graphics device, panel rows) and exits with code 0 or 1. `tests/test_observation_timeline.py` asserts the same sequence against the headless C# host, so the expected outcome is known before a player exists.

Output goes to the folder given by `-rgEvidenceDir <path>`, or to Unity's persistent data directory (normally `%USERPROFILE%\AppData\LocalLow\RecycleGuard Research\RecycleGuard`). `-rgScenario reliable|delayed|dropout` and `-rgSeed <number>` choose the incident the player starts with.

The automated check does **not** replace interactive verification of HTTP advice, buttons, layout and replay scrubbing.

## References

- [Unity command-line builds](https://docs.unity.com/en-us/engine/6000.3/manual/unity-editor/command-line-arguments/run-unity)
- [UnityWebRequest](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Networking.UnityWebRequest.html)
- [Unity JsonUtility](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/JsonUtility.html)
- [GameCI build and licensing options](https://game.ci/docs/github/builder/)

Neither Unity workflow has completed a run yet, and no cloud resources have been purchased. Until one does, the Unity client remains uncompiled and unexecuted.
