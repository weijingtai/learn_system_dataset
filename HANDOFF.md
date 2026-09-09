# HANDOFF

更新时间：2026-09-09（T-02 已验收，六类 ID 已写入 README）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户确认 `art_/rev_/prun_/srun_/pkg_/rel_ + 32hex` 六类格式。根 README 已增加每个前缀的对象含义、稳定性和换号规则；架构 §8.1 已从“提案”更新为“确认并冻结”；T-02 验收与总 TODO 已标记 `ACCEPTED`。
进行到一半的事（精确到文件和章节）：D-02 的 D-03/T-02 前置依赖均已满足，但标准工作包尚未制作。业务代码、OCR、Schema 和依赖没有修改。
下一步（第一件事）：主 Agent 准备 D-02 的 README、BDD、TDD、ACT、Executor Prompt 和 Acceptance，并通过 ACT 四查；不亲自实现 Schema。
已知的坑：全局 17 FAIL 属其他 T 类未完成项。D-02 必须同时表达逻辑 ID 与不可变 Revision，尤其 StagePackage ArtifactRef 同时携带 `stage_package_id` 和 `artifact_revision_id`。首纵切 10 页 PNG 被 Git 忽略，其他 clone 不可恢复，开工前必须登记到本地 Object Store。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
