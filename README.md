# designcraft standalone skills

Local development version `0.1.0-dev.1`, pinned native CLI `0.2.1`. Six independently usable skills define scoped routing, side effects, recovery and acceptance boundaries, alongside checksum-verified bootstrap, argv launcher, live command discovery and a single-session plan gateway. **Unpublished; native and creative acceptance are pending; host discovery and read-only model routing passed for bundled Codex CLI 0.162.0-alpha.2 / gpt-6-astra / macOS arm64.**

Skills: `designcraft-cli`, `designcraft-cli-document`, `designcraft-cli-export`, `designcraft-cli-layout`, `designcraft-cli-setup`, `designcraft-use`.

`skill-routing.json` captures default, explicit single-purpose and unrelated request examples. Nine actual read-only model-routing cases passed in the recorded host; native dispatch and other host/model combinations remain unverified.

Use the directory of the SKILL.md actually loaded by the host. Every skill carries its own Python resources; siblings and global CLI paths are unnecessary. Python 3.11+ and macOS arm64 are the current target. `scripts/commands.py list/describe/check/run/receipt` discovers native interfaces and compiles plans. PrintCraft schemas are validated only within the documented supported subset; textual LightCraft/DesignCraft parameter guidance is not a machine schema. A zero native exit requires output review; unknown outcomes are not replayed.

Online invocation may install the pinned CLI and requires corresponding authorization. `--runtime-home` isolates user-data installation; `--archive` does not bypass checksums. Explicit `--catalog` files support offline discovery/checking only and cannot authorize execution.

Validate locally with `python3 -I -B scripts/validate_package.py` and `python3 -I -B -m unittest discover -s tests -v`. These checks do not execute native programs.

Optimization specifications and tasks are recorded in [the OpenSpec change](openspec/changes/harden-designcraft-skill-workflows/proposal.md); implementation is in progress. The development candidate is published on [GitHub](https://github.com/full-aigc-skills/designcraft-skills) on `main`. Native cold starts, full native interfaces, editable-project reopen/revision, source release pinning, native dispatch in the host, ArtCraft integration and final creative acceptance remain open. No version tag, GitHub Release or marketplace release has been created. See [architecture](docs/architecture.md) and `project-status.json`.

## 场景技能开发候选

已增加 6 个领域场景技能及 1 个内嵌编辑器入口。详见 [场景目录](docs/scene-skills.md)。本地未发布候选，不代表全部场景的创作质量已验收。

## 排版场景操作手册

新增8条带具体方法、参数与结果检查的排版流程，见 [designcraft-scenario-playbooks](skills/designcraft-scenario-playbooks/SKILL.md)。包含原生脚本返回引用、活表格、溢出与PDF交付；技术运行与真实宿主/创作验收分别记录。

## main开发候选补充

新增[main工作流与参数](skills/designcraft-scenario-playbooks/references/main-workflows.md)：SVG导入并交付可编辑PPTX、Flex模块布局、60个新增方法与119处参数变化的索引。来源为固定main实际目录；SVG/PPTX已通过Windows main专项39008681404；Flex仍待执行，不等于稳定版支持或宿主验收通过。
