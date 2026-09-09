# 旧存储与旧路径迁移地图

状态：`APPROVED_DESIGN`（2026-09-08）  
执行状态：`NOT_STARTED`

## 1. 何时必须阅读

修改 `ocr/`、`pipeline/`、`pattern_knowledge_workbench/` 的存储、导入、导出、索引或路径代码前，必须先读本文。旧路径仍被源码引用不代表它们是新架构的 Module Interface，也不代表迁移已经完成。

## 2. 总原则

1. 旧数据先分类，再迁移；原始事实、人工校订和审计记录优先保留。
2. 可确定性重建的索引只重建，不把旧索引行迁入正式 Ledger。
3. 不完整或已知错误的知识数据冻结为历史快照，不进入官方知识。
4. 迁移前允许旧实现继续读取旧路径；新 Module 只通过 ArtifactRef 和 Package 交换数据。
5. 迁移完成必须留下 `LegacyImportReport`，记录旧路径、源哈希、目标 Artifact、数量、失败项和验证结果。
6. 本文只登记迁移决议。表中状态变为 `MIGRATED` 前，任何 Agent 都不得声称数据已经进入 Artifact Ledger。

## 3. 权威处置表

| 旧存储或目录 | 当前性质 | 决议 | 未来目标 | 当前状态 |
|---|---|---|---|---|
| `ocr/data_work/data/*.json`、`ocr/data_work/logs/` | OCR 页面、字框、校订历史、异常和审计事实；本地存在但被 Git 忽略 | **迁移** | M2 Artifact、Revision、ReviewDecision 和 Lineage | `ACTIVE_LEGACY` |
| `ocr/data_work/index.db` | SQLite FTS5 派生索引，可由页面 JSON 重建；本地 SHA-256 `d9f1ad9c60915427c307f3191922d3730dc0613b82aa1c78c0989b92ec193886` | **重跑** | M2 查询投影；不是权威 Ledger | `GENERATED_LEGACY` |
| `pipeline/corpus/` | 已有八字、奇门语料与 manifest；部分 raw 文件受 Git 忽略规则影响 | **迁移** | M1/M2/M3 Source、Digitization、Corpus Artifact | `ACTIVE_LEGACY` |
| `pipeline/units/` | 139 个旧知识单元、1331 条 assertion，多数为机器态且上游存在漏编 | **冻结为历史快照** | `LegacySnapshotArtifact`；修复后从 CorpusPackage 重跑 M4 | `FROZEN_INPUT_PENDING` |
| `pipeline/rag/index.sqlite` | 开发索引，已知 span key 碰撞和错链；本地 SHA-256 `e9571d6e64c81ce3e4dbdfaf4134ddbfcfa88bff5d525e4a27c39e7e3bcac22d` | **重跑** | M8 `SearchIndexPack` 查询投影 | `REJECTED_FOR_RELEASE` |
| `pattern_knowledge_workbench/assets/ge_ju_database.sqlite` | 496 条七政 pattern/rule 原型；知识字段、审核和版本数据不完整；Git 已跟踪；SHA-256 `1f25a9304d6b88394f495267d371ea7566ca19de431026b3c79b13340111c764` | **冻结为历史快照** | UI seed；未来只能经独立 `legacy_candidate` 导入流程进入候选区 | `FROZEN_LEGACY` |

### OCR 决议修正说明

早期计划把 `ocr/data_work/index.db` 称为“OCR 工作库并迁移”。源码与 `ocr/docs/PLANS.md` 已证明它是可重建索引；权威校订事实实际位于页面 JSON、edit history、audit 和 anomalies。故最终决议为：**迁移校订事实，重建 index.db**。

## 4. 旧路径的兼容规则

源码中的旧路径按下列状态处理：

- `ACTIVE_LEGACY`：迁移前仍是当前实现的读写位置；修改代码时保持可用，同时新增 Artifact Adapter 测试。
- `COMPATIBILITY_READ`：迁移后只允许 LegacyImportAdapter 读取；禁止新写入。
- `FROZEN_LEGACY`：只读留证；不得作为正式发布输入。
- `GENERATED_LEGACY`：允许删除后重建，但删除动作必须由执行计划明确授权。
- `MIGRATED`：Ledger 中已有核验通过的目标 Artifact；旧路径仅保留迁移报告引用。

路径替换不得做全仓字符串批量替换。每个调用点必须先判断它是在读权威事实、写工作状态、生成投影，还是仅在文档中举例，然后分别接入 Artifact Adapter、查询投影或更新说明。

## 5. 已知源码调用点

| 旧路径 | 主要调用点 | 后续处理 |
|---|---|---|
| `ocr/data_work/index.db` / `index.db` | `ocr/src/gujiorc/core/storage.py`、`index/fulltext.py`、`core/paths.py`、`core/config.py`、`run_sanche10.sh` | 保留为 M2 可重建查询投影；数据源改由 Ledger 导出的页面 Artifact 驱动 |
| `pipeline/corpus/` | `pipeline/runner/ingest_raw.py`、`ocr/src/gujiorc/core/export.py` | 迁移期由 Corpus Artifact Adapter 双写或导出；切换后目录成为可重建兼容投影 |
| `pipeline/units/` | `pipeline/tools/assemble_units.py`、`pipeline/rag/build_index.py` | 停止作为正式输入；新 M4 从版本化 CorpusPackage 生成 CandidatePackage |
| `pipeline/rag/index.sqlite` | `pipeline/rag/build_index.py`、`query.py`、`validators/validate_rag_index.py` | 由 M8 编译器重建为 SearchIndexPack；旧库永不升级为正式发布索引 |
| `ge_ju_database.sqlite` | `pattern_knowledge_workbench/lib/database/drift_database.dart`、`pubspec.yaml` | 只作初始 UI seed/历史样本；正式 ReviewDecision 写入 Ledger，本地库仅为查询投影 |

完整引用清单应在每次迁移批次前重新生成，不能把本表当作永不变化的缓存：

```bash
rg -n 'index\.db|index\.sqlite|pipeline/corpus|pipeline/units|ge_ju_database\.sqlite' \
  ocr pipeline pattern_knowledge_workbench
```

## 6. 首纵切素材的可移植性警告

`ocr/data_work/sanche_pages/page_001.png` 至 `page_010.png` 当前存在于本机工作目录，但被 `.gitignore` 忽略，`git ls-files` 不会列出它们。它们是首纵切本地 SourceAsset，不是可由 Git 克隆恢复的仓库资产。

首纵切开始前，M1 必须把源 PDF 或派生页图登记到本地 Object Store，记录 SHA-256、页数、派生关系和权利状态。其他 Agent 若缺少这些文件，应报告 `BLOCKED_SOURCE_ASSET_MISSING`，不得创建空文件、替代图片或伪造哈希使验收变绿。

## 7. 迁移完成判定

单个旧存储只有同时满足以下条件才可把状态改为 `MIGRATED`：

1. 源文件和源哈希已冻结；
2. 目标 Artifact 数量、关系数量和哈希已记录；
3. 人工校订、失败记录和来源关系无丢失；
4. 新路径查询结果通过抽样与全量计数校验；
5. 旧源码调用点已改为 Adapter、兼容投影或明确的只读快照；
6. `LegacyImportReport` 已进入 Artifact Ledger 并在 `PLAN.md` 勾选对应任务。
