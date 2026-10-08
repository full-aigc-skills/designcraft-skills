# designcraft 独立技能

本地开发版本 `0.1.0-dev.1`，固定原生 CLI `0.2.1`。已实现六项自包含技能、明确技能职责和路由样例、带摘要的首次安装入口、原生命令目录和单会话计划转换。**尚未发布，未完成当前原生与创作验收；宿主发现及只读模型路由在记录的内置 CLI/模型组合通过。**

| 技能 | 职责 |
|---|---|
| designcraft-cli | 原生命令、参数和多步计划 |
| designcraft-cli-document | document |
| designcraft-cli-export | export |
| designcraft-cli-layout | layout |
| designcraft-cli-setup | 安装与版本诊断 |
| designcraft-use | 任务拆解与领域交付 |

`skill-routing.json` 固定通用入口、显式原子技能和无关请求的示例；各技能正文还列明输入前置、副作用、恢复及验收边界。当前九项只读模型路由已在真实内置 Codex CLI 0.162.0-alpha.2 / gpt-6-astra 验证；原生调用和其他组合未验收。

## 使用入口

从宿主实际加载的 SKILL.md 确定技能目录，不假定兄弟技能或固定用户路径。每项技能都带全部所需Python资源，Python 3.11+，当前固定平台为macOS arm64。

```bash
: "${SKILL_DIR:?本技能的实际加载目录}"
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- --version
python3 -I -B "$SKILL_DIR/scripts/commands.py" list
python3 -I -B "$SKILL_DIR/scripts/commands.py" describe <真实命令ID>
python3 -I -B "$SKILL_DIR/scripts/commands.py" check /absolute/path/plan.json
python3 -I -B "$SKILL_DIR/scripts/commands.py" run /absolute/path/plan.json --output /absolute/path/new-run
```

上述在线命令可能安装固定原生运行时，执行前需已有对应用户授权。安装位于用户数据目录，不修改PATH、系统应用或技能内容。`--runtime-home`可隔离目录，`--archive`仍强制核对固定摘要。`commands.py --catalog <原生目录JSON>`只用于显式离线查询／检查，不能作为执行目录。

计划格式：`{"domain":"designcraft","steps":[{"command":"实际命令ID","params":{}}]}`。
PrintCraft将步骤转换为`tool/args`，其他两域保留`command/params`。PrintCraft校验原生JSON Schema的受支持约束；LightCraft、DesignCraft保留参数原文，由原生程序检查类型和状态。原生退出零仍需检查实际工程和输出，超时保存UNKNOWN，不自动重放。

## 本地验证

```bash
python3 -I -B scripts/validate_package.py
python3 -I -B -m unittest discover -s tests -v
python3 -I -B scripts/check_research_inventory.py --source-root ../../research/designcraft
python3 -I -B scripts/record_offline_evidence.py
python3 -I -B scripts/evidence_freshness.py evidence-manifest.json
```

研究清单检查只比对静态源码、研究提交和文件摘要；它不会运行或证明固定 CLI。证据记录绑定源码包、锁文件、输入/报告、运行环境和 runId，摘要变化会报告 `STALE`。当前宿主发现与只读模型路由为 `PASS`；原生、CI、平台和创作层仍各自为 `NOT_RUN`。本地测试检查技能资源、自包含路径和拒绝边界，不运行原生程序，不替代首用验收。

## 未完成项

- [OpenSpec 优化规范与任务](openspec/changes/harden-designcraft-skill-workflows/proposal.md)已建立并通过严格格式校验；离线实现持续推进，宿主发现与只读路由通过；原生、创作与发行验收待完成。
- 实际冷安装、完整原生命令目录与参数对照、保存重开、局部返工、实际结果质量。
- 固定技能源发行与插件发布锁，以及真实宿主原生调用、重启续跑与完整创作接受。
- ArtCraft三领域协议映射、依赖与版本交接、选择性重建及移动交付。
- 其他平台、完整GUI／真实RAW／签名加密等各自适用能力的验收。

开发候选源码已推送至[公开 GitHub 仓库](https://github.com/full-aigc-skills/designcraft-skills)的 `main` 分支。版本标签、GitHub Release 和技能市场发行尚未创建；必要的原生、创作与发行验收未完成前不会登记为正式发行。[架构](docs/architecture.zh-CN.md)与`project-status.json`记录当前边界。
