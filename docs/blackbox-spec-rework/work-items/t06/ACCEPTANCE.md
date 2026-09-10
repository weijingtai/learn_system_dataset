# T-06 主 Agent 验收清单

状态：`ACCEPTED`（R1，2026-09-10）

## 1. Scope and Commits

- [x] 本轮仅修改 T-06 白名单：架构规格、`verify-T.sh`、TDD、ACCEPTANCE
- [x] 未触碰业务代码、JSON Schema、测试用例、数据库、TODO.md、PLAN.md 或 HANDOFF.md

## 2. EvidenceMapPack Content Verification

- [x] 完整证据链路逐项写出（`KnowledgeEntry → Assertion → EvidenceLink → SourceSpan → SourceAnchor → OcrPage / 字框坐标 → SourceAsset 页标识`）
- [x] 明确声明 SourceAnchor 必须随包发布，严禁留在 M3 内部
- [x] 坐标系与 `SourceAssetPack` 页图像素尺寸同源可换算强约束已声明
- [x] 链路完整性作为 `ValidationReport` 的 fail-closed 检查项已声明

## 3. Evidence and Regression

- [x] `docs/blackbox-spec-rework/work-items/t06/TDD.md` 中的全部 Green checks 通过
- [x] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码由 9 严格降为 8
- [x] `T-06` 由 FAIL 转为 PASS
- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查通过
- [x] 主 Agent 质量审查通过并标记 `ACCEPTED`

## R1 返工证据

- Red：临时交换编号 1/3 后，`T-06s` 非零失败。
- Green：完整七项编号链路通过，`T-06s` PASS；全量门禁与 `git diff --check` 通过。
- Mutation：临时删除首项、末项及把链路词移出编号条目，均使 `T-06s` 非零失败。
- 变更范围：架构规格、`verify-T.sh`、TDD、ACCEPTANCE。

最终结论：`ACCEPTED`。主 Agent 已独立复跑全量门禁、检查有序链路与负向变异设计，未发现越界修改。
