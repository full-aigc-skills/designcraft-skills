# IDML 原生往返与导入后编辑观察

关联任务：源 2.6b，保持开放。固定 CLI 0.2.1 对已提交的 export.idml 重新导入、检查、预检、保存工程及导出 PDF；4 页、19 个 Story，原始输入摘要未变化。`native-output/receipt.json` 保留实际命令、二进制/目录/资源摘要与原始结果。

`pdf-comparison.json` 记录原始 PDF 与往返 PDF 在 1.25 倍 RGB 渲染下四页像素及规范化文本一致。这仅证明该渲染观察，不证明对象语义无损。`formatting-differences.json` 保留工程标题改变、对象/Story ID 重映射、默认字段显式化及 object style 第三项 stroke.weight 从 1.0 到 0.0 的差异。表引用 ID 变化不可直接判作文本格式丢失；后续编辑的样式语义仍未认证。

导入工程的 Story 21 从 A Better Grid 改为 A Clearer Grid，另存新工程并重新导出。新原生会话重开后 story.get 返回新文本；4 页、预检无错误/警告，源工程摘要保持不变。仅 Story 21 内容快照变化，当前渲染差异只出现在第三页，见 edit-observation.json。原生零退出仍是 NATIVE_EXIT_ZERO_REVIEW_REQUIRED。

未运行 InDesign 等外部 IDML 目标应用，不代替其互操作验收；PDF/X 外部认证、完整格式验收及人工创作签核仍未完成。此证据不放行正式发行，不勾选源 2.6b。原始临时路径保留在回执中供身份追踪，归档副本以本目录路径读取。
