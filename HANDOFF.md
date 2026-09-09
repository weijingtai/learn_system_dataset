# HANDOFF

更新时间：2026-09-08
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：在多轮用户确认后形成 Learn System 黑箱内部架构规格 `openspec/learn-system-blackbox-architecture.md`，明确八个加工 Module、三个基础设施 Module、EditionRun/ReleaseRun、整书阶段 Gate、全过程 Artifact Ledger、M2 校订、M3 混合语义切分、M4 多模型交叉复核、增量多版本汇编和 Graph 无损投影；新增根 `CONTEXT.md` 固化核心领域词汇。此前的《穷通宝鉴》审计、七政工作台迁移及源目录清理结论继续有效。
进行到一半的事（精确到文件和章节）：黑箱架构规格状态为 `REVIEW_REQUIRED`，尚待用户复核；根 `PLAN.md` 尚未按规格中的差距矩阵机械重写为实施计划。业务实现未开始。`pipeline/tools/gen_outline.py` 仍漏掉带正文的二级总论；`pipeline/rag/build_index.py` 仍无法解析 glossary 完整 span ID；工作台 `lib/database/drift_database.dart` 仍有启动覆盖本地库、保存即 verified 和版本历史未写入等风险。
下一步（第一件事）：请用户复核 `openspec/learn-system-blackbox-architecture.md`；确认后读取 `writing-plans` skill，把规格第 19 节差距矩阵拆成根 `PLAN.md` 的可执行阶段任务和验收门禁。
已知的坑：工作台 496 rules 全无 original_text/assertion/brief/explanation/notes，verified=0、versions=0；404 条有 conditions、486 条有 chapter。`School` 混合书籍与流派，`pattern_id + school_id` 唯一键不能表达多书多主张；私有内网依赖会阻断干净环境构建。OCR corpus 仍无扫描/字框 anchor；ReleaseBundle、APP Adapter 和注解共享系统尚无实现；`Embedding-AI` 明确后置。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
