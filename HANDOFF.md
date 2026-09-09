# HANDOFF

更新时间：2026-09-09（G0 启用；D-03 验收；T-02 READY）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户确认启用 `openspec/subagent-delivery-gate.md`，G0 已标为 `ACCEPTED`。已为 D-03 补齐追溯 BDD/TDD/ACT/Prompt，核对提交 `b0022d4` 的三文件范围并完成规格与质量审查，结论 `ACCEPTED`。已为 T-02 建立六件套工作包并通过 ACT 四查，状态 `READY`。
进行到一半的事（精确到文件和章节）：T-02 尚未派发；其 Executor Prompt 位于 `docs/blackbox-spec-rework/work-items/t02/PROMPT.md`。提案前缀为 `art_/rev_/prun_/srun_/pkg_/rel_ + 32hex`，执行者只能作为“待用户确认”写入 §8.1。规格整体仍为 `REVIEW_FAILED_R1`；业务代码、OCR、Schema 和验收脚本没有修改。
下一步（第一件事）：用户把 T-02 Prompt 交给执行 Agent；Agent 返回 commit 与证据后，由主 Agent 按 `ACCEPTANCE.md` 验收，再请用户确认六类前缀。两者完成后才准备 D-02 工作包。
已知的坑：D-02 明确依赖 §8.1 完整 ID 格式，故 T-02 未 `ACCEPTED` 前必须保持阻塞。全局 `verify-T.sh` 当前基线为 18 FAIL / 2 PASS，不能要求 T-02 清掉与其无关的失败。首纵切 10 页 PNG 被 Git 忽略，其他 clone 不可恢复，开工前必须登记到本地 Object Store。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
