# 独立格式验收实测（2026-10-09）

## 结果

- Scribus 1.6.6：实际导入原 IDML 的四页，保存为 SLA、关闭并重开；修改第三页标题、再次保存和重开，修改保留。共八张前后预览，见 qualified/。这证明该应用中的文本编辑与保存重开，不等同 InDesign 认证，也未验证重新导出 IDML。
- 安装工程原用 Source Sans 3 / Source Serif 4 的 OFL 字体后复验，仍有文本框报告 Arial Regular，第四页 u3d 仍报告 overflow=1。视觉预览中颜色圆形保留，但标签等存在表现差异。原因尚未定位，版式保真不判通过。图片由 IDML 解包至临时目录；原始链接路径保留在 SLA，另存 import-assets 副本，跨机器搬迁仍需重链接，不能宣称 SLA 自包含。
- 固定原生 CLI 0.2.1 用 standard=x4 导出当前修订工程：内部 preflight 0 错误/0 警告，四页 PDF 导出警告为空；Qoppa PDFX_4_Profile 独立检查 FAIL，13 条结果记录，含 xmp:MetadataDate、xmpMM:VersionID 缺失以及 RGB 与 OutputIntent 不兼容。原始报告见 native-pdfx4-preflight.txt。普通 PDF 为负对照，266 条记录。
- IDML 为 10 月 8 日格式基线；PDF/X 输入为 10 月 9 日修订工程，二者分别绑定 SHA，不合并为同一产物验收。旧未补字体结果与失败启动日志保留，未算通过。首次启动对话框通过给出已有文档路径绕过；完整复验在同一 Scribus 实例内完成。

## 工具来源与复现

Scribus 官方分发：https://sourceforge.net/projects/scribus/files/scribus/ （1.6.6 arm64；Homebrew cask 安装至用户 Applications）。Qoppa 官方 JAR：https://www.qoppa.com/files/pdfpreflight/jars/v2022R1/jPDFPreflight.v2022R1.34.jar 。二进制哈希见 report.json；不提交应用/JAR。

Qoppa 为 Demo：部分错误细节隐藏，报告可带试用标记；本轮只做 verifyDocument，不转换或修复输入 PDF。VerifyPdfX.java 为实际验证程序。qualified_idml.py 为实际 Scribus 脚本，需按本机路径调整；字体安装记录见 font-install.json。

## 修复与重验要求

1. 原生 PDF/X 导出补齐上述 XMP 属性，并使页面颜色空间与 OutputIntent 一致；重新导出后运行独立 PDF/X-4 检查，结果必须通过，不能以内置预检代替。
2. 定位 IDML 文本样式、字体映射及第四页溢出，分别检查原始 XML 与导入器差异；对相同输入重跑字体齐全的目标应用测试，核对前后页面及编辑保存结果。
3. 固定布局 EPUB 的栅格化、XML 空内容、缺失图片格式命令等原有差距仍有效。OpenSpec 2.6b 保持未完成，本轮不改变验收标准。
