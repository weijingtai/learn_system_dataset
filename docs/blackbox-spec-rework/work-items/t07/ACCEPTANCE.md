# T-07 主 Agent 验收清单

状态：`BLOCKED`（R1，等待 D-07）

## 1. Scope and Commits

- [x] 提交只修改 `openspec/learn-system-blackbox-architecture.md`（提交 `4bda4a8`，+24）
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未修改工作包文档、TODO.md、PLAN.md、HANDOFF.md 或 `verify-T.sh`
- [x] 提交消息严格为 `docs: map KnowledgePack directories to PublicationPackage artifacts`

## 2. KnowledgePack Mapping Table Verification

- [x] 14/15 个目录条目全量覆盖，无任何遗漏（`concepts`, `entries`, `assertions`, `applicability-rules`, `school-views`, `evidence-links`, `source-spans`, `source-anchors`, `query-contract` 等）
- [x] 表中无空行，所有项均有明确归属
- [x] `optional-vector-index` 显式标注「本期不产出（依据 §21）」
- [x] 包含明确的 KnowledgePack 取代声明（`PublicationPackage` / `KnowledgeDataPack` 取代旧概念）

## 3. Evidence and Regression

- [x] `docs/blackbox-spec-rework/work-items/t07/TDD.md` 中的全部 Green checks 通过
- [x] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码由 8 严格降为 7
- [x] `T-07` 由 FAIL 转为 PASS
- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查通过
- [x] 主 Agent 质量审查通过
- [x] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`BLOCKED`。T-07 依赖尚未完成的 D-07，且 query-contract 当前归属错误；返工项见 `../../reviews/G3-REVIEW-R1.md`。
