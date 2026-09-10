# Learn System 上游契约核对回执

状态：`REVIEW_REPLY_FOR_COORDINATION`；仅审查与建议，不代表共同 Schema 已冻结或生产交付已通过。
审查日期：2026-09-09（环境日期；被审草案标注 2026-09-10）。
对象：`SERVER_DATA_CONTRACT_DRAFT.md`、`BOOK_ASSET_DELIVERY_CONTRACT_DRAFT.md`。

## 1. 结论与边界

总体架构兼容，现有数据不能直接作为生产交付包。稳定业务身份与修订分离、知识只读投影、UGC 独立存储、同版查询、失败不切换已激活版本等方向一致。缺口主要在阅读数据契约、选区与迁移、各格式证据链及正式发布编译器。

本次核对了本仓库实际代码、Schema 和样例。未部署或测试 APP 后端、Firestore、上传/下载通道；两份消费草案引用的外部服务能力不能由本回执确认。

`ACCEPT` 表示接受设计方向；`CHANGE` 表示共同契约需修改或补齐；`UNAVAILABLE` 表示当前无可交付实现或验证证据。接受设计不等于功能已经实现。

Learn System 仍是单人单机编译工具。APP 登录、权限、UGC 和通知属于消费端；SERVER §10 关于线上 UI 范围的说明仅适用于社区线，不应覆盖黑箱的单机边界。黑箱内部各步数据持续保留；生产包只携带已批准的阅读/知识数据、必要证据和血缘引用，不把模型候选或私有运行日志全部下发。

## 2. 必须先沟通的差异

| 事项 | 当前差异及证据 | 建议与负责方 |
|---|---|---|
| 纯电子书能否生产发布 | 架构 §11（503–504 行）、§13（564 行）要求 PUBLIC_RELEASE 一律 glyphbox_level；§16（660–667 行）固定经过 OcrPage。消费稿支持 EPUB/TXT 的原生定位 | 联合决定按来源类型分支：扫描走页图/字框；EPUB 走精确文件修订+内部资源/文本范围；TXT 走原始字节与阅读文本映射。保留完整性与人工审核门禁。此建议尚未改写既有发布政策 |
| 原件交付档位 | 资产稿 §3 必交原件；上游 §16 允许仅派生页图或 reference_and_hash_only | 分开 source_content_level 与 packaged/already_stored 传输方式。面向生产声称 original_view 的原件必须已交付或在后端核验可取；本机绝对路径不满足线上解析。缺原件应明确能力缺失，不静默放行。本次不重新评估版权 |
| 阅读全文与知识片段 | SERVER §4 提出 ReadingUnit/TextBlock；现上游主要是结构段、语义段、SourceSpan | M2/M3 保存完整阅读正文和来源映射，M8 输出阅读投影；不能只导出抽出知识的句子。ReadingUnit 与 EditionPart 分开，TextBlock 与 SourceSpan 建多对多范围映射 |
| 任意选区与修订 | SERVER §5 的单个 text_block_id 无法表达跨块选区；D-06 未完成 | 联合冻结有序多段 selector、计数单位、text_hash、精确修订与拆合迁移。阅读块没有知识 SourceSpan 时也必须可注解；补合法目标/完整结构锚点，不能伪造语义 SourceSpan |
| 实际文件与 Schema | 当前机器 Schema 是四份 L0 信封，尚无完整书籍交付记录 Schema；资产稿定义 Page 但 §4 布局未列其文件 | 明确 pages.jsonl 或等价承载点，并登记 SourceSpan/SourceAnchor/知识对象、迁移记录、目录及资源映射文件与必填性。A 稿可以是子包视图，但不得被当作缺失知识对象的完整 PublicationPackage |
| 排盘和流派消费 | 两份稿重点为阅读/社区；KnowledgeReference 不能替代规则与查询契约 | D-07 的 FactSet/Profile/规则 AST/查询协议及 D-08 流派视图仍需交付。由上游定义、生产端映射；阅读协议不等于全部排盘需求已覆盖 |

## 3. U 系列回执

| 编号 | 回执 | 当前证据、缺口与具体答复 |
|---|---|---|
| U-01 | CHANGE | `pipeline/registry/works/qiongtong_baojian.yaml` 已有字符串 `work_id=work_qtbj`；corpus manifest 有字符串 `source_id=src_qtbj_ed01`，未形成独立 Edition/Asset 的共同机器契约。保留已有值，补显式映射；不得将 Source 与 Edition 或文件资产默认视为同一个对象 |
| U-02 | CHANGE | 架构 §3 定义加工 Part；`pipeline/corpus/bazi/qtbj_ed01/source/sections.yaml` 是标题结构样本。尚无 ReadingUnit/TextBlock 发布模型。补父子结构、有序关系和覆盖范围，不把伪页当扫描页 |
| U-03 | CHANGE | 架构 §8.1 已确定 entity_id + artifact_revision_id 双锚；D-06 仍未冻结。目标类型、稳定性和精确修订查询必须补齐，现有 L0 ArtifactRef 不能直接充当实体选区 DTO |
| U-04 | CHANGE | 接受 `[start,end)`；建议计 Unicode code point，text_hash 对冻结 text 的 UTF-8 字节做 SHA-256。传输与显示不得再次繁简转换/去标点/规范化；任何清洗前后保留映射。`pipeline/tools/ingest_epub.py:51–54,96–100` 会去空格、重组换行，目前无映射，不可直接复用其偏移。具体规则及 Python/Dart 一致用例需联合冻结 |
| U-05 | CHANGE | 建议 selector 含有序 ranges，每段绑定 block_id、精确修订、text_hash 与区间；重复句靠身份+位置区分。跨块、跨 Span、空白/非知识正文和拆分后歧义均需定义；不得按引文找第一个命中 |
| U-06 | CHANGE | 接受显式知识→Assertion→EvidenceLink→SourceSpan 关系；不同 Edition 同文不自动合并讨论。同实体跨修订可归同主题，但评论保留 observed revision；拆合后的讨论关联需显式规则。D-07/D-08 补查询与流派关系，不能由标题猜关联 |
| U-07 | CHANGE | §8.1 已要求合并/拆分新 ID、旧 ID 退役，但无范围迁移表实现。需 from/to release、精确修订、关系类型、范围映射、歧义原因；不能只给新旧 ID 名单。保存原始 AnchorRef，解析结果另存 |
| U-08 | CHANGE | 接受幂等导入和隔离激活方向；需统一 schema_version/delivery_schema_version、文件 hash/manifest_hash/canonical_hash 的不同含义与计算规则，固定发布范围和依赖包。生产必须检验 PUBLIC_RELEASE 与完整报告；本地路径或临时 URL 不作为持久对象身份 |
| U-09 | UNAVAILABLE | 有开发语料和 L0 示例，无通过两份消费契约的真实 PublicationPackage、修订/拆分前后包及联合导入记录。`openspec/schemas/examples/qtbj_ed01.m1.stage_package.valid.yaml` 仅为 M1 信封示例，不能冒充生产发布包；不承诺未验证的交付日期 |

当前可冻结复用的 ID：`art_<32hex>`、`rev_<32hex>`、`rel_<32hex>` 及既有 Source/SourceSpan 等格式见架构 §8.1。字段必填性仅能以已有 L0 Schema 为准；上述书籍消费字段的类型全集、空值和必填条件尚未冻结，不宣称已有完整生成代码。

## 4. A 系列回执

旧 ID 生成风险已核对：`pipeline/tools/assemble_units.py:118,146–147,164–167` 按排序后的 span 重新枚举 `ku_bazi_*`；插入新 span 可能使同一个 unit ID 指向不同原文。该路径仅适用于旧数据，进入生产前必须稳定分配身份并登记迁移，不可只给旧 ID 加 release 字段后直接上线。

| 编号 | 回执 | 当前证据、缺口与具体答复 |
|---|---|---|
| A-01 | CHANGE | 原始字节保留符合上游目标；现有 `pipeline/corpus/bazi/qtbj_ed01/manifest.yaml` 登记 EPUB 原件与转录哈希。旧存储仍标 NOT_STARTED/ACTIVE_LEGACY，未迁入统一 Ledger。交付按第 2 节区分档位；尚无全格式资产修订样例 |
| A-02 | ACCEPT | 职责接受：M1 登记源、M2 页图/校订/字框、M3 正文范围映射、M8 打包。现有 `ocr/src/gujiorc/core/models.py` 和页面 JSON 可复用；`core/export.py:148–192` 仅导出 transcript+manifest，未导出完整页身份/变换/选区映射。可直接装载的交付目前 UNAVAILABLE |
| A-03 | CHANGE | `pipeline/tools/ingest_epub.py:32–44` 使用 spine 顺序，69–100 转为标题伪页和文本；未保存原 EPUB 元素/范围映射及阅读图片/脚注关系。先冻结覆盖清单及不可省略内容，不能通过丢弃脚注、空格或资源来伪称完整支持。TXT/带文本 PDF 完整交付样例未验收 |
| A-04 | CHANGE | 接受在 M8 输出 UTF-8 JSONL 的候选方案，作为已有子包的装载投影。共同 Schema/文件归属、Page 记录、引用闭合、分片上限仍需确定。区分传输分片与逻辑 TextBlock；分片不能悄悄换 block_id 或改变选区坐标 |
| A-05 | UNAVAILABLE | 本次未见可验证的生产上传联调证据。建议生产端复用对象存储提供缺失对象上传/完成确认协议；上游只交付清单和对象，通过薄适配上传。对象完成与哈希核验前不得激活；需要中断恢复与幂等实测 |
| A-06 | ACCEPT | 接受旧修订可回看、按 hash 去重、临时下载地址与逻辑身份分离。实现实证 UNAVAILABLE。生产端负责下载/访问/保留执行，上游提供精确版本和派生变换；需旧注解跨版本回看与对象缺失的联合用例 |

## 5. 最少代码接法与共同验收

建议复用现有 OCR 和解析器，将需要的字段、映射补到现有导出/发布步骤。M8 从同一 CanonicalSnapshot 生成 JSONL 装载投影、SQLite 查询投影和 Graph 投影，携带相同身份/版本；JSONL 不取代内部所有存储格式。Firestore 只做机械映射、校验、索引和激活，避免各端重新解码、切句或创建另一套书目。

共同验收按格式和功能声明执行；某种格式未验证就声明未支持，不能把开发数据升格为生产数据：

1. 真实小样本同时含重复句、跨块选择、生僻字/补充平面字符；Python 与 Dart 对同一范围和哈希一致。
2. 扫描选区回到精确页和区域；EPUB/TXT 回到各自固定原件范围，无伪造字框。
3. 一个知识对象经明确关系返回来源，同时从阅读入口找到同一公开讨论；流派不同不被错误合并。
4. 初版、校订版和拆分版保留历史；旧注解显示当时正文，歧义进入待处理。
5. 篡改 hash、漏文件、悬空引用、candidate/dev 包、缺必要能力都应被拒绝；导入失败保持旧 active 版本。
6. 重试上传/入库不会重复建发布，旧对象不被覆盖；大记录的传输分片不改变逻辑选区。

下一步：双方先处理第 2 节决策并完成 D-06/D-07 与阅读交付字段映射，再冻结一个共同 Schema 和真实联调样例。通过联调与生产门禁后才向用户开放；模型置信度、Schema 单测或演示可运行均不等于生产验收。

本回执未修改原两份草案或现行发布政策，未联系外部工程师，未执行业务实现。
