# 本地交付架构

独立技能项目是源码来源，每项技能携带固定CLI安装器、公开argv入口、命令目录网关及运行时锁。插件保存逐文件摘要的本地快照；来源未发布，不能登记为可安装市场发行。

PrintCraft使用原生JSON Schema；LightCraft、DesignCraft保留参数说明文本。计划在一个原生进程中执行；超时保留未知状态，不自动重放。零退出仍需检查工程、输出、保存重开和创作质量。安装、宿主发现、模型选用及最终交付分别验收。

`command-coverage.json` 的 `nativeCommands` 只记录固定原生 CLI 实际发现的目录；`nativeCatalogStatus` 当前为 `NOT_RUN`。`research-command-inventory.json` 是单独的静态研究源码清单，绑定研究仓库 commit、CLI 分发源码、命令注册源码及各文件 SHA-256。清单内命令标记为 `RESEARCH_SOURCE_ONLY`，不提供 `ownerSkill`，不能据此声称安装制品支持。研究源码仍可用时运行 `python3 -I -B scripts/check_research_inventory.py --source-root ../../research/designcraft` 检查提交和文件摘要是否过期。

`evidence-manifest.json` 分层记录离线测试、包校验和研究清单检查，并将每项结果绑定当前包、技能/命令/运行时锁、输入、报告产物、环境和 runId。使用 `scripts/record_offline_evidence.py` 重跑离线验收并刷新记录，使用 `scripts/evidence_freshness.py evidence-manifest.json` 检查时效；摘要不符会标记 `STALE`。原生、CI、宿主、平台、模型和创作层保持独立状态。

[OpenSpec 优化变更](../openspec/changes/harden-designcraft-skill-workflows/proposal.md)已建立并通过格式校验，实现任务仍未完成。开发候选已推送至[公开 GitHub 仓库](https://github.com/full-aigc-skills/designcraft-skills)的 `main` 分支；尚无版本标签、GitHub Release 或技能市场发行。原生安装尚未执行，执行时须具备对应授权。已有五套仍使用原OpenSpec；三领域的ArtCraft公共协议映射、依赖交接、返工和移动交付仍未接入。


安装锁现在绑定发行标签、归档名、二进制身份与版本；不一致时在创建运行时目录前拒绝。当前所有三领域真实固定发行仍为0.2.1。
