# DesignCraft CLI 0.2.1 原生证据

本目录保存 2026-10-08 在 macOS arm64、Python 3.13.5 上使用固定 DesignCraft CLI 0.2.1 的冷安装与多页样例验证记录。安装落在隔离 runtime-home，不修改全局 PATH。安装归档 SHA-256 为 `e11386860ee88da34a59c79dfedeba2a00166c368d7e99650d97a8db89702aaf`，二进制 SHA-256 为 `e18578b28f43d6c6854ded930065feed5c9ee8af6a2e51338aa675ba4a5723a8`；实际 432 命令目录摘要为 `bf780a8b8a356f6af52e1bdda9319aad2d804b4915148cccf3b1f9c5d3c01700`。

`sample-create-receipt.json` 保存原生模板样例创建结果。`revision-receipt.json` 在第 3 页新增标题 “A Better Grid” 并导出 PDF；其保存工程摘要为 `b7e34dab77d3f1fd21c22dc478bf295ae4ea49ac947a1783aade9e827a5197a6`。`fresh-reopen-receipt.json` 在新的 CLI 会话重开该工程，核对四页、内嵌图片、标题、零错误/警告预检并重新导出四页 PDF。最终工程和 PDF 的路径、格式、字节数、SHA-256 与重开记录在 `artifact-manifest.json`；逐页预览和自动视觉检查在 `previews/` 与 `page-review.json`。两个验证器均通过，但都显式保留 `completeAcceptance: false`。

`overset-negative-*` 是一次故意将标题框缩小后得到的失败样本：网关进程退出码为 0，但原生预检报告溢出错误。这证明零退出不能代表业务验收。最终修正扩大文本框并再次运行预检，错误和警告均为 0。所有原始网关回执仍标记 `NATIVE_EXIT_ZERO_REVIEW_REQUIRED`，不会被提升为完整接受。

本证据只覆盖该固定 CLI 的 macOS arm64/Python 3.13.5 本地运行、样例创建、第三页局部新增、保存、独立 CLI 会话重开、PDF 导出和逐页视觉检查。它不证明真实 Codex 宿主发现/模型路由、数据合并、IDML/EPUB/图像格式、外部 PDF/X 认证、跨项目契约完整兼容或正式发行。原生网关回执中的 `descendantsTerminationVerified` 为 false；单独进程查询在本次观察时未发现遗留 CLI 进程，但该观察不等同于网关终止证明。
