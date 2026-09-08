# HANDOFF

更新时间：2026-09-08
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：新增根级权威说明 `LEARN_SYSTEM_TARGET.md`，确认 Learn System 的最终目标是把授权古籍编译为存储无关、可追溯扫描证据、可供多术数排盘 APP 确定性匹配并支持私人/公开锚定注解的 KnowledgePack；同步登记现有工具成熟度、缺口、第一条八字纵切和分阶段路线，并更新根 README/PLAN。
进行到一半的事（精确到文件和章节）：尚未实施新纵切。既有 OCR、pipeline、knowledge 和 Tag 文件保持原位；系统集成主线已在 `PLAN.md` 置顶，Tag 线与 OCR 遗留任务继续作为并行支线。
下一步（第一件事）：定义第一条八字纵切的 `KnowledgePack`、`BaziFactSet`、`ApplicabilityRule`、`SourceAnchor` 和 `Annotation` 契约，验收目标为 `丙日干 + 亥月 → 十月丙火 → 原文 → 扫描区域 → 注解锚点`。
已知的坑：多数现有八字 assertions 仍是 `machine_extracted`；OCR corpus 导出未保留扫描/字框 anchor；taskgen 有书名/技法硬编码；RAG concept 链和完整 span ID 索引有缺口；预置 SQLite 需重建验证；ReleaseBundle、结构化盘面匹配、APP Adapter 和注解系统尚无实现；`Embedding-AI` 明确后置。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
