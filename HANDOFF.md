# HANDOFF

更新时间：2026-07-11
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/learn_system`
刚完成：按用户要求完成 `pipeline/` 首轮真实生命周期的全面评审，新增 `PIPELINE_REVIEW_v1.md`；评审覆盖四本手册、validators 覆盖缺口、raw→RAG 审计链、s13-s110/类型 C-D 扩批风险、v1.1.1/v1.2 设计偏差。未修改 `pipeline/` 下任何现有文件。
进行到一半的事（精确到文件和章节）：评审只产出报告，尚未按报告修订手册或 validator；本地裸 `python3` 缺 `yaml` 模块，validators/RAG 脚本当前不可直接复验，现有 SQLite 索引可读。
下一步（第一件事）：若继续 pipeline 工作，优先补 `pipeline` 的依赖声明/环境检查，并新增 assertion/glossary/RAG index 三类 validator；若回到原 Tag Style 工作，则继续将 D-015–D-020 落实到 v1.2 主规格正文。
已知的坑：`pipeline/` 仍是未跟踪目录，提交时不要误纳入无关历史改动；`RAG_GUIDE.md` 状态落后于现实；ed02 权利链和人工 review 明细尚未闭合；当前工作区还有用户/其他 agent 的未提交改动，勿覆盖。
