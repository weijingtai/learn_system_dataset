# T-08 主 Agent 验收清单

状态：`BLOCKED`（R1，等待 D-07）

## 1. Scope and Commits

- [x] 提交只修改 `openspec/learn-system-blackbox-architecture.md`（提交 `4e13439`，+40）
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未修改工作包文档、TODO.md、PLAN.md、HANDOFF.md 或 `verify-T.sh`
- [x] 提交消息严格为 `docs: specify Tag system coupling interfaces and fields`

## 2. Tag System Interfaces & Fields Verification

- [x] §1 系统边界清晰声明 Tag 三个承接接口（`最小盘面概念字典`、`MarkContentBinding`、`EvidenceBundle`）
- [x] §16.3 完整定义三接口供给子包与字段矩阵
- [x] 明确写入「最小盘面概念字典约 100–200 个概念，仅包含稳定 ID + 名称 + 基础类象，**严格声明不含规则 DSL**」
- [x] 明确写入五个关键字段：`omen_carrying`、`condition_affordance`、`school_variance_display`、`concept_id`、`是否改变当前判断`
- [x] 明确写入「是否改变当前判断由知识层供给，**UI 不得猜测**」约束

## 3. Evidence and Regression

- [x] `docs/blackbox-spec-rework/work-items/t08/TDD.md` 中的全部 Green checks 通过
- [x] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码由 7 严格降为 5
- [x] `T-08` 由 FAIL 转为 PASS
- [x] `T-08b` 由 FAIL 转为 PASS
- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查通过
- [x] 主 Agent 质量审查通过
- [x] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`BLOCKED`。T-08 依赖尚未完成的 D-07，并把 M5 错写为生产者、混用了 G4 编号；返工项见 `../../reviews/G3-REVIEW-R1.md`。
