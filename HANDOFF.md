# HANDOFF

更新时间：2026-09-09（Subagent 工作包准出制度建立）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户明确主 Agent 不再亲自实现，只负责把工作项准备为规格、BDD、TDD、ACT、Executor Prompt 和 Acceptance 包，再验收其他 AI Agent 的提交。已新增 `openspec/subagent-delivery-gate.md` 与 `docs/blackbox-spec-rework/SUBAGENT_TODO.md`，按大项/小项跟踪全部执行 Agent 工作；只有主 Agent 核对原始证据后才能勾选完成。
进行到一半的事（精确到文件和章节）：D-03 已由执行代理提交 `b0022d4`，但在新制度下仍处于 `REVIEWING`，尚未补齐 BDD/TDD/ACT 对照和最终验收。规格仍为 `REVIEW_FAILED_R1`；业务代码、OCR、Schema 和验收脚本没有在本轮修改。
下一步（第一件事）：请用户复核 Subagent 准出书面规格；通过后先补齐并验收 D-03 工作包，再准备 T-02 工作包。T-02 完成并确认新增对象 ID 前缀后，才能生成 D-02 的 READY 工作包。
已知的坑：旧执行顺序写成 `D-01 → D-03 → D-02`，但 D-02 明确依赖 §8.1 完整 ID 格式，而 T-02b 仍 FAIL，存在隐式循环依赖；真实顺序必须插入 T-02。首纵切 10 页 PNG 被 Git 忽略，其他 clone 不可恢复，开工前必须登记到本地 Object Store。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
