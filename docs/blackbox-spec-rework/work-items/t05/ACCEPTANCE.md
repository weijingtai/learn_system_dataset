# T-05 主 Agent 验收清单

状态：`ACCEPTED`（2026-09-09）

## 1. Scope and Commits

- [x] 提交只修改 `openspec/learn-system-blackbox-architecture.md`（提交 `8720464`，+9, -2）
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未修改工作包文档、TODO.md、PLAN.md、HANDOFF.md 或 `verify-T.sh`
- [x] 提交消息严格为 `docs: define evidence_level enum and release constraints`

## 2. evidence_level Enum and Constraints Verification

- [x] `offset_level` 完整定义（source offset + quote hash，开发级证据）
- [x] `glyphbox_level` 完整定义（扫描页 + 图像哈希 + OCR 字框范围，最终无损证据链）
- [x] 明确写入 `offset_level` 仅可用于 `INTERNAL_DEMO` 与 `DEV_SEARCH`
- [x] 明确写入 `PUBLIC_RELEASE` 必须达到 `glyphbox_level`（引用 TARGET:140）
- [x] §13 M5 G3 门禁条件明确承接 `evidence_level` 校验

## 3. Evidence and Regression

- [x] `docs/blackbox-spec-rework/work-items/t05/TDD.md` 中的全部 Green checks 通过
- [x] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码由 10 严格降为 9
- [x] `T-05` 由 FAIL 转为 PASS
- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查通过
- [x] 主 Agent 质量审查通过
- [x] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`ACCEPTED`。经主 Agent 独立核查代码 diff、全套自动化 checks 以及全局 verify-T.sh 脚本，两档证据级别枚举与发布性约束接线完整准确，符合全部准出条件。
