# Building Unity without installing it on the applicant's laptop

There is no compiled Unity player in this release. C# compilation and browser testing do not establish Unity runtime compatibility. A licensed Editor must execute somewhere to produce genuine Unity evidence.

## Existing licensed machine or cloud runner

1. Use a Windows x64 machine with an activated Unity 6 LTS Editor and Windows Mono build support. Licensing and cloud-machine costs are the owner's responsibility; this project does not bypass activation.
2. Copy or clone this repository to a short path. Run `scripts/build-unity.ps1` with the exact Editor path.
3. Archive `unity-build.log`, the player directory, the exact Editor version, source commit and OS/GPU information.
4. Start the Python service, launch the player, and follow the Unity checklist in `VALIDATION.md`.
5. Capture real player footage and replace the browser-only submission evidence only after checking it.

The included manually dispatched GitHub workflow uses labels `self-hosted`, `Windows`, `X64`, `unity6`. Set `UNITY_EDITOR` in that runner's environment to its activated Editor executable. This can run on a remote machine. It is not a hosted service that works without a license or runner configuration.

The automated `-rgSmoke` player option checks scene startup, rejection of an unsafe action, replay and a screenshot request. Its output is placed under Unity's persistent data directory (normally `%USERPROFILE%\AppData\LocalLow\RecycleGuard Research\RecycleGuard`). It does **not** replace interactive verification of HTTP advice, buttons, layout and replay scrubbing.

## References

- [Unity command-line builds](https://docs.unity.com/en-us/engine/6000.3/manual/unity-editor/command-line-arguments/run-unity)
- [UnityWebRequest](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Networking.UnityWebRequest.html)
- [Unity JsonUtility](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/JsonUtility.html)
- [GameCI build and licensing options](https://game.ci/docs/github/builder/)

No GitHub workflow has been dispatched from this session, and no cloud resources have been purchased.
