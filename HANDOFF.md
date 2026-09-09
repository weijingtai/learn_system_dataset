# HANDOFF

更新时间：2026-09-08（R1 返工转译 v1 后）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：R1 的 38 条返工项及新增 RG 版权边界 2 条，已转译为 `docs/blackbox-spec-rework/` 下 4 个 ACT、13 条转录类和 19 条设计类指令；提交 `f241c83`。首纵切已裁定为七政《三辰通载三十卷》影宋鈔本 10 页、字框级证据、复用现有工作台、496 条空 rule 不作输入。
进行到一半的事（精确到文件和章节）：规格仍为 `REVIEW_FAILED_R1`；40 条要求尚未返工。`bash docs/blackbox-spec-rework/verify-T.sh` 基线实测 19 FAIL / 1 PASS。业务实现未开始。
下一步（第一件事）：执行不需拍板的第 1 轮：ACT 01/02/03、T-11、D-16；PLAN 只增补映射，不重写、不删除既有未完成项。
已知的坑：仍有 7 个拍板点：Ledger 进程模型、Pattern/Concept/KnowledgeEntry 关系、EditionPart 单位、M3/M4 人工队列归属、五处旧存储处置、版权边界、工作台 AI 去留。ACT 04 在 AI 去留裁定前禁止开工；R0-3 原 `grep 192.168 == 0` 标准在“抽象保留 AI”路径不可达。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
