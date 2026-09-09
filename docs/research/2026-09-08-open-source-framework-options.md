# Learn System 免费开源框架选型调研

状态：调研建议，尚未构成架构规范
日期：2026-09-08
范围：单人、单机、离线优先；Python + FastAPI + Flutter；不依赖云服务，不优先引入微服务。

## 结论先行

建议采用以下组合，而不是寻找一个“大平台”包办黑箱：

1. **工作流：Prefect OSS**，只作为 `Local Orchestrator` 的实现适配器；Learn System 的 StepRun 状态和 Artifact Ledger 仍是权威记录。
2. **元数据：SQLite + SQLAlchemy + Alembic**；Flutter 继续用 Drift 读查询投影，不直接写权威 Ledger。
3. **大文件：先实现极薄的 SHA-256 本地 CAS；DVC 只作可选的数据快照/备份工具，不作 Ledger 或运行时 Blob API。**
4. **OCR：保留现有、已经针对中国传统竖排古籍调优的 PaddleOCR + FastAPI/Vue 校订链；不引入第二 OCR 引擎。按 Edition 使用版本化 `OCRProfile`。**
5. **人工审核：暂不引入 Label Studio 作为正式 Review Console。** 它可用于制作 OCR/分类金标集，但不能替代跨阶段审核、Revision、回退和发布签发。
6. **契约与质量：JSON Schema 2020-12 + `jsonschema`；API 边界用 Pydantic；发布表格再加 Frictionless。领域一致性和证据链仍需自研校验器。
7. **全文检索：首版使用 SQLite FTS5；** 古汉语以 trigram/字面检索起步，再按 fixture 评估自定义中文 tokenizer。暂不引入独立搜索服务。
8. **Graph 与发布：规范化 SQLite/JSONL 是权威数据；JSON-LD + RDFLib + SHACL/pySHACL 是图投影与校验；BagIt + RO-Crate 是 PublicationPackage 的完整性与元数据外壳。**
9. **身份验证：当前不安装认证框架。** 只保留 `ActorProvider` 接口，默认返回固定的 `local_owner`；未来线上实现可换成 OIDC adapter。业务对象的稳定 ID 与登录认证是两回事，不能删掉前者。

## 逐项选型

### 1. 单机工作流编排与人工暂停

| 候选 | 许可证/免费性 | 单机复杂度 | 适配评价 |
|---|---|---:|---|
| **Prefect OSS** | Apache-2.0；核心仓库明确声明该许可证 | 中 | **推荐**。原生支持 pause/suspend、带 Pydantic 类型的人工输入和恢复；本地 self-host server 支持 SQLite；Python Pipeline 接入最直接，FastAPI/Flutter 可经本地 REST 查询/恢复 |
| Dagster OSS | Apache-2.0 | 中高 | 资产建模、物化历史和可观察性更强，但本项目已经有自己的 Artifact/Revision/Lineage 领域模型；长时人工暂停不是它相对 Prefect 的直接优势，容易形成第二套资产权威模型 |
| 自研 DAG | 项目自有 | 低起步、高长期成本 | 不建议。重试、恢复、超时、运行状态、并发限制和可观察性会重复造轮子 |

Prefect 官方文档明确支持 `pause_flow_run` / `suspend_flow_run` 等待类型化人工输入，并可从 UI 或 API 恢复；本地配置支持 SQLite。其仓库为 Apache-2.0。[Prefect interactive workflows](https://docs.prefect.io/v3/advanced/interactive)、[Prefect settings and SQLite](https://docs.prefect.io/v3/concepts/settings-and-profiles)、[Prefect repository/license](https://github.com/PrefectHQ/prefect)

Dagster 同样是 Apache-2.0，并明确定位为 data assets 的编排与观察平台。[Dagster repository/license](https://github.com/dagster-io/dagster)

落地边界：

- Prefect flow 对应一个 `EditionPart` 的阶段推进；task 对应 StepRun 执行。
- `awaiting_human` 必须先写 Learn System Ledger，再调用 Prefect pause/suspend；恢复时人工事件也先落 Ledger。
- Prefect 自身数据库、run ID、artifact 概念都不是领域权威；通过 adapter 保存映射即可。
- Flutter 不嵌 Prefect SDK，只调用 Learn System 本地 FastAPI；后者再调用 Prefect API。

### 2. Artifact、CAS 与数据版本

**不建议用 DVC 直接替代 CAS。** DVC 的强项是把数据版本指针放进 Git、使用本地 cache/remote、声明可重放 pipeline；官方说明它无需服务器并能只重跑受影响步骤，许可证 Apache-2.0。[DVC repository/license and model](https://github.com/iterative/dvc)、[DVC command workflow](https://dvc.org/doc/command-reference/)

但 Learn System 还要求固定 SHA-256 地址、版权档位、Artifact Revision、ReviewDecision、双图血缘和本地服务 API；这些都不是 DVC 的领域职责。把 DVC 置于运行时核心还会把 Git revision、DVC pointer、CAS identity 和 Ledger revision 混成三套身份。

建议：

- 权威 CAS 用 `objects/sha256/ab/cd/<digest>` 目录约定、Python `hashlib`、原子 rename 和只读封存；这一层代码很薄，反而比适配 DVC 更可控。
- SQLite Ledger 保存 digest、字节数、MIME、rights、logical role、revision、producer StepRun 与 lineage。
- DVC 可选地管理大型 fixture、可再分发模型或离线备份；不得让 `.dvc` 文件成为唯一 provenance。
- 后续真有跨机器需求时，只替换 BlobStore adapter（本地目录 → S3 兼容存储），不改 Artifact 契约。

### 3. SQLite 元数据与迁移

采用 **SQLAlchemy 2 + Alembic**。SQLAlchemy 对 SQLite、aiosqlite、事务、外键和连接模式有正式支持；Alembic 专门提供 SQLite 的 batch “move-and-copy” 迁移。二者均为 MIT。[SQLAlchemy SQLite docs](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)、[SQLAlchemy license](https://github.com/sqlalchemy/sqlalchemy/blob/main/LICENSE)、[Alembic repository/license](https://github.com/sqlalchemy/alembic)

必须明确：

- SQLite 开启 WAL、`PRAGMA foreign_keys=ON`，Ledger 本地服务保持单写者。
- Alembic migration 是唯一 DDL 变更入口，不允许启动时从 asset 覆盖数据库。
- Drift 只维护工作台本地缓存/只读投影；Dart schema 由发布契约生成或同步验证，不另立领域真相。
- SQLite 官方将交付代码置于 public domain，且 FTS5 可与元数据同库部署。[SQLite copyright](https://www.sqlite.org/copyright.html)

### 4. OCR 与古籍版面

| 候选 | 许可证 | 建议用途 |
|---|---|---|
| **现有 PaddleOCR 管线** | Apache-2.0 | **当前唯一主引擎**。已有中国传统竖排古籍的参数、修复、测试和人工校订工具，优先复用这些真实资产 |
| Kraken | Apache-2.0 | 已评估但当前不采用。它面向多类历史文献，并不能证明比现有、已经针对本项目中国古籍样本调优的管线更合适 |
| eScriptorium | MIT | 暂缓。其历史文档标注/训练能力强，但会引入另一套完整 Web 工作台和部署栈，和现有 M2 UI 重叠 |

来源：[PaddleOCR official repository](https://github.com/PaddlePaddle/PaddleOCR)、[Kraken official repository](https://github.com/mittagessen/kraken)、[eScriptorium repository](https://gitlab.com/scripta/escriptorium)

仍需补齐：版本化 `OCRProfile`、古籍版面类型、字框坐标归一化、人工校订 Revision、异常页终态、证据 anchor 与原始扫描哈希。OCR 框架只生成候选，不能完成 M2 Gate。

### 5. 人工审核与标注 UI

Label Studio Community Edition 是 Apache-2.0，可 pip/Docker 单机运行，默认可用 SQLite，支持图像、文本、矩形框、自定义标注配置、预测预标注和 REST API。[Label Studio official repository](https://github.com/HumanSignal/label-studio)

结论是 **有限采用，不进入正式主链**：

- 值得用于：OCR 字框金标、版面分类、M3 边界标注实验、模型训练集导出。
- 不适合替代：M2 校订编辑器、M3/M4 分歧裁决、八类 ReviewDecision、M7 合并/冲突审核、跨 Revision 继承、CorrectionRequest 和整卷 Gate。
- 原因：接入后仍要写双向转换、权限绕过、Ledger 事件同步和领域状态机；节省的 UI 工作不足以抵消两套任务/用户/项目数据库。其官方 plugin 机制还是 Enterprise 功能，不能把免费版可扩展性估得过高。[Label Studio plugins notice](https://github.com/HumanSignal/label-studio-plugins)

所以正式 Review Console 应继续泛化现有 Flutter 工作台；Label Studio 只作为可删除的 `GoldSetAnnotationAdapter`。

### 6. Schema 与数据质量

分三层使用现成工具：

1. **JSON Schema 2020-12** 定义跨语言 Package/Artifact/StepRequest/StepResult 契约；这是当前稳定规范。[JSON Schema specification](https://json-schema.org/specification)
2. Python 用 MIT 的 **`jsonschema`** 做全量、fail-closed 校验；它完整支持 Draft 2020-12 和逐条错误报告。[python-jsonschema repository](https://github.com/python-jsonschema/jsonschema)
3. FastAPI 内部 DTO 用 Pydantic，但 Pydantic model 不是跨语言唯一规范；应由 JSON Schema 对外冻结。
4. PublicationPackage 中 CSV/JSON 表资源用 MIT 的 **Frictionless** 描述字段、主键、资源和校验报告；它适合表格质量，不适合验证知识语义。[Frictionless repository/license](https://github.com/frictionlessdata/frictionless-py)

不建议当前引入 Great Expectations：它是真正 Apache-2.0 的成熟数据质量框架，但 Learn System 的关键 Gate 是 evidence/lineage/revision/coverage/graph round-trip，而非数据仓库列统计；仍要大量自定义，单机依赖和概念负担偏高。[Great Expectations repository](https://github.com/great-expectations/great_expectations)

仍需自研：原文覆盖无缺口/无重叠、引用字节完全相等、证据链可达、Revision 继承、规则 AST 可执行、发布级别 G1-G7、图往返与跨包 ID 完整性。

### 7. 全文检索

首版直接使用 **SQLite FTS5**。它内建 phrase、prefix、NEAR、列过滤、external-content/contentless 表和自定义 tokenizer API；trigram tokenizer 可做通用子串匹配。[SQLite FTS5](https://www.sqlite.org/fts5.html)

建议两个索引：

- `literal_fts`：trigram，保证古籍连续字串、异体字归一化前后串检索。
- `semantic_terms`：显式 Concept/Alias/Pattern/School 关系的普通表 + FTS，不让 tokenizer 代替领域匹配。

Meilisearch 暂不采用：当前数据规模下，独立搜索服务带来的部署、索引同步和第二套运行状态大于收益；先用 SQLite FTS5 建立真实检索基线，再由召回率和延迟数据决定是否升级。

### 8. Graph 无损投影与打包

建议把“权威数据”和“图投影”分开：

- 权威记录：规范化 SQLite + JSONL/Parquet 表，保留稳定 entity/relation ID、revision、顺序、状态和全部 provenance。
- 图投影：W3C **JSON-LD 1.1**；它是 JSON 兼容的有向图序列化标准。[JSON-LD 1.1 Recommendation](https://www.w3.org/TR/json-ld11/)
- Python 投影/解析：BSD-3-Clause **RDFLib**，支持 JSON-LD、N-Quads、Turtle 与 SPARQL。[RDFLib repository](https://github.com/RDFLib/rdflib)、[RDFLib license](https://github.com/RDFLib/rdflib/blob/main/LICENSE)
- 图结构门禁：W3C **SHACL** + Apache-2.0 **pySHACL**，检查类型、基数、悬空引用与必需边。[SHACL Recommendation](https://www.w3.org/TR/shacl/)、[pySHACL repository](https://github.com/RDFLib/pySHACL)
- 批量分析表：需要时使用 Apache Parquet；不把它当移动端主格式。[Apache Parquet overview](https://parquet.apache.org/docs/overview/)

“无损”不能由 JSON-LD 或 RDFLib 自动保证，必须保留自研 round-trip 门禁：`CanonicalSnapshot → JSON-LD/RDF → CanonicalSnapshot'` 后比较实体数、关系数、稳定 ID 集、字段 canonical hash、列表顺序、revision 和 tombstone。

发布包装采用双层标准：

- **BagIt RFC 8493**：文件清单、SHA-256、完整性验证；`fetch.txt` 可以表达未内嵌的大型/受限远端 payload，正好承接 `reference_and_hash_only`。[RFC 8493](https://datatracker.ietf.org/doc/html/rfc8493)、[Library of Congress bagit-python](https://github.com/LibraryOfCongress/bagit-python)
- **RO-Crate**：用 JSON-LD 描述数据实体、上下文实体、来源、许可证和运行信息；`ro-crate-py` 为 Apache-2.0，支持附着/分离 crate 与 zip 写出。[RO-Crate specification repository](https://github.com/ResearchObject/ro-crate)、[ro-crate-py](https://github.com/ResearchObject/ro-crate-py)

BagIt 不替代 Learn System ReleaseManifest；RO-Crate 不替代领域 Schema。它们是标准外壳，可显著减少校验、交换和长期保存格式的自研量。

## 推荐落地顺序

1. 先落 JSON Schema、SQLite/SQLAlchemy/Alembic、SHA-256 CAS 和固定 `local_owner` ActorProvider。
2. 用 Prefect 做一个 `EditionPart: M1 → awaiting_human → resume → M2 Gate` 纵切，验证状态映射；不要先迁完整 M1-M8。
3. 保留现有 PaddleOCR/UI，先把已存在的命令行参数和必要硬编码收敛成版本化 `OCRProfile`；不做自动寻参或第二引擎。
4. 正式审核继续改现有 Flutter；仅在金标制作明显拖慢时独立试用 Label Studio。
5. M8 先生成 SQLite FTS5 + BagIt + RO-Crate；随后加入 JSON-LD/RDFLib/SHACL 与 round-trip Gate。
6. DVC、Frictionless、Parquet 都是外围工具，按真实数据规模启用，不进入 L0 核心契约。

## 最终“买现成 / 自研”边界

| 可直接复用 | 仍必须由 Learn System 自研 |
|---|---|
| Prefect 的调度、重试、暂停、恢复与运行观察 | `EditionPart` Gate、StepRun 权威状态映射、失效传播 |
| SQLite/SQLAlchemy/Alembic 的存储与迁移 | Artifact/Revision/ReviewDecision/Lineage 领域表 |
| 现有 PaddleOCR 管线的版面和识别候选 | OCRProfile、古籍校订、证据坐标、异常终态、质量门禁 |
| Label Studio 的通用金标标注 | 跨 M2-M7 的 Review Console |
| JSON Schema/jsonschema/Frictionless 的结构验证 | 语义正确性、证据忠实度、规则可执行性、G1-G7 |
| SQLite FTS5 的倒排索引 | Concept/Pattern/School/FactSet 查询契约 |
| JSON-LD/RDFLib/SHACL 的图格式与图约束 | 可逆映射、稳定 ID、Revision/tombstone 与双图语义 |
| BagIt/RO-Crate 的包完整性和通用元数据 | ReleasePolicy、版权档位、KnowledgePack 目录与客户端契约 |

这套组合避免了云依赖与重型微服务，也没有把第三方内部数据库提升为 Learn System 的事实来源；未来换掉任一工具时，M1-M8 的 Package 契约无需跟着重写。
