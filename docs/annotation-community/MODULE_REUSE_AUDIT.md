# 既有模块复用调查与主 Agent 裁定

状态：`SOURCE_REVIEWED_NOT_RUNTIME_VERIFIED`；2026-09-10。

用户授权三位 `gpt-5.6-terra` 只读调查：`storage_audit`、`social_notification_audit`、`client_notes_audit`。调查范围为 xuan-storage、social、notification、notebook、Repository 系列及 Python Functions。主 Agent 抽查关键实现并汇总；未运行两设备、真实云或完整 APP 联调，不以文件存在证明部署完成。书籍原文 U/A 协议不在本次调查范围。

下面路径相对 `/Users/jingtaiwei/Git/Public/xuan-migration/`；`SERVER/` 专指 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py/`。行号为本次读取位置。

## 1. 存储：可复用机制与尚缺链路

| 能力 | 源码证据 | 裁定 |
|---|---|---|
| 私人多通道策略 | `xuan-storage/core/lib/model/storage_policy.dart:41,90` | private 允许 cloud/LAN/WebRTC，属于策略，不代表生产链路已装配 |
| 云 row SDK | `xuan-storage/firebase/lib/persistence_firebase.dart:109,198,213,481`；`firebase_realtime_remote_gateway.dart:27` | 有真实 SDK push/pull；Firestore 除 layout_template 专用分支还有 generic upsert。不能称“所有云代码都是 fake”，也不能据此称宿主笔记已接通 |
| 私有 row 编码 | `xuan-storage/drift/lib/sync/record_outbox_mapper.dart:11` | 明文 JSON 包括 meta/moduleData/searchTags；禁止直接用于私人笔记正文备份 |
| 云 blob | `xuan-storage/core/lib/model/blob_gateway.dart:76`；`firebase/lib/media/blob_gateway_firebase.dart:17` | 端口可用；该 Firebase 文件实际是内存 fake，生产 BlobGateway 在此次包内调查未发现 |
| 本地 blob 加密 | `xuan-storage/drift/lib/blob/drift_local_blob_store.dart:94,152`；`blob_cipher_registry.dart:28`；`aes_gcm_blob_cipher.dart:30,73` | 有执行加密/缺密钥拒绝的组件；单设备 DEK/keyVersion=1 不等于跨设备恢复协议，也不等于整库加密 |
| WebRTC 配对 | `xuan-storage/p2p/lib/web_rtc_transport.dart:128,181,209`；`device_pairing.dart:93,135` | 有签名与通道绑定；设备配对与同账号授权分开，需要授权源/吊销接线 |
| 同账号 guard | `xuan-storage/core/lib/sync/same_account_im_reconciliation.dart:21` | 存在 IM guard，不能直接当通用笔记会话授权；见下方主 Agent 补充 |
| 同步设置/删除 | `xuan-storage/core/lib/sync/sync_runtime.dart:44,157`；`core/lib/configuration/sync_configuration_manager.dart:24`；`drift/lib/record/local_record_repository.dart:74` | 有启停/批量/重试及本地软删；未发现备份专属设置、保留/恢复协议 |
| 本地备份 | `xuan-storage/drift/lib/scope/scope_backup.dart:5,25` | scope 切换的 SQLite 文件复制，不是长期加密云备份 |

主 Agent 复核发现：`SameAccountSessionGuard.verifyPeerSession` 接收 `peerDeviceId`、`peerFingerprint`，但其当前函数体未比较这两项，且只排除 revoked 而非明确要求 active。签名/DTLS 由传入布尔值表示。授权适配必须把实际会话签名、设备、公钥指纹、账号与权威授权记录绑定，并验证 active/epoch；不能把 guard 类名或注释当作完整授权证明。

接入裁定：沿用 StoragePolicy、同步调度、outbox、BlobCipher 和传输端口；新增笔记 entityType/加密 mapper、生产 blob 网关接线、完整备份 manifest、密钥恢复与设备授权流程。不得自创密码算法；现有协议缺口进入明确前置工作项。私有策略和公共发布投影分别注册。

服务端补证：`SERVER/xuan/handlers/media.py:20,42,62,78,111` 有真实 bucket 删除调用、对象完成触发器定义和 pending 媒体 24 小时清理；它们面向 `playground_media`，不是私人备份或 P2P relay。触发器有导出不代表已经部署。本轮未发现该服务端私人分块上传/完整备份清单/恢复下载接口。可复用 Firebase 身份验证（`SERVER/xuan/handlers/playground_rest.py:689`）和 bucket 基础，新增私有命名空间、上传会话/完成校验/授权下载/可重试删除。清理器必须按集合和对象用途双重隔离，不能仅凭相似路径认为安全。

## 2. 社交与通知：逐项复用

| 能力 | 源码证据 | 裁定 |
|---|---|---|
| 两级回复 | `SERVER/xuan/handlers/replies.py:29,96`；`social/lib/src/plaza/viewmodel/plaza_post_detail_viewmodel.dart:202` | 可复用 depth/root/reply_to 结构与归属校验；服务端写 reply 尚未写通知 outbox，且绑定 postId；新社区需要事务化 ACL 与通用主题接线 |
| 赞/取消赞 | `SERVER/xuan/handlers/likes.py:22` | like/unlike 已有；dislike、互斥切换与新目标类型需补齐 |
| 收藏与分享 | `SERVER/xuan/handlers/bookmarks.py:17`；`social/lib/src/plaza/detail/plaza_post_detail_app_bar.dart:152`；`list/plaza_post_card.dart:408` | 收藏仅 post；分享空回调/图标不算链路。新内容资源与当前 ACL 校验需接入 |
| @ 候选 | `SERVER/xuan/handlers/user_search.py:165`；`social/lib/src/mention/mention_text_controller.dart:102` | 候选查询可用；当前只插入显示名文本，需要稳定用户 ID 的结构化 mention 和通知事件 |
| 关注/私信/拉黑 | `SERVER/xuan/handlers/follow.py:18`；`conversations.py:173,253` | 有服务端实现；复用账号关系与私信调用，检查宿主注入，不能重建独立 IM |
| 资料前端 | `social/lib/src/profile/public_profile_viewmodel.dart:84`；`relationship/user_relationship_viewmodel.dart:9,206` | 存在本地翻转/mock 退路；界面能点不代表真实关系已保存 |
| 举报 | `SERVER/xuan/handlers/moderation.py:20`；`social/lib/src/plaza/viewmodel/plaza_post_detail_viewmodel.dart:529` | 可复用流程与端口，新增笔记/评论目标适配 |
| 私有/公开、发布修订与收回 | `SERVER/xuan/handlers/posts.py:31,140` | 现 post 的 active/tombstone、匿名身份和 revisions 初始化不满足笔记发布模型；需要独立 community 内容/版本/权限 |
| 旧 outbox 消费 | `SERVER/xuan/handlers/notifications.py:46` | 当前只处理 reply_verified/verification_revoked/like_added/dm_message/dm_accepted；没有普通评论、回复、@ 分支 |
| 可靠接收/ACK/补拉 | `notification/lib/src/ack/ack_pipeline.dart:69,142`；`realtime/connection_manager.dart:156`；`shelf/body_fetch_wake_handler.dart:41` | 管线可复用；MessageBodyFetcher、BackfillSource 等端口需要生产适配与服务端业务接口 |
| ACK 拒绝语义 | `notification/lib/src/ack/ack_pipeline.dart:142`；`docs/integration-guide.md:104,119` | 当前 ReceiptRejected 整批结束并报告；文档“任意 4xx 重试”与之矛盾，HTTP→Outcome 映射冻结时须修正，不由业务猜测 |

主 Agent 额外核验：旧 `notifications.py:17` 使用“查询是否已通知 → 随机 ID 写通知”的分离操作，不能证明并发幂等；且按 event_id 全局查询不支持同一事件多收件人的可靠扇出。新投递采用 `(event_id, recipient_id)` 唯一身份与事务/原子创建；将创建通知和推送重试分开，避免记录已存在后丢失推送重试机会。

回复当前流程在事务外读主题，再写回复；不能直接满足“收回和回复并发时权限一致”的要求。新模块需在同一业务事务读取权限版本、写入评论与 outbox。公共更新/收回都修改同一权限协调记录，使并发读写可冲突重试。

调用链裁定：两入口上下文 → 同一 thread → 已鉴权业务 REST 命令 → Firestore 事务（ACL、内容、outbox）→ 按接收者幂等生成 delivery → Notification 适配 → 接收持久化 → ACK；点击时重新鉴权并定位。结构化 @ 与回复对象重叠只发一份通知。私人草稿不进社交通知。

## 3. Flutter 与 Repository

| 能力 | 源码证据 | 裁定 |
|---|---|---|
| Markdown Plus | `xuan-common-ui/sample/pubspec.yaml:35`；本机缓存 `flutter_markdown_plus-1.0.12` | 依赖可用；未发现可直接接入的完整笔记编辑器。采用 Plus 渲染，薄输入工具栏自行整合 |
| 现有正文输入/显示 | `social/lib/src/plaza/create/plaza_create_post_input_fields.dart:80`；`detail/plaza_post_detail_main_card.dart:233` | TextField/MentionRichText，不能冒充 Markdown 编辑预览 |
| 图片引用模式 | `social/lib/src/plaza/state/plaza_common_state.dart:34`；`viewmodel/plaza_post_composer_viewmodel.dart:18` | 可借 provider-neutral 附件引用与已上传资源提交边界；私人附件仍必须独立权限/加密 |
| 草稿写队列 | `notebook/lib/src/annotation/persistence/write_queue.dart:16`；`persistence/database.dart:57` | 可借串行/合并写入与 WAL 模式；是排盘图元模型，不直接复用为读书笔记表 |
| 历史与保存 | `notebook/lib/src/annotation/model/history.dart:73`；`persistence/database.dart:381`；`engine/annotation_engine.dart:467` | undo/redo 不是永久历史；commitDraft 删除旧 committed；内存降级 save 返回 true。新笔记必须新增不可变修订，只有持久成功才报已保存 |
| 软删/恢复 | `repository-contract-kernel/lib/src/slices.dart:37`；`base/crud_base_repository.dart:69` | 可复用契约；不会自动提供回收站保留期、云清理或发布 ACL |
| REST 版本条件 | `repository-rest-adapter/lib/src/rest_storage_driver.dart:179,230` | write 可传 If-Match/读 ETag，deleteOne 无 expectedRev；笔记删除优先用带版本的业务命令，不为一项业务先扩大整个 kernel 接口 |
| OpenAPI 验证 | `repository-rest-adapter/openapi/openapi.yaml:38`；`test/openapi_validation_test.dart:11` | operation 下的 headers 不是标准请求头参数；现测试为 YAML 字段断言，不是规范校验。正式输出需真正解析与契约测试 |

主 Agent 不采纳的子 Agent 提案：以 `note_revision_id` 代替原书修订定位、用只含 quote/offset/hash 的上下文当规范锚点、用明文通用 notes CRUD 传私人修订。这些与已确认上游稳定身份和私人加密边界冲突。原书位置继续按 U 系列契约，私有 API 只处理密文封装；本期无需先修改所有 Repository 删除接口，可通过业务命令保持局部改动。

第三方核对：[flutter_markdown_plus 官方包说明](https://pub.dev/packages/flutter_markdown_plus) 用于渲染能力；[OpenAPI 3.1 Operation/Parameter 规范](https://spec.openapis.org/oas/v3.1.0.html#operation-object) 要求请求头作为 header 参数。版本号是本机已查到的依赖，不是对未来最新版本的承诺。

## 4. 接下来应该新增的最小模块

1. 笔记本地模型与修订 Repository、编辑保存状态机；不复刻排盘图元库。
2. 私有同步加密封装、真实备份网关/清单与恢复授权接线；继续用现有存储和传输组件。
3. 公共发布投影与权限协调记录；两入口共用内容/讨论身份。
4. 两级评论业务事务、互斥 reaction、结构化 mention 与通用收藏/分享目标适配。
5. 通知业务事件/投递接口及宿主适配，不重写 Notification 内核或 IM。
6. 合规 OpenAPI、Drift/DTO 映射、Flutter 页面与 Tooltip 原型的纵向验收。

具体交互、候选默认值及验收顺序见 [接入细化稿](CLIENT_SERVER_DESIGN_DETAIL_DRAFT.md)。本次调查把“等已离场维护者回复”改为有代码证据的明确工作项；密钥恢复仍缺成熟接入方案，不能据此宣布设计全部冻结。两名 Agent 初次定位用了错误的相邻根路径：主 Agent 纠正服务端地址并取得补查；客户端原书锚点建议未依草案，故已明确不采纳。缺失文件不能据此判为项目缺能力。
