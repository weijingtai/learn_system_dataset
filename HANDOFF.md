# HANDOFF

更新时间：2026-09-09（G3 交叉验收 R1：未通过，6 通过 / 6 返工或阻断）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：
- G3 十二个 T 类提交已完成第一轮交叉验收；机器门禁为 0 FAIL，但语义验收仅 T-01/T-03/T-05/T-09/T-10/T-12 通过。
- 详细证据与机械返工项见 `docs/blackbox-spec-rework/reviews/G3-REVIEW-R1.md`。
进行到一半的事（精确到文件和章节）：T-04/T-06/T-11/T-13 需要返工；T-07/T-08 因 D-07 未完成而阻断。
下一步（第一件事）：先重制 T-04、T-06、T-11、T-13 返工包；完成 D-07 后再按 T-07 → T-08 顺序返工，最后重验 G3。
已知的坑：`verify-T.sh` 当前主要检查关键词和数量，0 FAIL 只能证明形式存在，不能证明全文转录、链路顺序、依赖关系和事实时效正确。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
