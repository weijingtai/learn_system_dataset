# HANDOFF

更新时间：2026-07-11
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/learn_system`
刚完成：新增 `tag_system/specs/official-tag-starter-kit.md`，定义第一版官方基础 Tag 图标包/预设包生产规格：`official_starter_clear`、十类物种资产矩阵、qimen/bazi/liuyao TechniqueProfile、官方受控动效、Preview Catalog、AI agents 使用 UIUX Pro Max 的标准设计流程。同步更新 `tag_system/README.md`、`tag_system/EXECUTION_PLAN.md`、`PLAN.md`。
进行到一半的事（精确到文件和章节）：Tag 线现在的第一落点是 Official Tag Starter Kit v0.1，而不是 TagStyleEditor。下一步要制作 A-7 `official_starter_clear` 资产矩阵、A-8 三个 TechniqueProfile、A-9 Preview Catalog；之后再用它作为 TagStyleCompiler MVP 的 golden input。
下一步（第一件事）：让设计/AI agent 读取 `tag_system/specs/official-tag-starter-kit.md`、`tag_system/TAG_SYSTEM_DESIGN.md` §3、`tag_system/specs/mark-taxonomy-and-registry-split.md`、`tag_system/specs/tag-style-system-design.md`，按 UIUX Pro Max 视角为十类物种输出第一版视觉矩阵和 YAML/资产清单。若继续 pipeline，按 `PIPELINE_REVIEW_v1.md` 补依赖声明/环境检查。
已知的坑：当前工作区还有 pipeline 线未提交改动，提交时不要误纳入；第一版官方包允许官方 Flutter 白名单动效和官方 Lottie，但不允许用户 Lottie、animated SVG 或用户 Dart/Flutter；TagStyleEditor、Marketplace、三维稀缺视觉仍冻结。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。
