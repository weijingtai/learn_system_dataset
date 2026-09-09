# HANDOFF

更新时间：2026-09-09（T-02 第一轮验收需返工）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：独立核对 T-02 第一轮提交 `6e317cc0ddac36935fc2f34f5507ebc8cf1213a5`。范围、八类冻结格式、六类提案存在性、版本轴及机器门禁通过，T-02b 已转绿，全局由 18 降至 17 FAIL。规格/质量审查发现两项阻断，故未验收。
进行到一半的事（精确到文件和章节）：架构规格 :210 要求 StagePackage 物理修订使用 `artifact_revision_id=rev_...`，但 :249/:261 又把 `pkg_...` 定义为物理修订；同时 `<stage>` 没有闭集。已扩充 T-02 的 BDD/TDD/Acceptance 并新增 `REWORK_PROMPT.md`。业务代码、OCR、Schema 和依赖没有修改。
下一步（第一件事）：将 `docs/blackbox-spec-rework/work-items/t02/REWORK_PROMPT.md` 交给同一或另一执行 Agent。返工提交回来后，重跑补充门禁；通过后再由用户确认六类前缀并验收 T-02。
已知的坑：建议保留六个前缀本身，但 `pkg_...` 必须是 StagePackage 逻辑身份，物理版本另用 `rev_...`；`<stage>` 应冻结为 m1–m8。D-02 在 T-02 `ACCEPTED` 前继续阻塞。首纵切 10 页 PNG 被 Git 忽略，其他 clone 不可恢复，开工前必须登记到本地 Object Store。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
