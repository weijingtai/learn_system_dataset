# HANDOFF

更新时间：2026-09-09（G2 已验收；下一批进入 G3）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：
- G2 R0 零号批次已全部完工并由主 Agent 验收标记 `ACCEPTED`：
  1. ACT-03 (`ffda853`): 删除零引用内网依赖 `enumeration`。
  2. ACT-04 (`2e11932`): 剥离内网私有 `ai_core` 依赖与聊天旁路，`flutter pub get`、`flutter analyze` (0 warning)、`flutter test` 完全解锁。
  3. ACT-01 (`f7ffd2f` 红测试, `3d6cfd2` 绿实现): 修复启动时 asset SQLite 覆盖本地数据库，改为缺失时播种。
  4. ACT-02 (`424dc9a` 红测试, `54c0497` 绿实现): 修复保存与 AI 产物自动置 verified，人工编辑不再静默置 verified，AI 产物强制置 false，保留显式勾选通道。
- 全局门禁 `bash docs/blackbox-spec-rework/verify-T.sh` 保持 17 FAIL，退出码 17，无退化。
进行到一半的事（精确到文件和章节）：G3 尚未制作标准工作包；`verify-T.sh` 当前为 17 FAIL / 2 PASS。
下一步（第一件事）：制作 T-03 六件套，要求保留 D-03 已冻结的 StepRun 状态；随后依次制作 T-01、T-04。三个执行任务均写同一架构规格，必须串行派发。
已知的坑：T-03 的旧转录说明仍写“Artifact status / StepRun status 只建空表并标注 TODO(D-03)”，但 D-03 已完成，现应接入既有状态全集，禁止回退为空表。T-04 依赖 T-03 的内容状态，必须后执行。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
