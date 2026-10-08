# 技能源与插件的共享契约交付

本地候选 `designcraft-skills` 版本 `0.1.0-dev.1` 向 `designcraft-plugin` 交付六项源技能；插件独立维护 Harness。源版本和插件版本不要求长期相同。正式 repo/tag/commit 来源锁仍由独立发行任务验收。

| 合同 | 公开入口及版本 | 当前兼容验证 |
| --- | --- | --- |
| EX-01 | 启动器 `cli.py` 的 result schema 1；`commands.py run/receipt` 的 receipt schema 2 | 保留 UNKNOWN/NOT_STARTED/FAILED_OR_PARTIAL/零退出待审阅；不以网关和原生两个退出码相同为前提 |
| EX-02 | schema 2 的 started、terminationVerified、descendantsTerminationVerified 与原始日志 | 受控子进程中断到 Harness 后仍为 UNKNOWN；未确认后代终止的恢复仍显示风险。长驻 MCP 生命周期由源端原有测试验收 |
| EX-03 | `commands.py recover`，`designcraft-checkpoint-recovery/v1` | 真正调用当前源网关生成报告，再由 Harness 独立核验保存工程、原/重开 runId、步骤和剩余后缀；不自动执行 |
| EX-04 | command/params 单会话计划及 schema 2 stepReferences/stepResults | 保留跨步骤引用、完成前缀、失败步及 NOT_STARTED 后缀；未知版本保守拒绝 |
| EX-05 | schema 2 的输入/资源/工作副本摘要与保全状态 | 执行前漂移不创建输出；执行后漂移保留专门状态与身份、阻止重复调用；源工程原件不变 |
| AV-01 | `business_evidence.py`，`designcraft-business-evidence/v1` | 原始结果重算、当前 AV-02/工程/会话绑定、警告及伪造 PASS 拒绝 |
| AV-02 | `artifact_manifest.py`，`designcraft-artifact-manifest/v1` | 当前候选文件和新会话重开；缺少重开不能登记 |
| AV-03 | `page_review.py`，`designcraft-page-review/v1` | 当前 AV-02、逐页预览与审阅记录摘要；旧预览拒绝 |
| AV-04 | `revision_evidence.py`，`designcraft-revision/v1` | 前后工程、授权范围、影响页闭包、审阅和导出重验；伪造/越界/漂移拒绝 |

源方 `scripts/sync_local_snapshot.py` 是唯一同步入口；`candidate-source.json` 的 `skillFileSha256` 是插件携带的源资源摘要表。交付报告 `evidence/plugin-handoff-20261008.json` 同时列出版本、公开入口、摘要、兼容 fixture 和当前离线报告身份；同一报告复制到插件 `evidence/source-handoff-20261008.json`。它不构成正式发行身份或原生支持清单。

复验：在两个仓库分别运行 `python3 -I -B scripts/record_offline_evidence.py`，确认各自 `scripts/evidence_freshness.py evidence-manifest.json` 中离线和包校验是当前 PASS；插件完整套件包含 `tests/test_execution_handoff.py`、业务/产物/审阅/修订及恢复拒绝测试。比较源技能全部文件摘要、插件六项外部技能实际摘要与 `candidate-source.json`，三者必须完全一致。任一代码、输入、资源或报告变化使旧联合报告失效，需重新记录绑定和兼容测试结果。

执行兼容 fixture 使用当前启动器、网关和 Harness，安装器及原生二进制是隔离临时程序；readiness 只在离线 fixture 中替代。真实 readiness 不被更改，也不会因 fixture 通过而恢复宿主或原生能力。AV fixture 和校验器证明证据合同的一致性，不证明原生执行、视觉判断真实性、人工签核、目标应用兼容性或外部 PDF/X 认证。
