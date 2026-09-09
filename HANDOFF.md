# HANDOFF

更新时间：2026-09-08（OCRProfile 参数化设计确认后）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户确认现有中国传统竖排古籍 OCR/FastAPI/Vue 保持主链，不引入 Kraken；已写 `openspec/ocr-profile-parameterization.md`，规定每个 Edition 使用代表页校准、人工验收并冻结的版本化 OCRProfile，首版只做 YAML 参数映射、Schema 校验和运行留痕。当前不实现登录鉴权，只保留固定 `local_owner` 的 ActorProvider。
进行到一半的事（精确到文件和章节）：规格仍为 `REVIEW_FAILED_R1`；RN-2、RN-3 和其余 R1 返工未完成。T 判据仍为 19 FAIL / 1 PASS。迁移只是决议，尚未执行；业务代码未修改。
下一步（第一件事）：请用户复核 OCRProfile 书面规格；通过后，返工仍严格执行 `D-01 → D-03 → D-02`。OCRProfile 实现必须等黑箱 R1 复审通过，且只做薄参数层。
已知的坑：D-02 原排序早于 D-03 会冻结一个没有合法状态枚举的 StepResult Schema，已改为 D-03 之后。首纵切 10 页 PNG 被 Git 忽略，其他 clone 不可恢复，开工前必须登记到本地 Object Store。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
