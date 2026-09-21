# 书籍交付核对清单（NC-020a）

状态：`PREPARING`（骨架已建，待逐条回填实际状态）
创建时间：2026-09-14
依据：`docs/annotation-community/UPSTREAM_DATA_CONTRACT_REPLY.md`、`docs/annotation-community/CONSUMER_ALIGNMENT_RESPONSE.md`

## 1. 核对说明

本清单逐条列出消费端需要上游冻结的项目及其判定标准。每项标注以下三种状态之一：

- **已交付**：上游已提供可验证实现/Schema/样例，消费端已核对通过
- **有回执但未冻结**：上游已回复（ACCEPT/CHANGE），但共同 Schema 未冻结、无真实联调
- **未交付**：上游无回复或明确标注 UNAVAILABLE

状态判定依据：上游回执的 `ACCEPT`/`CHANGE`/`UNAVAILABLE` 标注 + 消费端处理结论 + 实际交付证据。

## 2. 政策与发布门禁

| 编号 | 项目 | 判定标准 | 状态 | 依据 |
|---|---|---|---|---|
| P-01 | 扫描件 PUBLIC_RELEASE 政策 | 扫描件必须 glyphbox_level，有权威规格修订 | 有回执但未冻结 | U-回执 CHANGE；架构 §11/§13/§16 未修订 |
| P-02 | 原生 EPUB/TXT 发布政策 | 按来源类型分支，不将原生来源按旧规则标 PUBLIC_RELEASE | 有回执但未冻结 | U-回执 CHANGE；消费端 §2.1 提案 |
| P-03 | 原件档位与运输方式 | `source_content_level` 与 `packaged/already_stored` 分离 | 有回执但未冻结 | U-回执 CHANGE；消费端 §2.2 处理 |
| P-04 | original_view 可用条件 | 对应原件可授权获取时才 available | 有回执但未冻结 | 消费端 §2.2 明确 |

## 3. 机器 Schema 与文件映射

| 编号 | 项目 | 判定标准 | 状态 | 依据 |
|---|---|---|---|---|
| S-01 | Work/Edition/Source/Asset Schema | 完整字段、类型、必填条件、子包归属 | 未交付 | U-09 UNAVAILABLE；仅 L0 信封 |
| S-02 | ReadingUnit/TextBlock/Page Schema | 覆盖完整阅读内容，与加工 Part/SeparateSpan 分开 | 未交付 | U-02 CHANGE；无发布模型 |
| S-03 | 目录/阅读资源映射文件 | pages.jsonl 或等价承载点，列必填性 | 未交付 | U-回执 §2 要求 |
| S-04 | SourceSpan/SourceAnchor Schema | 有序 ranges、block_id、artifact_revision_id、text_hash、区间 | 有回执但未冻结 | U-05 CHANGE；消费端 §2.1 提案 |
| S-05 | 知识关系 Schema | KnowledgeReference → Assertion → EvidenceLink → SourceSpan | 有回执但未冻结 | U-06 CHANGE |
| S-06 | 迁移记录 Schema | from/to release、精确修订、关系类型、范围映射、歧义原因 | 未交付 | U-07 CHANGE；无实现 |
| S-07 | manifest/canonical_hash 计算规则 | schema_version、delivery_schema_version、文件 hash/manifest_hash/canonical_hash 含义与算法 | 有回执但未冻结 | U-08 CHANGE；消费端 §2.3 |

## 4. D-06 选区与迁移

| 编号 | 项目 | 判定标准 | 状态 | 依据 |
|---|---|---|---|---|
| D-06-01 | 有序跨块 ranges | selector 含有序 ranges，每段绑定 block_id、精确修订、text_hash 与区间 | 未交付 | D-06 未冻结 |
| D-06-02 | Unicode 计数单位 | 固定 unicode_code_point，Python/Dart 一致 | 有回执但未冻结 | U-04 CHANGE；消费端 §2.1 |
| D-06-03 | text_hash 算法 | UTF-8 字节 SHA-256，不加 BOM、不去标点/繁简转换 | 有回执但未冻结 | U-04 CHANGE；消费端 §2.1 |
| D-06-04 | 无知识片段正文锚点 | 阅读块没有 SourceSpan 时也可注解 | 未交付 | 消费端 §2.1 要求 |
| D-06-05 | 拆合迁移规则 | 旧注解保留原始 AnchorRef，解析结果另存 | 未交付 | U-07 CHANGE |

## 5. 资产与交付

| 编号 | 项目 | 判定标准 | 状态 | 依据 |
|---|---|---|---|---|
| A-01 | 原始字节保留 | EPUB/扫描件原件完整保留，无损 | 有回执但未冻结 | A-01 CHANGE；旧存储未迁移 |
| A-02 | 职责分工 | M1 登记源、M2 页图/字框、M3 正文范围映射、M8 打包 | 有回执但未冻结 | A-02 ACCEPT 方向但无交付实证 |
| A-03 | EPUB 原生范围映射 | 保存原 EPUB 元素/范围映射及阅读图片/脚注关系 | 未交付 | A-03 CHANGE；ingest_epub.py 无映射 |
| A-04 | JSONL 装载投影 | M8 输出 UTF-8 JSONL，共同 Schema/文件归属确定 | 未交付 | A-04 CHANGE |
| A-05 | 上传/入库联调 | 真实上传、完成确认、中断恢复、幂等实测 | 未交付 | A-05 UNAVAILABLE |
| A-06 | 旧修订可回看 | 按 hash 去重，临时下载地址与逻辑身份分离 | 有回执但未冻结 | A-06 ACCEPT 方向但无实证 |

## 6. 真实样例

| 编号 | 项目 | 判定标准 | 状态 | 依据 |
|---|---|---|---|---|
| E-01 | 最小样例组 | 各格式原件/派生材料/映射；初版、校订版、拆分版 | 未交付 | §4 第 4 项 |
| E-02 | 重复句/跨块/脚注/图片 | 真实小样本同时含这些边界情况 | 未交付 | §5 共同验收第 1 条 |
| E-03 | 生僻字/组合字符 | emoji、补充平面字符、组合字符均覆盖 | 未交付 | 消费端 §2.1 |
| E-04 | Python/Dart 一致性 | 同一组期望值测试，范围和哈希一致 | 未交付 | §5 共同验收第 1 条 |

## 7. D-07/D-08 依赖登记

| 编号 | 项目 | 判定标准 | 状态 | 依赖说明 |
|---|---|---|---|---|
| D-07 | 排盘规则与流派 | QueryContractPack/SchoolViewPack 由上游交付 | 未交付 | 不阻断独立笔记；真实 Tooltip 关系验收必须等待 |
| D-08 | 流派视图 | SchoolView 由上游定义、生产端映射 | 未交付 | 不阻断独立笔记；阅读协议不替代排盘需求 |

## 8. 汇总

- **已交付**：0 项
- **有回执但未冻结**：12 项
- **未交付**：16 项

结论：NC-020a 骨架已建，所有项目状态为「未交付」或「有回执但未冻结」。NC-020b（上游冻结）BLOCKED 等待上游交付。

## 9. 消费端仍需完成

1. 政策差异稿（按来源类型列证据要求）
2. 机器 Schema 与文件映射表（消费端侧）
3. 上传/入库契约 API 草案
4. Firestore 映射设计
5. D-07/D-08 并行完成（不阻断独立笔记）
