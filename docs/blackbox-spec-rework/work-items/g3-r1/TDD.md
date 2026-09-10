# G3 R1 返工 TDD

## 必须覆盖的语义断言

### T-04

- §13 的 G1–G6 每项必须包含权威标准的实质检查；G7 明确在 M8。
- §16 必须含三级消费级别、完整 G7、风险簇全检、ReleaseManifest、最低 APP 版本、拒绝 `source_release=dev`。
- 删除 G3 锚点、G6 FactSet/AST 或 G7 任一发布拒绝条件时必须失败。

### T-06

- §16 必须按顺序匹配 `KnowledgeEntry → Assertion → EvidenceLink → SourceSpan → SourceAnchor → OcrPage / 字框坐标 → SourceAsset 页标识`。
- 删除首项/末项或交换 Assertion 与 EvidenceLink 时必须失败。

### T-11

- 只允许真实路径 `pipeline/tools/ingest_epub.py`。
- M1/M6/M8 的事实必须与 HEAD 复核结果一致。
- 已由 G2 修复的私有依赖、启动覆盖和保存即 verified 不得继续写成当前缺口；tracked 非 OCR 测试数按 `git ls-files` 统计，不扫描 `.venv`。
- 每个现存差距必须具有可二元判定的命令，观察型命令不算门禁。

### T-13

- 精确校验 §3–§18 的章节号→状态映射。
- §16 章节级仍为待验证假设；“建议一个 Technique 一个 Release”附近另有局部讨论候选。
- 任一最终规范标签必须失败。

### D-07/T-07/T-08

- D-07 冻结 TechniqueProfilePack、QueryContractPack、四接口、FactSet、operator、规则 AST schema version、Profile version。
- 删除四接口之一、FactSet、AST schema version 或 Profile version 时必须失败；可执行 Python 规则必须失败。
- §16.2 的 15 个目录各且仅出现一次，query-contract 唯一归属 QueryContractPack。
- §16.3 逐行校验三个接口、五字段、生产 Module 和目标 Package；生产 Module 中不得有 M5。
- Tag 的 G4 必须命名为 `TAG_SYSTEM_DESIGN.md §12.2` 的 G4，不能与本规格 G4 内容分层门禁混同。

## 通用命令

```bash
git diff --check
bash docs/blackbox-spec-rework/verify-T.sh
```

执行者还必须为每项报告至少一个临时副本负向变异及其非零退出码。当前 `verify-T.sh=0` 不是 Red 基线；只有新增语义断言在旧规格上失败，才算有效 Red。

