# 原版影印、PDF、EPUB、TXT：服务端直接入库交付契约

状态：`DRAFT_FOR_CROSS_AGENT_REVIEW`；2026-09-10。

本文件是 `SERVER_DATA_CONTRACT_DRAFT.md` 的资产补充协议。用户明确要求原件、电子书及阅读数据的格式在生成前对齐，避免到 APP 服务端再写格式转换或重新处理。本轮不评估版权；已有权利元数据可原样携带，不以新增版权讨论阻断本次契约协调。

## 1. 双方应确认的目标

**上游按共同交付 Schema 生成一次，服务端验证并直接装载。**

- 上游负责原件登记、OCR/文本提取、解码、目录解析、阅读块生成、来源映射与版本迁移。
- 服务端负责上传登记、完整性检查、原样对象存储、按共同结构入库、激活版本和查询分发。
- 服务端不再做 OCR、EPUB 拆章、TXT 重新编码、文本重新切句、临时分页或身份重编号。
- 通用传输适配仍存在：JSON 到 Firestore 类型、时间戳编码、对象上传和分页响应属于入库机械操作；目标是消除每本书/每种格式专有的语义转换，不承诺零适配代码。
- 若当前上游产物不满足阅读消费需要，在上游发布步骤补齐一次，不能客户端与服务端各自补做一遍。

## 2. 服务端存在哪里

沿用现有 Firebase/Google Cloud Storage 对象存储基础设施保存文件字节，Firestore 保存可查询元数据与关系。桶名由部署配置注入；上游清单使用相对路径和对象哈希，不写死测试/生产桶名、机器绝对路径或临时下载链接。

| 数据 | 对象存储 | Firestore / 查询投影 |
|---|---|---|
| 收集到的原始 PDF、影印图片、EPUB、TXT | 保留原始字节，按 SHA-256 标识不可变对象 | SourceAsset 身份、版本归属、文件类型、大小、哈希、存储引用 |
| 上游生成的扫描页图、缩略图 | 独立派生对象；保留来源与变换记录 | page_id、原书页序/页标、尺寸、旋转、资源引用 |
| EPUB 内图片等阅读资源 | 上游一次提取并登记为对象（本期阅读所需的资源） | 原 EPUB 内路径到 asset_id 的映射 |
| 可选择、可注解的正文 | 原件另存；标准化阅读文本按共同结构随包交付 | 阅读单元、TextBlock、顺序、修订、正文及哈希；大块使用同 Schema 的分片引用 |
| 目录与原文位置映射 | 版本化清单/JSONL 原样留档 | 分页查询的目录与锚点映射投影 |
| 原始 OCR 中间数据 | 保留在上游；仅交付阅读或证据定位需要的部分 | 不把模型中间产物作为客户端书籍正文 |

候选对象键：`library/objects/sha256/<前2位>/<64位sha256>`；包清单可位于 `library/releases/<release_id>/<manifest_hash>/manifest.json`。同字节可物理复用，同名不同字节不能覆盖；业务 SourceAsset 身份不因去重而合并。最终键规范由双方冻结。

候选集合为 `library_releases`、`library_works`、`library_editions`、`library_asset_revisions`、`library_reading_units`、`library_text_blocks`、`library_source_mappings`。业务 ID 与 release/revision 均保留；投影键必须区分版本，不能用 entity_id 单独覆盖旧版。共同的记录分片上限由 A-04 确认，在生成端执行，服务端不临时重分块。

现有 `functions-py/xuan/handlers/media.py` 处理的是 `playground_media/{userId}/{uploadSessionId}/...`，并有用户媒体孤儿清理逻辑。复用其存储 SDK、配置和部署方式；书籍资产使用独立路径、登记与保留规则，不能直接混入帖子附件集合或套用孤儿清理条件。

## 3. 每种输入需要交付什么

| 输入格式 | 必交原件 | 上游同时交付的阅读材料 | 定位规则 |
|---|---|---|---|
| 影印图片集 | 原始图片逐文件保留 | 页序清单、阅读用页图、OCR/校订后 TextBlock、字/行到页图映射 | page_id 为稳定页身份；文件名、显示页码不是身份 |
| 扫描 PDF | 原 PDF | PDF 页序清单、阅读用页图、OCR/校订正文与坐标映射 | PDF 页索引、原书印刷页标分开；PDF 页到派生图变换明确 |
| 带文本 PDF | 原 PDF | 提取/校订正文、阅读顺序、正文到原 PDF 位置映射；需要原图浏览时交付页图 | 提取顺序/连字等处理由上游冻结，不由客户端猜 |
| EPUB | 原 `.epub` | 目录、明确阅读顺序、TextBlock、所需图片等资源、原 EPUB 内位置到 block/range 映射 | 保存内部资源路径与元素/文本位置；不使用随字号变化的屏幕页数 |
| TXT / text | 原文件原始字节 | 编码信息、可阅读 Unicode 文本、目录或有序阅读块、原始位置到规范文本映射 | 原始字节偏移与规范正文字符偏移分开；无目录时不虚构章名 |

EPUB 的逐字内容、图片说明、脚注等转换覆盖范围由 A-03 确认；本期统一阅读视图不宣称完整复刻 EPUB 的样式和交互。若要按原 EPUB 排版直接阅读，可保留原件入口并后续选择阅读器，但不能因此省略统一注解定位所需的正文与映射。

只有原图没有 OCR/校订文本时，可具备原件浏览能力，但不满足本期“选择原句并注解”的完整交付。清单显式声明 `capabilities`：`original_view`, `text_read`, `text_select`, `source_locate`，各取 `available / unavailable` 并给缺失原因；不能由文件扩展名推断能力。资产登记可成功，缺能力的原句注解验收仍为阻断。

## 4. 统一交付包与记录

这是 PublicationPackage 的消费交付布局提案，不新增与之竞争的发布包。下列文件应由既有 SourceAssetPack / EvidenceMapPack / KnowledgeDataPack 等承接；最终承载点需上游回执。

```text
<release-package>/
  manifest.json
  records/
    works.jsonl
    editions.jsonl
    asset_revisions.jsonl
    reading_units.jsonl
    text_blocks.jsonl
    source_mappings.jsonl
    knowledge_source_links.jsonl
    identity_migrations.jsonl
  objects/sha256/<前2位>/<完整sha256>
```

- 清单至少包含 `delivery_schema_version`, `release_id`, `canonical_hash`, `files[]`、对象及记录数量、能力声明；每个文件记录 `relative_path`, `media_type`, `size_bytes`, `sha256`, `record_kind?`, `record_count?`。
- JSONL 为候选统一装载格式，UTF-8，一行一个对象；上游若已有等效正式格式，应在 A-04 提出共同采用，避免额外转换链。此处尚非批准上游整体改格式。
- 清单内对象采用 `packaged`（提供包内相对路径）或 `already_stored`（提供可核验既存对象引用）两种交付方式；仅给第三方网站链接不是已存储原件。需要下载的来源由上游采集步骤处理并留 provenance。
- 所有清单路径必须在包内、无父目录逃逸；对象引用必须与实际字节哈希相符。文件已上传但未登记、记录已导入但对象未就绪，都不能激活 Release。

### 4.1 AssetRevision 最小字段提案

| 字段 | 要求 |
|---|---|
| `asset_id`, `artifact_revision_id`, `release_id`, `edition_id` | 业务身份、不可变修订及归属；具体命名与上游既有字段统一 |
| `role` | `original / page_image / thumbnail / embedded_resource / reading_text` |
| `media_type`, `size_bytes`, `sha256` | 对实际存储字节计算；`size_bytes` 非负整数 |
| `original_filename` | 可读名称，不参与身份或排序 |
| `object_ref` | packaged 相对路径或 already_stored 逻辑对象引用，不存过期签名 URL |
| `derived_from[]`, `transform_ref?` | 派生对象指向精确来源修订与变换记录；原件为空数组 |
| `provenance` | 来源类别、取得时间、可选原 URL/来源说明；来源 URL 不是下载时的唯一依赖 |
| `format_metadata` | PDF 页数；图片宽高/方向；TXT 编码；EPUB 阅读顺序清单引用等按格式定义 |

### 4.2 Page 与 SourceMapping 最小字段提案

`Page`：`page_id`, `edition_id`, `source_asset_revision_id`, `page_index`（建议从 0 起，待统一）、`page_label?`, `image_asset_ref?`, `width?`, `height?`, `rotation?`, `reading_order`。

`SourceMapping`：`mapping_id`, `release_id`, `text_block_id`, `text_revision_id`, `text_range`, `source_asset_revision_id`, `locator_type`, `locator`。`text_range` 与主草案 §5 共用字符计数和规范化规则。

- 图像/PDF locator：页身份、PDF 页索引（若适用）、矩形/多边形或字框范围、坐标单位、尺寸与变换引用。
- EPUB locator：内部文档路径、稳定元素定位/文本范围；如上游已有 CFI 可一并交付，但须明确对应的精确 EPUB 修订。
- TXT locator：原编码、原字节范围或版本固定的文本范围，以及到标准阅读文本的映射。
- 同一原文范围允许多个来源片段，一个阅读块允许多条映射；不能强制一块只对应一页。

## 5. 上传与分发链路

1. 上游完成共享 Schema 校验，交付清单及就绪对象。
2. Python 服务登记导入，按哈希确认哪些对象已有；为缺失对象使用既有存储能力安排上传，具体上传会话协议由 A-05 冻结。
3. 大文件字节走对象存储上传通道，REST 接收清单、状态和完成确认；不把 PDF/EPUB Base64 塞进 Firestore，也不要求整个大包经过一次 Functions 请求。
4. 验证上传完成、哈希/大小、全部引用、阅读顺序、映射和声明能力，分批机械入库；重复请求不重复建版本。
5. 全部通过后切换 active Release；失败保留旧版并报告精确文件/记录错误。历史引用存在期间保留对象；清理需做引用检查，不能按上传时间直接删除。
6. 客户端通过 REST 获取固定版本的元数据与资源描述，通过存储下载通道读取文件；资源描述返回 `asset_id`, `artifact_revision_id`, `sha256`, `size_bytes`, `media_type`, `download_url`, `expires_at?`, `range_supported`。URL 只作临时传输地址，锚点永远引用逻辑身份。
7. PDF/EPUB 的按需/续传下载能力需由实际存储通道验证后声明；Drift 存目录、版本、块与缓存索引，设备文件目录存 PDF/EPUB/页图字节。缓存删除不删除用户注解。

## 6. 交付准入与上游回执

| 编号 | 上游需明确回复 | 完成证据 |
|---|---|---|
| A-01 | 原件是否逐字节保留；SourceAsset/Edition/Revision 如何归属 | 真实影印/PDF/EPUB/TXT 样例和原件哈希 |
| A-02 | 影印/PDF 页序、页图、OCR 正文和坐标由哪个步骤产出 | 能从任一已声明可定位选区打开准确页/区域 |
| A-03 | EPUB/TXT 的读取顺序、解码、正文、脚注/图片及映射格式 | EPUB 内重复句、TXT 换行/生僻字等实际样例，不只提供原始文件 |
| A-04 | 共同 Schema、交付布局、记录分片上限及所属子包 | 上游输出无需重新拆章、重编码或改 ID 即可通过消费校验 |
| A-05 | 上传通道、环境无关对象引用、已有对象复用及失败重试 | 中断上传再续传/重试，无半就绪 Release 暴露 |
| A-06 | 资源下载、历史对象保留与坐标/版本一致性 | 重发包不重复字节、改版不覆盖旧件，锚点仍返回当时版本 |

对每项回复 `ACCEPT / CHANGE / UNAVAILABLE`，附生成代码/Schema/真实样例路径。可写入主草案约定的 `UPSTREAM_DATA_CONTRACT_REPLY.md`，分别保留 U 系列和 A 系列回执。

**完成标准：每一种声称支持的输入，都能从上游输出直接装载、下载原件、显示有序正文并保存准确选区，服务端和客户端均未执行第二次内容加工。** 缺少某种输入样例时仅声明该格式未验收，不阻断其他格式单独完成，也不声称全格式已通。

下一步由用户把本文件与主草案一起交给数据生成 Agent。双方先冻结共同输出格式，再安排上游生成与下游装载代码；本文件不代表已经联系对方、完成桶部署或迁移旧资料。
