# Development and contributions

## Provenance

The initial implementation was developed with substantial Codex assistance, including the C# simulation, Unity client source, Python service, browser interface, tests, evaluation runner, documentation and packaging. Codex also ran local verification and prepared the recorded demonstration. Git history records this development; it does not establish independent authorship or Unity proficiency for a portfolio owner.

Validation scope and outstanding checks are maintained in [VALIDATION.md](VALIDATION.md). The measured experiments use offline proposal fixtures.

## Contributing

Keep changes reviewable. Describe the problem, the design decision and the checks performed in the commit or pull request. Credit assistance and external code where applicable.

Changes to simulation rules require particular care:

- Keep state transitions in the shared C# core; do not duplicate the simulator in Python.
- Update adviser constraints when action prerequisites change, and run the parity tests.
- Preserve revision checks, resource accounting and replay verification.
- Use development seeds while tuning policies. Reserve a separate seed range for final comparisons.
- Regenerate results and source manifests when evaluated code changes; keep earlier evidence clearly identified.
- Record the Editor version and player checks when validating the Unity client.

## Open engineering work

1. Compile and exercise the native client with a licensed Unity Editor.
2. Evaluate real-model proposals on cached observations shared by all checker variants.
3. Add stronger planning baselines to separate filtering effects from repair-policy effects.
4. Extend the observation model with sensor noise and delayed action acknowledgements.
5. Review scenario assumptions with domain experts before designing a human study.
