# HANDOFF

更新时间：2026-09-08（七项架构决议落盘后）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户批准 7 项架构决议并写回规格：Ledger 本地进程、三对象关系、按卷 EditionPart、统一 Review Console、旧存储分类处置、三层版权存储、剥离工作台 AI 聊天。新增 `openspec/legacy-storage-transition.md`，并由根 AGENTS/README 强制引导后续 Agent 阅读。
进行到一半的事（精确到文件和章节）：规格仍为 `REVIEW_FAILED_R1`，其余 R1 返工未完成；T 判据仍为 19 FAIL / 1 PASS。迁移只是决议，尚未执行；业务代码未修改。
下一步（第一件事）：请用户复核本次规格与旧路径迁移地图；确认后继续第 1 轮 ACT 01/02/03、T-11、D-16。
已知的坑：`ocr/data_work/index.db` 经源码复核是可重建索引，最终方案改为迁移页面 JSON/校订/审计事实并重建索引；首纵切 10 页 PNG 位于仓库工作目录但被 Git 忽略，其他 clone 不可恢复，开工前必须登记到本地 Object Store。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
