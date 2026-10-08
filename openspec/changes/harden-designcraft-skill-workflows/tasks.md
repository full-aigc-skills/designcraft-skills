## 执行约定

本清单跟踪实现与验收：当前 28 项已完成、5 项开放（共 33 项）。已勾选项仅代表其列出的验收范围已完成，不代表原生、宿主、平台或发行验收整体完成。P0 为执行正确性及交付证据，P1 为技能体验及验证覆盖，P2 为跨项目交接与收尾。各组内先建立可暴露目标行为的失败测试，再实现和回归；不得用环境故障代替行为红灯。

需求编号对应本 change 的四份 specs；共享语义以技能源为事实源。关联插件 change：`harden-designcraft-plugin-delivery`。插件来源/状态夹具可并行设计，但 PH 执行和完成验收分别依赖本清单第 1、2 组。安装、Git、提交和发布仅在已有对应授权下执行；本次编写清单不构成这些动作的授权。

## 1. P0 执行状态、进程与恢复

- [x] 1.1 [EX-01, EX-02, QG-02] 建立启动器→网关的受控真实子进程回归，先复现内层超时被降级为普通失败，并覆盖启动前失败、中断与未确认终止；证据：行为红灯及保留日志的测试输出。
- [x] 1.2 [EX-01, EX-04] 定义版本化机器结果文件及回执 schema，保留原生 stdout/stderr 和旧入口；证据：成功、UNKNOWN、截断/缺失/未知版本及旧回执 fixture 的兼容测试。
- [x] 1.3 [EX-01, EX-02] 实现内层状态向外层无损传递，分开短任务与 MCP 生命周期并记录 terminationVerified；证据：1.1 回归通过及 MCP stdio 未混入元数据的检查。
- [x] 1.4 [EX-03, EX-04] 编辑前落盘 runId、计划/输入/资源/运行时/目录摘要，记录逐步结果并维持 command/params 单会话引用；证据：跨步骤 Story 引用、部分失败与身份缺失的行为测试。回执保存版本化执行身份、原生计划摘要和顺序化 command/params 引用；只有批次状态时按 `BATCH_EXIT_ZERO_REVIEW_REQUIRED` 或 `UNKNOWN` 保守标记；固定 CLI 若给出完整 `completed`/`failedIndex`/`failedCommand`/`results`，则摘要绑定已完成前缀、失败步标为 `STEP_FAILED_OR_PARTIAL`、未启动后缀为 `NOT_STARTED`。失败步仍可能产生副作用，不允许自动重试。行为测试覆盖结构错配回退 UNKNOWN、旧回执只读及身份漂移拒绝；固定 CLI 原生只读失败探针 run `c64c358f-303a-41d7-b355-1e0daae71651` 验证前缀已完成、失败索引与未启动后缀被区分，失败步不重试。回执及二进制/目录摘要见 `evidence/native/designcraft-cli-0.2.1/partial-step-observation-20261008/`；1.5 的重开工程检查点恢复保持独立开放。
- [ ] 1.5 [EX-03, EX-04] 实现仅基于已保存重开工程的检查点核对和剩余步骤恢复，旧回执缺字段时只读诊断；证据：重复副作用被阻止、跨会话重新发现对象及检查点错配拒绝测试。
- [x] 1.6a [EX-05, QG-02] 实现登记输入和技能资源执行前后复核、DesignCraft 源工程工作副本及新输出目录约束；证据：漂移阻止原生编辑且不创建输出、源工程原件不变、零退出后资源漂移将回执降级并保留计划/日志，且不声明回滚或完成。离线受控子进程测试和完整套件通过。
- [x] 1.6b [EX-05, QG-03] 在获得固定 CLI 0.2.1 原生验收授权后验证参数内路径、登记输入和输出覆盖范围的真实行为；证据：`evidence/native/designcraft-cli-0.2.1/path-side-effects/` 绑定实际二进制、目录摘要和运行回执。固定 CLI 将 PDF 写到 `--output` 外的未登记参数路径，该文件实际生成但不在 `inputAfterSha256`；同一计划另将 PDF 写入显式登记的输入目录，新文件出现在执行后摘要并将回执降为 `INPUT_CHANGED_REVIEW_REQUIRED`。这证明登记范围可检测执行后变化，但不阻止写入；参数内路径可在当前 OS 权限范围内写入任意位置，不被自动限制到 `--output`。

## 2. P0 业务结果与可编辑交付验收

- [x] 2.1 [AV-01, QG-03] 在具备原生安装授权后采集固定 CLI 0.2.1 的预检、合并和导出实际结果，标明二进制与目录摘要；证据：脱敏原始样本和字段差异记录。固定二进制和目录摘要绑定的真实样本现位于 `evidence/native/designcraft-cli-0.2.1/business-assessment/`：预检返回零错误与低分辨率警告、CSV 字段清单、`data.merge` 返回 records/pages、五页 PDF 导出与实际字节数均有原始回执。单独含 `{{Name}}` 的样例保留了原样占位文本，所以合并计数不被描述为字段内容验收。
- [x] 2.2 [AV-01, QG-02] 先写零退出但溢出/缺图/警告及未知字段的拒绝测试，再实现按任务策略分类业务问题；证据：原始问题定位、接受依据和不兼容状态的回归。`designcraft-business-assessment/v1` 在六项独立技能入口同步，未知结果字段返回 `UNKNOWN`，溢出和缺失链接返回 `REJECTED`，预检警告与未核对内容的合并计数返回 `REVIEW_REQUIRED`。证据包括固定 CLI 0.2.1 原始溢出、低分辨率、链接缺失回执及离线业务分类回归；原始进程状态仍保持 `NATIVE_EXIT_ZERO_REVIEW_REQUIRED`，分类结果不能替代创作接受。
- [x] 2.3 [AV-02] 实现期望产物契约与清单，核对路径、格式、字节数、SHA-256 和工程保存后新会话重开；证据：只有回执无工程必失败，以及页数、尺寸、关键文本和链接素材重开检查。固定 CLI 0.2.1 在隔离 macOS arm64 runtime-home 冷安装后，执行四页工程保存和新 CLI 会话重开；工程 SHA-256、4 页尺寸、第三页标题、内嵌链接素材、PDF 字节数/摘要均被记录。证据：`evidence/native/designcraft-cli-0.2.1/{artifact-manifest.json,native-evidence-summary.json,fresh-reopen-receipt.json}`；产物清单验证通过，仍显式标记 `completeAcceptance: false`。
- [x] 2.4 [AV-03] 建立排版 rubric 和绑定工程/预览摘要的逐页审阅记录，区分结构、视觉、输出、可编辑性和人工/自动来源；证据：旧候选审阅拒绝及无参考图按任务规范审阅的案例。固定 `designcraft-layout-rubric/v1` 记录绑定修订后工程、AV-02 清单和四页实际 PDF 渲染；自动视觉审阅按结构/视觉/输出/可编辑性分别记录。无参考图时以规格文件摘要作依据。证据：`evidence/native/designcraft-cli-0.2.1/page-review.json` 与 `previews/`；页审阅校验通过。审阅报告只证明记录和摘要绑定，不证明评审判断客观真实或整体验收完成。
- [x] 2.5a [AV-04, QG-02] 建立规范化页/对象/Story 修订回执校验，核对授权范围、对象快照差异、Story 影响页闭包、修订前后 AV-02/AV-03 身份和全部既有导出的修订后重验绑定；证据：第三页标题、跨页 Story 影响、越权变化、影响页遗漏、旧导出摘要和回执摘要漂移 fixture 均通过。该校验只证明证据链内部一致，不证明原生操作或审阅事实。
- [x] 2.5b [AV-04, QG-03] 用固定 CLI 0.2.1 将第三页 Story 65 标题从 `A Better Grid` 修订为 `A Considered Grid`；原生回执绑定二进制 SHA `e18578b…a5723a8`、命令目录 SHA `bf780a8…01700` 与三个执行计划。新会话重开确认 4 页及新标题，preflight 0 errors/0 warnings，重新导出 PDF 4 页/552605 bytes；修订快照仅检测到 frame 64 / Story 65 变化，影响页闭包为 `[3]`。修订前后 AV-02 清单、四页预览摘要、页审阅和导出 SHA 均通过 `revision_evidence.py` 关联校验。重开 `document.inspect` 的 spread 列表未列出 frame 64，但 `story.get` 返回 frame 64 与完整新文本；审阅记录明确以 Story 查询及修订前页面几何绑定，并将该限制保留为可审查事实。证据：`evidence/native/designcraft-cli-0.2.1/av04-revision/`。自动视觉审阅与结构校验不代表客观设计签核或整体完成验收。
- [x] 2.6a [AV-01, AV-04] 建立 PDF、IDML、EPUB、PNG/JPEG/WebP/TIFF 的离线结构探针，明确内部结构检查不代表视觉、可编辑性、损失、应用重开或外部 PDF/X 认证；证据：PDF 页对象/页面框、压缩或缺少结构时的 PARTIAL、图片头部尺寸、IDML 包/XML、EPUB 容器/manifest/spine、路径越界与错误包 fixture 均通过。探针摘要绑定文件大小/SHA-256，`completeAcceptance` 始终为 false。
- [ ] 2.6b [AV-01, AV-04, QG-03] 已用固定 CLI 0.2.1 观察 PDF、IDML、reflow EPUB、fixed-layout EPUB、HTML 和 XML 原生导出，绑定二进制 SHA `e18578b…a5723a8`、目录 SHA `bf780a8…01700` 与隔离四页工程。证据：`evidence/native/designcraft-cli-0.2.1/format-export-20261008/`。PDF/IDML/两类 EPUB/HTML 有文件产物，IDML 与 EPUB 结构探针通过；fixed EPUB 包含四张整页 PNG（外观栅格化，文本/向量编辑语义损失），reflow EPUB 只有单个 spine 文档与两张嵌图（分页及网格不保留）。XML 仅含空 `Root`（71 bytes），按空内容拒绝；同批 `file.exportText` 未产生结果并导致 `FAILED_OR_PARTIAL`。Chrome headless 仅提供 HTML 浏览器预览。当前环境无 InDesign 或 EPUB 桌面阅读器，IDML/EPUB 应用重开和视觉复核未运行；PDF/X 外部认证未运行；PNG/JPEG/WebP/TIFF 无固定目录导出命令。结构探针不替代目标应用验收，以上限制未满足 2.6b 完整门槛，任务保持开放。

## 3. P1 技能路由、领域资料与命令覆盖

- [x] 3.1 [SK-01, SK-02] 为现有六项技能补齐适用范围、输入前置、副作用、交接、恢复及验收，use 保持唯一通用路由；证据：通用手册、显式导出和无关请求的正反例路由表。
- [x] 3.2a [SK-02, SK-03] 补齐 document/layout/export 的成功、既有工程修改和失败恢复场景材料；证据：重开工程/UNKNOWN、文本串联、图像、溢出、PDF/IDML 导出案例及本地审阅参考均明确标记为场景合同，不声称原生支持。
- [x] 3.2b [SK-02, SK-03] 用固定 CLI 目录核对并补充样式调整和数据合并的真实命令/参数映射及执行记录；证据：目录摘要绑定的命令说明和场景回执。固定 CLI 0.2.1 的 `style.paragraph.create/apply`、`data.fields {csv}`、`data.merge {rows}` 和 PDF 导出说明与实际回执已加入 `skills/designcraft-cli/references/command-plans-and-receipts.md` 及 `evidence/native/designcraft-cli-0.2.1/business-assessment/`。目录摘要为 `bf780a8b8a356f6af52e1bdda9319aad2d804b4915148cccf3b1f9c5d3c01700`；合并字段内容仍标记需人工/结构核验。
- [x] 3.3a [SK-03] 建立绑定研究仓库与源码摘要的 `RESEARCH_SOURCE_ONLY` 清单及过期检查器；证据：fixture 验证来源 commit/文件变化会使清单失效，保持研究源码与固定制品命令的边界。
- [x] 3.3b [SK-03] 使用固定 CLI 二进制与目录摘要构建唯一 `ownerSkill` 命令覆盖表；证据：`evidence/native/designcraft-cli-0.2.1/command-catalog.json` 保存 432 项真实目录，`scripts/build_native_command_coverage.py` 按工程生命周期/版面/导出职责赋予唯一 owner；包校验核对锁定 CLI 版本、二进制 SHA-256、目录 SHA-256 和目录 ID 全集，并以 fixture 拒绝重复、遗漏、研究独有 ID 与非 DISCOVERED 新项。目录发现不代表逐项执行验收。
- [x] 3.4 [SK-04, QG-01] 确立 canonical 执行资源及确定性分发/漂移检查，统一实际加载目录定位规则；证据：每项技能单独复制到中文空格路径后离线 list/describe/check 通过，不存在兄弟技能仍可运行。
- [x] 3.5 [SK-04, QG-02] 补充离线查询与在线安装边界说明及拒绝测试；证据：离线 catalog 的 run 在安装/编辑前拒绝，缺安装授权时只执行已有离线能力。
- [x] 3.6 [SK-01, SK-04] 按首个 Codex 宿主所需提供源技能发现元数据，通用 use 与显式原子入口职责一致；证据：六项 frontmatter 与技能路由矩阵静态校验、六个 SKILL.md 的插件快照清单；真实模型路由仍由插件 HI-01 验收。
- [x] 3.7 [SK-02, QG-05] 按 Dreamina 渐进披露与场景质量模式审查六项技能：入口保留触发/边界/前置/副作用/交接/恢复，细节放在本技能 references，组合步骤放在 examples；补齐每项职责对应的成功和拒绝/恢复案例，并扩展包检查验证链接与覆盖。证据：六项覆盖矩阵、缺引用/缺案例 fixture 被拒绝、全套 67 项离线测试与包校验通过；文档示例与原生验收状态明确分离。

## 4. P1 独立测试与固定制品验收

- [x] 4.1 [QG-01, QG-02] 将依赖真实兄弟插件的同步测试改为自建临时 fixture，并补来源错配、用户改动、链接越界、未审查删除和中断复制场景；证据：仅技能源独立检出即可运行完整离线测试。
- [x] 4.2 [QG-01, SK-02, SK-04] 扩展包校验覆盖实际技能集合、frontmatter、500 行限制、资源、所有 Markdown 引用及命令覆盖；证据：故意破坏 fixture 被拒绝、正式包检查通过。
- [x] 4.3 [QG-03] 在已授权的隔离 runtime-home 完成 macOS arm64 和实际 Python 版本的冷安装→目录→创建→编辑→保存→重开→导出；证据：固定制品摘要、实际命令/日志、工程与导出身份。固定 CLI 0.2.1 在隔离 runtime-home 冷安装并校验 archive/binary SHA-256；捕获 432 命令目录，完成四页样例创建、第三页标题新增、保存、独立会话重开和 PDF 重导出，过程与摘要保存在 `evidence/native/designcraft-cli-0.2.1/`。本项限于 macOS arm64 / Python 3.13.5；网关回执仍为 `NATIVE_EXIT_ZERO_REVIEW_REQUIRED`，不等于全局接受。
- [x] 4.4 [QG-03, QG-02] 验证污染/损坏制品和不支持平台的拒绝行为；证据：安装失败前后的文件状态、错误分类及未执行原生写入记录，不安装额外平台来模拟支持。
- [x] 4.5 [QG-04] 建立分层证据清单与失效判定，分别记录离线、原生、CI、宿主、平台、创作状态；证据：运行时/源码/输入摘要改变后受影响证据失效的回归及当前 NOT_RUN 项。已实现绑定源码、运行时锁、目录、环境、输入和产物的证据清单，漂移回归覆盖上述输入；生成器刷新离线运行记录，状态检查器逐层核对 project-status.json，未执行层保留 NOT_RUN。

## 5. P2 跨项目交接与规范收尾

- [ ] 5.1 [EX-01, EX-04, AV-02, QG-04] 向插件交付共享契约版本、资源摘要、兼容 fixture 和验证报告；依赖第 1、2 组，证据：插件 PH-01/PH-03 联合兼容检查，不直接改写插件 vendored 文件。AV-02 已发布本地候选契约 `designcraft-artifact-manifest/v1`，同步器刷新了插件外部技能快照；新增插件 Harness 公共入口 fixture 验证可保存/只读展示 EX-03/04 的 `runtimeIdentity` 与批次级 `stepResults`，且 `resumeAllowed` 保持 false；同步后插件完整离线套件复验通过。EX-01～EX-05 与 AV-01/03/04 的联合兼容证据仍不齐，任务保持开放。
- [x] 5.2 [QG-01, QG-04] 配合插件 SP-04 加固本项目拥有的同步器，按已验证旧快照暂存、核验、发布新快照，保护用户改动和来源锁；证据：独立临时源/插件正常、拒绝及中断恢复测试。
- [ ] 5.3 [QG-04] 汇总本项目验收和开放项，在另有 Git/发行授权且必要门禁通过后形成真实技能源发行身份供插件 SP-02/RG-03 锁定；证据：实际 repo/tag/解析 commit/版本/内容摘要，不制造未存在的发行记录。
- [ ] 5.4 [QG-04] 对照全部需求逐项核验实现和当前证据，完成后才同步主规范并归档；证据：追溯表、OpenSpec 严格校验和无未完成验收项。仅计划产物齐备不得勾选。
