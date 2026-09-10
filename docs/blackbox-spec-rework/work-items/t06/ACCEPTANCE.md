# T-06 主 Agent 验收清单

状态：`REWORK_REQUIRED`（R1，2026-09-09）

## 1. Scope and Commits

- [x] 提交只修改 `openspec/learn-system-blackbox-architecture.md`（提交 `1e52327`，+6）
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未修改工作包文档、TODO.md、PLAN.md、HANDOFF.md 或 `verify-T.sh`
- [x] 提交消息严格为 `docs: define EvidenceMapPack content and lossless evidence chain`

## 2. EvidenceMapPack Content Verification

- [x] 完整证据链路逐段写出（`EvidenceLink → Assertion → SourceSpan → SourceAnchor → OcrPage / 字框坐标 → SourceAsset 页标识`）
- [x] 明确声明 SourceAnchor 必须随包发布，严禁留在 M3 内部
- [x] 坐标系与 `SourceAssetPack` 页图像素尺寸同源可换算强约束已声明
- [x] 链路完整性作为 `ValidationReport` 的 fail-closed 检查项已声明

## 3. Evidence and Regression

- [x] `docs/blackbox-spec-rework/work-items/t06/TDD.md` 中的全部 Green checks 通过
- [x] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码由 9 严格降为 8
- [x] `T-06` 由 FAIL 转为 PASS
- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查通过
- [x] 主 Agent 质量审查通过
- [x] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`REWORK_REQUIRED`。证据链遗漏 KnowledgeEntry 且倒置 Assertion/EvidenceLink；返工项见 `../../reviews/G3-REVIEW-R1.md`。
