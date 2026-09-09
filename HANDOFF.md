# HANDOFF

更新时间：2026-09-09（D-01 身份与修订标识拆分完成）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：D-01 已在 `openspec/learn-system-blackbox-architecture.md` §2 原则 7 与 §8.1 落地并完成质量返工：业务对象及 `ocr_profile_id` 遵守稳定 `entity_id` 语义，物理修订及 `ocr_profile_revision_id` 遵守不可复用的 `artifact_revision_id` 语义；§7 三类 Artifact 引用必须指向冻结修订；StepRun 重跑使用新的 `step_run_id`；ReviewDecision、EvidenceLink、Annotation 同时记录稳定主锚与当时所见修订。PLAN 的 RN-2 与 RA D-01 已勾选并附依据。验证结果：`entity_id` 6 处；原则 7 命中 `artifact_revision_id`；`git diff --check` 通过；`verify-T.sh` 为 18 FAIL / 2 PASS，其中仅 T-02 标题子检查转为 PASS，T-02b 仍为 FAIL；D 提示为 `entity_id=6 / artifact_revision_id=6`。
进行到一半的事（精确到文件和章节）：规格仍为 `REVIEW_FAILED_R1`；RN-3 和其余 R1 返工未完成。迁移只是决议，尚未执行；业务代码、OCRProfile 规格与 Schema 均未修改。
下一步（第一件事）：严格执行 D-03（StepRun 生命周期状态机），完成后再执行 D-02（冻结 L0 机器 Schema）。
已知的坑：StepRun 使用独立 `step_run_id`，不得混入 `artifact_revision_id`；D-02 必须在 D-03 后执行。`verify-T.sh` 的 T-02 目前只是标题子检查假绿，T-02b 仍 FAIL；执行完整 T-02 前必须修正该验证风险。其余未完成 T 项仍会按预期失败，不属于 D-01 失败。首纵切 10 页 PNG 被 Git 忽略，其他 clone 不可恢复，开工前必须登记到本地 Object Store。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
