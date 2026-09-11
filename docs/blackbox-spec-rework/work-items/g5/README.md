# G5：R1 总准出 —— 文档级状态翻转

状态：`READY`（**只在用户书面确认「进入实现阶段」之后派发**；G5 准出记录见 `docs/blackbox-spec-rework/reviews/G5-EXIT-REVIEW.md`）

## 1. 目标

把规格文件头部的文档级状态从 `REVIEW_FAILED_R1` 改为 `R1_REWORK_CLOSED`，并把头部的 R1 阻断引用块替换为准出说明；其余一个字节不改。§3–§18 每节的四态标签**不动**（T-13 冻结映射由 `verify-T.sh` 锁定；升级为「最终规范」需用户另行批准整份规格，不属 G5）。

## 2. 依据

- PLAN.md「黑箱架构规格 R1 审查返工项」节 44 条全部勾选、0 条未完成（2026-09-11）。
- SUBAGENT_TODO G1/G2/G3/G4 共 36 个大项全部 `ACCEPTED`。
- 三门禁 + `run_all.sh` + `check_d16.py` + fixture `verify.sh` 在 HEAD 干净树全绿（G5-EXIT-REVIEW §2）。
- 用户确认：待填（日期 / 原话）。

## 3. 范围

写：`openspec/learn-system-blackbox-architecture.md` 第 3 行与第 5–7 行引用块；`docs/blackbox-spec-rework/README.md` 第 5 行状态词。禁止：改任何 `## N.` 节内容、任何 `状态：` 节标签、§19/§20/§22。

## 4. 决定

- 新状态词 `R1_REWORK_CLOSED`（不是 `ACCEPTED`/`最终规范`：整份规格未获批为最终规范，只是 R1 返工全部结清、允许进入 §22 首纵切实现）。
- 引用块保留 R1 审查的历史指针，追加准出日期与证据路径。
