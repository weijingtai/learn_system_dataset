# HANDOFF

更新时间：2026-07-11
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/learn_system`
刚完成：按用户要求把 D-015–D-020 从 `TAG_STYLE_SPEC_review_report.md` 回写到 `docs/superpowers/specs/2026-07-11-tag-style-system-design.md` 正文，并同步评审报告状态。关键入口：主规格 §3.3、§4.1、§6.2、§12、§13.4、§14、§17.5、§19、§21；评审报告 §1.1、§5.1、§6。
进行到一半的事（精确到文件和章节）：Tag Style 已可进入 OpenSpec 拆分和基础契约开发准备，但 `tag-style-editor` 仍冻结；`CapabilityRegistry 1.0` 仍依赖上游 `MarkInstance / computed-mark-semantics`、G1–G3 和 `required_slots` 收敛。pipeline 线仍未修订手册或 validator。
下一步（第一件事）：若继续 Tag Style，先建 OpenSpec 上游依赖与 Tag Style 六项当前批次：`tag-style-package-format`、`tag-style-compilation-and-activation`、`tag-style-rendering-contract`、`tag-style-asset-safety`、`tag-style-official-presets`、`tag-style-host-integration`；不要创建当前批次的 `tag-style-editor`。若继续 pipeline，按 `PIPELINE_REVIEW_v1.md` 补依赖声明/环境检查。
已知的坑：当前工作区还有用户/其他 agent 的未提交改动，尤其 `AGENTS.md`、`METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md`、`pipeline/` 等，提交时不要误纳入；Tag Style Registry 字段仍是候选，不得声明破坏性稳定；用户个人审美不硬拒绝，但学习/测试/分享场景必须官方样式或显著标注。
