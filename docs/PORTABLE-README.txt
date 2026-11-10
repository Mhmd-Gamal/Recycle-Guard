RECYCLEGUARD - LOCAL BROWSER DEMO

1. Extract the entire zip to a short path, e.g. C:\RecycleGuard-demo.
2. Run RecycleGuard.exe. Your browser opens the local demo.
3. Keep the console open while using it. Press Ctrl+C in the console to stop.
4. If the port is busy, run RecycleGuard.exe --port 8766.

Windows 10/11 x64 with .NET Framework 4.x (normally included) is required.
No Unity installation, Python installation, model credentials or network connection
is needed to use the offline demonstration. The build is unsigned.

This executable serves the browser interface and runs the shared C# simulation.
It is NOT a Unity player build. Unity client source and build scripts are provided
in the source package; a licensed Unity Editor elsewhere is needed to validate it.

Offline proposals are deterministic fault-injection fixtures, NOT an LLM.
This fictional training prototype is not operational guidance and has no FRV
endorsement or physical validation. Do not use its action rules for real incidents.

Quick walkthrough:
- Choose sensor dropout, seed 42, and click New incident.
- Request a recommendation; inspect the evidence and missing observations.
- Request an alternative, reject it, or accept it.
- Click a facility zone and choose a manual action to override the adviser.
- Export the replay, then use Verify & view replay to inspect the decision trail.
  Replay debrief shows recorded simulator truth, not adviser observations.

Only local session data is used. Sessions live in memory and disappear when the
server stops. Export any replay you want to keep. Optional configured LLM modes
send synthetic observations to the endpoint you explicitly configure.

See the companion source package and technical report for the research method,
results, validation scope and development provenance.
