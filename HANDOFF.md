# HANDOFF

更新时间：2026-09-09（T-02 返工通过，待用户确认前缀）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：T-02 返工提交 `376e78c` 已独立验收。补充 Green checks 全部通过，T-02/T-02b PASS，全局保持 17 FAIL，无新增失败；Standards 与 Spec 双轴复核均 `APPROVED`。StagePackage 已使用稳定 `pkg_...` 逻辑身份，物理版本另用 `rev_...`，`<stage>` 已冻结为 m1–m8。
进行到一半的事（精确到文件和章节）：T-02 技术工作全部结束，只剩用户确认 `art_/rev_/prun_/srun_/pkg_/rel_ + 32hex` 六类前缀。业务代码、OCR、Schema 和依赖没有修改。
下一步（第一件事）：取得用户前缀确认，随后把 T-02 标记 `ACCEPTED`，并开始准备 D-02 的 BDD/TDD/ACT/Prompt 工作包。
已知的坑：D-02 在 T-02 `ACCEPTED` 前继续阻塞。全局 17 FAIL 属其他 T 类未完成项。首纵切 10 页 PNG 被 Git 忽略，其他 clone 不可恢复，开工前必须登记到本地 Object Store。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
