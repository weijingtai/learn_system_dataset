# HANDOFF

更新时间：2026-09-09（D-02 工作包 READY）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：D-02 标准工作包已制作并经两轮 ACT 审查达到 `READY`。包内冻结四个 JSON Schema 的字段、正反 fixture、真实《穷通宝鉴》manifest 绑定、YAML→JSON round-trip、两份顺序 ACT、开源校验依赖边界和防假绿门禁。主 Agent 未实现任何 Schema 或验证器。
进行到一半的事（精确到文件和章节）：等待用户派发 `docs/blackbox-spec-rework/work-items/d02/PROMPT.md`。D-02 必须由执行 Agent 按 ACT01、ACT02 两个独立提交完成。
下一步（第一件事）：执行 Agent 返回两个 commit 与 Red/Green 原始证据后，主 Agent 按 `ACCEPTANCE.md` 做范围、机器、规格和质量验收。
已知的坑：全局 17 FAIL 属其他 T 类未完成项。执行 Agent 不得实现 Ledger/Orchestrator 或自行增加第五份 Schema；`check-jsonschema` 安装或本地 `$ref` 解析失败时必须停止报告。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
