# designcraft standalone skills

Local development version `0.1.0-dev.1`, pinned native CLI `0.2.1`. Six independently usable skills define scoped routing, side effects, recovery and acceptance boundaries, alongside checksum-verified bootstrap, argv launcher, live command discovery and a single-session plan gateway. **Unpublished; native, host, model-dispatch and creative acceptance are pending.**

Skills: `designcraft-cli`, `designcraft-cli-document`, `designcraft-cli-export`, `designcraft-cli-layout`, `designcraft-cli-setup`, `designcraft-use`.

`skill-routing.json` captures default, explicit single-purpose and unrelated request examples. Actual model routing still requires host validation.

Use the directory of the SKILL.md actually loaded by the host. Every skill carries its own Python resources; siblings and global CLI paths are unnecessary. Python 3.11+ and macOS arm64 are the current target. `scripts/commands.py list/describe/check/run/receipt` discovers native interfaces and compiles plans. PrintCraft schemas are validated only within the documented supported subset; textual LightCraft/DesignCraft parameter guidance is not a machine schema. A zero native exit requires output review; unknown outcomes are not replayed.

Online invocation may install the pinned CLI and requires corresponding authorization. `--runtime-home` isolates user-data installation; `--archive` does not bypass checksums. Explicit `--catalog` files support offline discovery/checking only and cannot authorize execution.

Validate locally with `python3 -I -B scripts/validate_package.py` and `python3 -I -B -m unittest discover -s tests -v`. These checks do not execute native programs.

Optimization specifications and tasks are recorded in [the OpenSpec change](openspec/changes/harden-designcraft-skill-workflows/proposal.md); implementation is in progress. The development candidate is published on [GitHub](https://github.com/full-aigc-skills/designcraft-skills) on `main`. Native cold starts, full native interfaces, editable-project reopen/revision, source release pinning, host discovery/model dispatch, ArtCraft integration and final creative acceptance remain open. No version tag, GitHub Release or marketplace release has been created. See [architecture](docs/architecture.md) and `project-status.json`.
