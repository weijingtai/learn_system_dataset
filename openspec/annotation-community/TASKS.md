# 笔记、原句注解与讨论 Tasks

版本：1.0；2026-09-10。状态：`PLANNED_NOT_DISPATCHED`。
权威需求：[PRD](PRD.md)，技术依据：[Design](DESIGN.md)，根路径与执行门禁：[Plans](PLANS.md)。下面路径使用 Plans §1 的精确根路径标记；标为“新增”的路径是任务产物，不声称当前文件存在。

所有条目初始未完成。`BACKLOG` 表示可按依赖准备六件套；`BLOCKED` 表示有明确外部契约缺口。**本文件没有 READY 任务，不能凭自然语言直接派发业务编码。** 一项涉及多仓库时，六件套须拆为有序 ACT，分别限定写入所有权；其他 Agent 的改动不得回退。

## 1. 总表与需求追踪

| 任务 | 范围 | 依赖 | 初始状态 | PRD |
|---|---|---|---|---|
| NC-001 | 客户端位置、宿主与端口装配基线 | 无 | BACKLOG | R-18 |
| NC-002 | 非书籍模型、状态、限额与 fixture | NC-001 | BACKLOG | R-01/04/05/18/20 |
| NC-003 | 公共 REST/OpenAPI/Swagger 契约 | NC-002 | BACKLOG | R-18/20 |
| NC-004 | Drift 修订与可靠保存 | NC-002 | BACKLOG | R-02/04/16 |
| NC-005 | Markdown 编辑预览与状态 | NC-004 | BACKLOG | R-01/02/16 |
| NC-006 | Undo/Redo 与 IME/焦点 | NC-005 | BACKLOG | R-03 |
| NC-007 | 历史、差异、恢复与冲突 | NC-004/005 | BACKLOG | R-04/12 |
| NC-008 | 本地图片与公共资源适配 | NC-003/004 | BACKLOG | R-15/20 |
| NC-009 | 发布/更新/收回与权限事务 | NC-003/008 | BACKLOG | R-05/20 |
| NC-010 | 笔记列表、公开详情与发布 UI | NC-005/007/009 | BACKLOG | R-01/05/16 |
| NC-011 | 两级评论/回复与编辑删除 | NC-003/009 | BACKLOG | R-08/20 |
| NC-012 | 赞踩/收藏/分享/@/关系与举报 | NC-003/009/011 | BACKLOG | R-09/10/20 |
| NC-013 | 事务事件、投递与通知接口 | NC-003/011/012 | BACKLOG | R-11/20 |
| NC-014 | Notification 宿主适配与导航 | NC-010/013 | BACKLOG | R-11/16 |
| NC-015 | 密钥恢复、授权与删除窗口协议 | NC-001 | BACKLOG | R-12/13/14/20 |
| NC-016 | 私人加密 mapper 与设备同步 | NC-004/015 | BLOCKED | R-12/20 |
| NC-017 | 生产密文网关与备份清单 | NC-003/015 | BLOCKED | R-13/20 |
| NC-018 | 备份设置、进度与恢复 | NC-008/016/017 | BLOCKED | R-12/13 |
| NC-019 | 回收站、恢复、永久清理 | NC-007/009/018 | BLOCKED | R-14/20 |
| NC-020 | 上游书籍政策/Schema/D-06/样例 | 既有上游交付 | BLOCKED | R-06/07/17 |
| NC-021 | 书籍上传、导入、激活与查询 | NC-003/020 | BLOCKED | R-17/20 |
| NC-022 | 阅读、原句注解与锚点解析 | NC-004/020/021 | BLOCKED | R-06/07/17 |
| NC-023 | 真实 Tooltip 原型与入口一致性 | NC-010/012/014/022 | BLOCKED | R-07/19 |
| NC-024 | 跨模块真实验收与交接 | NC-006/007/008/010/011/012/014/016/018/019/021/022/023 | BLOCKED | R-01～R-20 |

NC-019 可先准备本地回收站子 ACT，但完整清理验收等待备份协议；NC-020 的协调文档可现在准备，不能越过上游政策冻结。状态解锁须记录证据，不只删除 BLOCKED 字样。

## 2. 前置契约

### NC-001：实际工程位置与装配基线

- [ ] 读取现有 SOCIAL/STORAGE/REST/NOTIFICATION 及候选 CLIENT 的 AGENTS、pubspec、导出与真实调用；确认是否已有可复用学习包。当前相邻 learn_system 不是 Flutter 包。
- [ ] 新增 `SPEC/INTEGRATION_BASELINE.md`，冻结 CLIENT 实际根、包名、Flutter/Dart 版本、各依赖精确范围、宿主初始化/账号/HTTP/存储/IM 导航注入点、各仓库基线提交。若改变拟建目录，回写所有任务路径。
- [ ] 验收：每个端口列真实文件/符号和“已有实现/新增适配”，不把 mock 或内存降级当生产；目录/版本未唯一确定则本任务不通过。

### NC-002：模型与固定行为契约

- [ ] 新增 `SPEC/contracts/community-models.md`、`SPEC/fixtures/community/`，覆盖 Note/Revision/Publication/Comment/Reaction/状态机、编码与 hash、工程限额；不冻结书籍选择器或密码字段。
- [ ] Fixture 至少含私改未发布、恢复同文新修订、两个并发 parent、跨楼非法 reply、超限内容和无效 mention；写清完整期望记录/错误而非“验证失败即可”。
- [ ] 验收：每个 DTO 与私人/公共字段归属唯一；私人 parent 链和正文不进入公共查询；PRD 已确认默认值无矛盾。为后续正反 Schema 测试提供固定字节输入。

### NC-003：公共 API 与 Swagger

- [ ] 修改 `REST/openapi/openapi.yaml`，新增社区公共资源/命令/错误/分页/ETag/幂等；请求头使用合法 header parameters。密码学/书籍扩展在 NC-017/021 合并至同一入口，不伪造已冻结字段。
- [ ] 新增 `REST/test/community_openapi_contract_test.dart` 与 `REST/tool/validate_openapi`（验证入口），固定真正 OpenAPI 验证器版本及离线失败规则；Swagger UI 读取同一契约。
- [ ] Red fixture 包含 operation.headers、缺必填、非法状态、同键异载荷及 412；Green 用真实解析器验证。运行 `dart test test/community_openapi_contract_test.dart` 与 `tool/validate_openapi openapi/openapi.yaml`，均退出 0；该脚本需本任务实际创建，不能假称现已可运行。

## 3. 独立本地笔记

### NC-004：可靠保存与不可变修订

- [ ] 在 NC-001 冻结的 CLIENT 位置建立或扩展 `pubspec.yaml`、`lib/reading_notes.dart`、`analysis_options.yaml`，依赖严格采用 NC-001 固定版本；登记 Drift 生成文件与 schema migration 步骤，运行必要生成命令后才能运行测试。
- [ ] 新增 `CLIENT/lib/src/domain/note.dart`、`note_revision.dart`、`persistence/note_database.dart`、`note_repository.dart`；在 `test/persistence/note_repository_test.dart` 建失败用例后实现事务保存与待同步记录。
- [ ] 覆盖首次/无变化保存、连续两版本、附件引用、磁盘失败回滚、文件库关闭重开、账号切换旧回调隔离；禁止照搬 notebook 覆盖 committed 或内存模式报成功。
- [ ] 运行 `flutter test test/persistence/note_repository_test.dart`；期望真文件重开后版本与引用不丢，失败不产生半个 head/outbox，不只测内存 Fake。

### NC-005：Markdown 编辑、预览和保存状态

- [ ] 新增 `CLIENT/lib/src/editor/note_editor_controller.dart`、`note_editor_page.dart`、`markdown_preview.dart`，及 `test/editor/note_editor_test.dart`；使用 Plus 渲染、现有文本输入与薄格式工具栏。
- [ ] 测试虚拟时间 2 秒去抖、失焦 flush、返回失败留页、相同内容去重、IME composing 未提交不建最终修订、无书籍也能编辑；UI 分开本地/设备/备份状态。
- [ ] 运行 `flutter test test/editor/note_editor_test.dart`；自动保存不改变已发布正文，未知云状态不显示成功；不添加本期以外快捷键。

### NC-006：撤销、重做与输入法

- [ ] 新增 `CLIENT/lib/src/editor/editor_history_adapter.dart`，修改 editor controller/page 的局部命令接线；新增 `test/editor/editor_history_test.dart` 与 `test/editor/editor_shortcuts_test.dart`。
- [ ] 用同一输入序列分别调用按钮/快捷键：Windows/Linux Ctrl+Z、Ctrl+Shift+Z、Ctrl+Y；macOS ⌘Z、⌘⇧Z；移动按钮。检验正文、光标、图片/@ 引用和 canUndo/canRedo 一致，不同时调用平台及自有栈造成双撤销。
- [ ] 覆盖连续输入归组、中文 composition 一次撤销、粘贴/格式/图片操作边界、自动保存后 Undo、Undo 后新输入清 redo、焦点在其他控件不响应、重开栈清空但修订仍在。
- [ ] 运行 `flutter test test/editor/editor_history_test.dart test/editor/editor_shortcuts_test.dart`；禁止把“取消发布”塞入 Undo；禁止实现 F-01 的其他快捷键。

### NC-007：历史差异与多分支恢复

- [ ] 新增 `CLIENT/lib/src/history/revision_history_page.dart`、`revision_compare.dart`、`revision_conflict_controller.dart` 及 `test/history/revision_history_test.dart`。
- [ ] 验收编辑会话归组但能查看每次修订；恢复旧版新建 ID/restored_from，不覆盖历史；选择任一冲突分支或手动合并生成含父链的新版本，旧分支仍可查。
- [ ] 运行 `flutter test test/history/revision_history_test.dart`；比较私人内容不调用服务器明文 diff API。

## 4. 图片与公开社区

### NC-008：图片引用与访问边界

- [ ] 新增 `CLIENT/lib/src/media/note_attachment_repository.dart`、`markdown_image_resolver.dart`、`test/media/note_attachment_test.dart`；新增 `SERVER/xuan/handlers/community_media.py`、`tests/test_community_media.py`。
- [ ] 本地图片使用现有 cipher 端口注入并按 scope 读取；发布资源独立于私有对象。校验 20 张/10 MiB 限额、丢文件/上传中断、图片 Undo 不清历史引用、私密外部图片默认不请求。
- [ ] 验收公共图片每次访问当前 ACL；禁止永久公开 URL 或改变私人 Blob ACL。运行 `flutter test test/media/note_attachment_test.dart` 与 `python3 -m pytest tests/test_community_media.py -q`；真对象访问证据在 NC-024 补齐。

### NC-009：公共发布事务与权限

- [ ] 新增 `SERVER/xuan/community/content_service.py`、`xuan/handlers/community_contents.py`、`tests/test_community_publications.py`；修改 `xuan/config.py`、`main.py` 的必要注册，实际规则/索引路径先由 NC-001 登记。
- [ ] 实现选定快照发布、更新、收回、当前权限查询；公共指针/绑定/事件同事务。先测私改不公开、旧 ETag、同键重试/异载荷、他人操作拒绝、收回与写评论并发。
- [ ] 运行 `python3 -m pytest tests/test_community_publications.py -q`；原始 HTTP 测试证明 401/403或404/409/412 语义，直接服务函数成功不等于 REST 已通。

### NC-010：列表、详情与发布页面

- [ ] 新增 `CLIENT/lib/src/community/note_list_page.dart`、`content_detail_page.dart`、`publication_controller.dart`、`community_api.dart` 和 `test/community/publication_flow_test.dart`；在拟新建 `CLIENT/example/` 配置真实测试宿主。
- [ ] 验收本人草稿/有未发布修改/已公开状态、发布预览固定修订、图片未就绪拒绝发布、离线保留待发操作、版本冲突保留私人稿、服务器确认前不显示成功。
- [ ] 运行 `flutter test test/community/publication_flow_test.dart`；公共内容缓存重连失效，不承诺完整离线公共阅读。

### NC-011：两级评论、排序与修改历史

- [ ] 新增 `SERVER/xuan/community/discussion_service.py`、`xuan/handlers/community_comments.py`、`tests/test_community_comments.py`；新增 `CLIENT/lib/src/community/discussion_controller.dart`、`discussion_panel.dart`、`test/community/discussion_test.dart`。
- [ ] 复用 replies 的 depth/root 校验思路；新事务同时检查主题 ACL、root/target 与版本，写 comment/revision/outbox。一级可最新/最早，楼内正序，各层独立稳定游标。
- [ ] 测跨 thread/root 拒绝、回复楼内仍 depth1、删除 root 留墓碑/已有回复但禁止新回复、编辑不改 created_at、收回并发无漏写。
- [ ] 运行 `python3 -m pytest tests/test_community_comments.py -q`、`flutter test test/community/discussion_test.dart`。

### NC-012：互动、关系与结构化 mention

- [ ] 新增 `SERVER/xuan/handlers/community_interactions.py`、`tests/test_community_interactions.py`；新增 `CLIENT/lib/src/community/interaction_controller.dart`、`mention_adapter.dart`、`social_navigation_adapter.dart`、`test/community/interactions_test.dart`。
- [ ] 赞踩按最终值原子互斥/取消；收藏私有；分享解析检查当前权限。@ 复用候选查询但持久 user ID；编辑删除 mention 不误通知。资料/关注/私信/举报/拉黑调用已有能力，不添加排盘反馈。
- [ ] 测快速切换的乱序/重试、两账号计数、失权目标、空候选、名字重复但 ID 不同；实际宿主注入，不接受本地翻转/mock 关系。
- [ ] 运行 `python3 -m pytest tests/test_community_interactions.py -q`、`flutter test test/community/interactions_test.dart`。

## 5. 通知

### NC-013：业务投递与服务端通知契约

- [ ] 新增 `SERVER/xuan/community/notification_dispatch.py`、`xuan/handlers/community_deliveries.py`、`tests/test_community_deliveries.py`；扩展 NC-003 的同一 OpenAPI，接入既有 outbox 触发入口。
- [ ] `(event_id,recipient_id)` 原子建投递；推送重试状态与记录创建分离。评论/回复/@ 去重，无自通知；赞站内、偏好控制系统提醒，踩/收藏/分享不通知。
- [ ] 验收偏好/拉黑/失权过滤、双触发并发、创建成功推送失败后的重试、正文当前权限、游标补拉、ACK 与已读分离；明确 ReceiptRejected 的 HTTP 映射。
- [ ] 运行 `python3 -m pytest tests/test_community_deliveries.py -q`；旧查询查重+随机 ID 不作为并发幂等实现。

### NC-014：Notification 生产适配与回跳

- [ ] 新增 `CLIENT/lib/src/notifications/community_notification_adapters.dart`、`notification_target_router.dart`、`test/notifications/community_notifications_test.dart`；按 NOTIFICATION 接入指南列出全部适配端口的实际注入点。
- [ ] 使用同一持久接收管线处理实时/唤醒/补拉；落盘失败不 ACK、不推进 cursor；ReceiptRejected 整批终止并可观察，不任意重试 4xx。
- [ ] 验收通知打开 content/thread/root/comment 的精确目标、账号切换、删除/收回后不可用状态。运行 `flutter test test/notifications/community_notifications_test.dart`；真实设备推送在 NC-024 单独验证。

## 6. 私人同步、备份与删除

### NC-015：恢复、设备授权和清理协议设计

- [ ] 新增 `SPEC/PRIVATE_SYNC_PROTOCOL.md` 与正反协议样例；读 STORAGE 真实 cipher/pairing/guard/row 网关，选成熟密码学组件与可恢复封装，不自创算法。
- [ ] 明确密钥生成/保存/授权新设备/全旧设备丢失恢复/吊销/epoch/密码改变；认证绑定 scope、设备 ID、指纹、有效期。不得仅凭现有 guard 返回 authorized 放行。
- [ ] 明确恢复材料的用户保存流程、不可恢复失败行为、tombstone 保留与离线重入、备份开关/删除/清理窗口。以攻击/故障场景审查并经主 Agent 接受后解锁 NC-016～019；不能用一句“复用 E2EE”通过。

### NC-016：加密 mapper 与双设备同步

- [ ] 新增 `CLIENT/lib/src/storage/private_note_mapper.dart`、`private_note_sync.dart`、`test/storage/private_note_sync_test.dart`，在 STORAGE 必要导出点薄接线；私有/public 注册不同 entityType。
- [ ] 测实际序列化输出无标题/正文/引用/附件名明文；云/P2P 重复投递去重，双方分支保留；错误账号/指纹/过期/吊销在交换正文前拒绝。
- [ ] 运行 `flutter test test/storage/private_note_sync_test.dart`；另建 `CLIENT/example/integration_test/private_device_sync_test.dart`，在 NC-001 记录的两台真实设备验证 LAN 与 WebRTC，各自记录证据。

### NC-017：密文云网关与完整备份

- [ ] 新增 `SERVER/xuan/handlers/private_note_backups.py`、`tests/test_private_note_backups.py`；新增 `STORAGE/firebase/lib/media/private_backup_blob_gateway.dart`，补同源 OpenAPI 中密文上传/完成/下载/删除 Schema。
- [ ] 复用 bucket/Auth 基础，限定服务器推导 owner/path；密文对象全部存在/hash 匹配后原子激活完整 manifest。备份集合/路径/清理与 Playground 媒体及 relay 隔离。
- [ ] 运行 `python3 -m pytest tests/test_private_note_backups.py -q`；验收跨账号、路径篡改、部分上传、错 hash、重试幂等、清理失败可重试；真实上传/下载证据必须另外提供，内存 BlobGateway 不足。

### NC-018：备份 UI 与恢复验证

- [ ] 新增 `CLIENT/lib/src/storage/backup_controller.dart`、`backup_settings_page.dart`、`test/storage/backup_controller_test.dart`；新增 `CLIENT/example/integration_test/private_backup_restore_test.dart`。
- [ ] 验收首次选择/启用自动/关闭仅停新传/单独删除云备份，三个保存同步备份状态分开；跨版本修订与图片依赖恢复完整。
- [ ] 运行 `flutter test test/storage/backup_controller_test.dart`，并在真实测试环境分别演练原设备在场和全部原设备丢失；仅新生成密钥打不开旧数据的测试不能算恢复通过。

### NC-019：30 天回收站与永久清理

- [ ] 新增 `CLIENT/lib/src/history/note_trash_page.dart`、`test/history/note_trash_test.dart`；新增 `SERVER/xuan/community/purge_service.py`、`tests/test_community_purge.py`，接入已冻结删除事件/备份清理。
- [ ] 测 30 天边界（可注入时钟）、恢复保持私密、已公开离线删除显示待收回、共享附件仍被引用时不删、清理重试、旧离线设备不能复活已清理正文。
- [ ] 运行 `flutter test test/history/note_trash_test.dart` 与 `python3 -m pytest tests/test_community_purge.py -q`；只本地 deleted_at 成功不代表云端清理完成。

## 7. 书籍与真实 Tooltip

### NC-020：共同书籍契约协调

- [ ] 输入 `docs/annotation-community/UPSTREAM_DATA_CONTRACT_REPLY.md` 与 `CONSUMER_ALIGNMENT_RESPONSE.md`，由上游交付来源分型发布政策、共同 Schema/文件映射、D-06、多段选区/迁移和真实原件样例；消费端核对结果写入 `SPEC/BOOK_CONTRACT_ACCEPTANCE.md`。
- [ ] 抽查 EPUB 空格/脚注/图片与原件映射、重复句/跨块/补充平面字符、旧版/校订/拆分；确认原生来源 PUBLIC_RELEASE 门禁已在权威规范与验证器同时生效。
- [ ] 缺 Schema/样例保持 BLOCKED；D-07/D-08 对相关知识/流派入口独立登记。不得仅因有回执就升级 ACCEPTED，也不在下游二次 OCR/切句。

### NC-021：对象上传、入库和版本激活

- [ ] 新增 `SERVER/xuan/handlers/library_imports.py`、`xuan/library/import_service.py`、`xuan/handlers/library_queries.py`、`tests/test_library_imports.py`，扩展同一 OpenAPI；输入仅 NC-020 已冻结记录。
- [ ] 实现缺失对象登记、完整性核验、隔离分批装载、校验报告、作用域内原子 active 指针；保留历史修订查询。对象存储/Firestore 各自事务边界与恢复状态明确。
- [ ] 运行 `python3 -m pytest tests/test_library_imports.py -q`；验收漏文件/悬空引用/hash 错/dev 包拒绝、失败旧版可读、同 release 异清单拒绝、传输分片不变 block_id。真实对象中断恢复为必要补证。

### NC-022：原书阅读与原句注解

- [ ] 新增 `CLIENT/lib/src/reader/book_reader_page.dart`、`anchor_resolver.dart`、`annotation_controller.dart`、`test/reader/anchor_contract_test.dart` 与 `test/reader/annotation_flow_test.dart`。
- [ ] 使用 NC-020 原生/扫描样例，固定版本取正文，Unicode 范围与 Python hash 对账，跨块与无知识 Span 正文可注解；原图/派生图能力分开显示，不制造 EPUB 页码/字框。
- [ ] 运行 `flutter test test/reader/anchor_contract_test.dart test/reader/annotation_flow_test.dart`；旧注解保留原始 AnchorRef，歧义显示待处理，不取第一个同句命中。

### NC-023：Tooltip 真实链路原型

- [ ] 新增 `CLIENT/example/lib/tooltip_prototype_page.dart`、`CLIENT/example/integration_test/tooltip_discussion_test.dart`，只通过同一 DiscussionContext/REST/Notification 适配；不修改占卜盘面代码。
- [ ] 演练原句 → 原型讨论 → 回复/@ → 另一个账号通知 → 原书/原型定位同一 thread/comment；赞踩收藏分享及资料/私信路由使用真实宿主适配。
- [ ] 在已登记设备/真实后端运行集成测试，记录同一 ID、服务端存储和通知证据；静态页面、mock JSON、纯按钮回调或知识关系未交付均不能通过。

### NC-024：全链路验收与交接

- [ ] 新增 `SPEC/ACCEPTANCE.md`、`CLIENT/example/integration_test/notes_full_flow_test.dart`，逐项映射 R-01～R-20 到提交、命令、真实数据与截图/录屏（适用时），不能只记录测试数。
- [ ] 主 Agent 复核所有子包依赖、范围、原始证据与失败路径；检查 Undo/Redo/IME、重启、云恢复、ACL 全入口、并发评论/outbox、双入口和修订迁移。
- [ ] 更新各工作包验收和总表；未完成项保持未勾选。输出配置/部署/迁移/恢复说明及准确版本组合，不把 F 项算本期欠交，也不把 E 依赖未完成隐藏掉。

## 8. 后续版本登记（当前不执行）

- [ ] F-01：完整键盘操作设计。**当前缺失；本期仅撤销/重做。** 后续单独做需求与设计，本次不提供额外按键表、不实现配置框架。
- [ ] F-02：原书与 Markdown 分屏、阅读分页体验。
- [ ] F-03：Markdown 引文点击定位原书。
- [ ] F-04：高亮/圈画/手写图形标记，评估 notebook 图元能力。
- [ ] F-05：通用附件、复杂富文本与实时协作，另行确定范围。

本文件为开发任务定义，不是完成报告；代码、Schema 和测试均应通过各自 READY 工作包执行。用户后续变更必须回写 PRD/Design/Plans/Tasks 的对应 ID，保持四份文档一致。
