# HANDOFF

更新时间：2026-09-09（D-02 已验收；R0 依赖解锁包待准备）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：D-02 已由执行 Agent 以 `08fe789`、`fa69901` 两个顺序提交完成；主 Agent独立重跑 `openspec/schemas/verify.sh`，四份 L0 JSON Schema、正反 fixture、真实《穷通宝鉴》manifest 绑定、YAML→JSON round-trip 与离线跨文件 `$ref` 全部通过。全局门禁保持 17 FAIL，无新增退化；D-02 状态为 `ACCEPTED`。
进行到一半的事（精确到文件和章节）：R0 工作台四项尚未制作符合 G0 的标准六件套，旧 `docs/blackbox-spec-rework/act/01.yaml` 至 `04.yaml` 不得直接派发。
下一步（第一件事）：主 Agent 只制作 R0 依赖解锁工作包与执行 Prompt，顺序固定为 `ACT 03 → ACT 04`；解锁后再分别准备 ACT 01、ACT 02。
已知的坑：`pattern_knowledge_workbench` 当前因私有 `ai_core` 的传递依赖版本冲突无法执行 `flutter pub get`。ACT 03 自身不能独立通过构建门禁，须先用引用数和精确 diff 验收，再由 ACT 04 移除全部内网依赖后统一运行 `pub get`、静态检查和测试。禁止用临时 Mock、依赖覆盖或恢复内网服务制造假绿。全局 17 FAIL 属其他未完成 T 类。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。
