# T-05 BDD 验收场景

## B1 evidence_level 两档枚举完整定义

Given 权威源 `pipeline/DATASET_ACCEPTANCE_STANDARD.md §4-G3` 规定了通用档与扫描档两类证据要求，
When 执行者查看架构规格 §11 M3 Corpus Compilation，
Then 能找到明确的 `evidence_level` 两档枚举定义：
- `offset_level`（通用档）：每个 span 必须包含 source offset（或等价确定性 anchor）以及 quote hash；
- `glyphbox_level`（扫描档）：在 offset 与 quote hash 基础上，追加扫描页、图像哈希和 OCR 字框范围（四点坐标）。

## B2 发布性强约束绑定

Given 权威源 `LEARN_SYSTEM_TARGET.md:140` 明确声明「纯文本引用只能算开发级证据，不能算最终无损证据链」，
When 架构规格定义证据级别与消费级别的映射关系时，
Then 规格明确规定：`offset_level` 只可用于 `INTERNAL_DEMO` 与 `DEV_SEARCH`，
And `PUBLIC_RELEASE` 必须强制达到 `glyphbox_level`，以确保最终无损证据链。

## B3 M5 G3 门禁条件接线

Given M5 负责执行 G3（身份、引用与证据锚点）自动校验，
When 执行者查看架构规格 §13 M5 Automatic Validation，
Then G3 门禁的校验条件明确包含对 `evidence_level` 的判定规则（目标级别为 `PUBLIC_RELEASE` 时，若仅有 `offset_level` 则直接判定校验失败）。
