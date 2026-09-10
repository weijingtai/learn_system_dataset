# 书籍交付：消费端对上游回执的处理

状态：`PROPOSED_ALIGNMENT_NOT_FROZEN`；2026-09-10。

依据：[上游核对回执](UPSTREAM_DATA_CONTRACT_REPLY.md)。本文件记录消费端接受的修订及下一次共同冻结所需材料，不代替上游改写发布政策，不声称 Schema、生成器、上传通道或正式样例已交付。上游原回执保持原样。

## 1. 消费端结论

架构可继续推进：上游一次生成完整阅读数据与定位映射，Python 后端验证并机械装载，原件/大对象进对象存储，Firestore 保存版本化元数据、阅读投影和关系；UGC 独立。无需下游再解码 EPUB、OCR、去空格、拆章或重新分配原文身份。

上游回执不是可执行交付协议。U-01～U-08 均为 CHANGE、U-09 为 UNAVAILABLE；A-02/A-06 接受职责方向但无交付实证，其余有修改或实现缺口。本轮接受下列消费设计修订；“共同冻结”和“生产接通”保持未完成。

## 2. 六项差异的处理

| 差异 | 消费端处理 | 仍需上游交付/联合定案 |
|---|---|---|
| 原生 EPUB/TXT 无扫描字框 | 赞同按来源类型验证精确来源，不制造 OCR 页；扫描仍保留字框链，EPUB/TXT 固定原件修订和原生范围 | 正式修订架构 §11/§13/§16、TARGET 及相应验证器的一致政策；未经批准不把原生来源按旧规则标 PUBLIC_RELEASE |
| 原件档位与运输方式混淆 | 将 `source_content_level` 与 `packaged/already_stored` 分开；不要求每个档位都重新携带原件 | 上游确认字段与已有 ReleasePolicy 对应；声明 original_view 的原件必须在交付中或被后端验证可取 |
| 阅读全文不等于知识片段 | ReadingUnit/TextBlock 覆盖完整声明阅读内容，和加工 Part/SourceSpan 分开 | M2/M3 保留全文、空白/脚注/资源与映射；M8 导出范围覆盖报告和身份一致的阅读投影 |
| 跨块选区与无知识片段正文 | selector 改为有序 ranges；单块也是一段。需要能锚定未抽出知识的阅读正文 | D-06 增合法结构锚点/阅读块目标，或提供等效权威表示；消费端不伪造 SourceSpan、不自行宣布新 target_type 已批准 |
| 交付文件缺口 | 增 pages、目录/阅读资源、SourceSpan/SourceAnchor 及依赖包引用的承载要求 | 每个 record_kind 的 Schema、必填条件、所属子包与真实输出文件；图谱/SQLite/JSONL 同源而非三套身份 |
| 排盘规则和流派 | 阅读/社区协议不替代 QueryContractPack/SchoolViewPack | D-07/D-08 继续由上游负责；独立笔记不被这些阻断，真实排盘上下文到 Tooltip 的关系验收必须等待必要查询契约 |

### 2.1 精确选区提案

`selector.ranges[]` 每段含 `block_id`, `artifact_revision_id`, `text_hash`, `start`, `end`；按原书阅读顺序排列，单段 `[start,end)`，计数单位固定候选 `unicode_code_point`。不得跨 Edition 或混用不兼容 Release。连续选区跨块时，中间完整块不能省略；如何表达段间分隔符由阅读结构契约明确，不能在客户端拼换行后重新计数。

每段 hash 建议为冻结 `text` 的 UTF-8 字节 SHA-256；不加 BOM、不自行去标点、繁简转换或做 Unicode 规范化。Python/Dart 对正文与范围须有同一组期望值测试。emoji/补充平面字符和组合字符均须覆盖；显示字形与 code point 计数不是同一概念。

`exact/prefix/suffix` 可随段保存以核验和展示，不能取代身份和范围。语义 SourceSpan 与这些范围建立多对多关联；没有 SourceSpan 不等于没有可注解原文。D-06 未冻结前只作为候选 Schema，不接受客户端随意 target_type。

### 2.2 来源能力与发布政策

源内容档位沿用现有 `full_scan / derived_page_images_only / reference_and_hash_only` 语义映射，不在此静默增加正式枚举。对原生电子书如何命名完整原件档位由上游共同冻结；不能为了兼容字段把 EPUB 虚称扫描件。

`original_view` 只在对应原件可授权获取时 available；派生页图另声明 `derived_view`，不能将缩略图冒充原件。`text_read/text_select/source_locate` 分别由对应正文和映射证据决定。登记引用可成功，但若某消费场景要求的能力缺失，则该场景验收不通过。

原生来源正式发布门槛属于架构政策修订，不能仅通过新增一个 capability 绕过。后端只接收符合当时有效发布政策的包；旧政策未修订前，相关原生来源样例仅作隔离开发验证。

### 2.3 三类哈希与版本

候选统一语义：`schema_version` 指所属上游包/记录 Schema，`delivery_schema_version` 指消费装载布局版本，两者分别标明注册项；不因数值相同视作同一版本。

- 文件 `sha256`：交付文件的实际字节，清单逐文件登记。
- `manifest_hash`：最终 manifest 文件实际字节 SHA-256，放在外层交付描述/导入请求，不让 manifest 包含自己的 hash 造成自引用。
- `canonical_hash`：上游 CanonicalSnapshot 的语义摘要；规范化/排序/排除字段及算法由上游给出，不能以任意 JSON 序列化重算替代。

同一 release_id 仅接受约定的不可变交付描述；相同 hash 重试复用，异 hash 拒绝。若上游需要一个 Release 对应多个装载变体，应增加明确 delivery 身份和依赖规则后共同冻结，不通过覆盖原清单支持。

## 3. 主 Agent 核验的原始证据

- `openspec/learn-system-blackbox-architecture.md:504,564,574,666` 确实要求 glyphbox_level/OcrPage；上游指出的政策冲突成立，本轮未修改这份权威文件。
- `pipeline/tools/ingest_epub.py:32` 读取 spine，`:51` 去标签/空格，`:69` 跳过部分文件，`:96` 重新合并换行；输出不能直接充当无损原文选区映射。
- `pipeline/tools/assemble_units.py:118,146,164` 根据排序后的已被主张引用 span 重编号；既不能代表完整阅读正文，也不能保证新增 span 后旧 unit ID 仍指原文。
- `openspec/legacy-storage-transition.md` 仍为 NOT_STARTED，相关旧语料为 ACTIVE_LEGACY 等；不把回执或本轮草案修订视为已迁移。

## 4. 下一次双方共同冻结的交付物

1. **政策差异稿**：按扫描/文本 PDF/EPUB/TXT 给出来源证据要求，列权威规格修改点和统一验证规则；包含原件档位与能力映射。
2. **机器 Schema 与文件映射表**：Work/Edition/Source/Asset、ReadingUnit/TextBlock/Page、目录/资源、SourceMapping、SourceSpan/Anchor、知识关系、迁移及 manifest；列 ID 来源、类型、可空性、必填条件、子包归属。
3. **D-06 选区与迁移规范**：有序跨块 ranges、Unicode/hash 规则、无语义 Span 正文锚点、精确修订查询、拆合歧义处理。
4. **真实最小样例组**：各声称支持格式的原件/派生材料/映射；初版、校订版、拆分版；重复句、跨块、脚注/图片、生僻字和组合字符。可先开发样例，不假冒 PUBLIC_RELEASE。
5. **消费端上传/入库契约**：缺失对象登记、受控上传、完成校验、分批装载、验证报告、原子激活和失败恢复；对象存储传输分片不改变逻辑 TextBlock 或选区。

消费端负责第 5 项的具体 API 草案及 Firestore 映射；上游负责第 1～4 项的生产模型与导出证据，涉及共同字段的部分双方核对。D-07/D-08 按真实知识/流派联动需要并行完成，不让阅读协议替它们宣称全覆盖。

本文件可由用户转交上游 Agent；没有自动发送消息。下一次回执请引用本节交付物与实际文件，避免只回复“方向同意”。冻结设计的标准是规则与 Schema 一致且可验证；生产上线另需真实导入、恢复、定位和权限验收。
