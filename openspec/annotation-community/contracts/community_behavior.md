# 行为事件、假名化与私人笔记元数据上报契约（NC-026）

状态：`PREPARING`（G0 待四查后转 `READY`）。权威来源：[DESIGN](../DESIGN.md) §2（BehaviorEvent / PseudonymMapping 行）、§2.1、§2.1.1、§4.3、§7.4、§10、**§11 全文**、§11.4 事件目录；[PRD](../PRD.md) R-21、§7；[TASKS](../TASKS.md) NC-026；[community-models](community-models.md) §0.1、§3.2、§4；[community_server](community_server.md) §2.2、§3.2、§3.3、D-NC009-04；[community_api](community_api.md) §2、§3.1、§4.1、§5.3、§6、§7、§14；[state-machines](state-machines.md) SM-C。本文把 DESIGN §11 已定的规则落到模块、集合、Schema、端点与测试判据，供执行者照抄；与上游冲突以上游为准并回报主 Agent。

**红线**：本契约与全部产物不得出现 `exactly-once` 声称（上报语义为 at-least-once，见 §5.3）。

## 1. 仓库、环境与基线

| 项 | 实值 |
|---|---|
| SERVER（canonical，写入目标） | `D:/Programme/xuan-server/functions-py`（git 根即此目录，`master`，HEAD `992088e`） |
| CLIENT（写入目标） | `D:/Programme/xuan/reading-notes`（`main`，HEAD `19afe37`＝NC-014 落地后基线，D-NC026-26） |
| REST（写入目标） | `D:/Programme/xuan/repository-rest-adapter`（`main`，HEAD `b60bfbd`） |
| RULES（新增测试文件） | `D:/Programme/xuan-server/xuan-server`（`main`，HEAD `a354463`）；规则文件在 `server/firestore.rules`（**不在仓根**），规则测试在 `server/functions/test/` |
| Emulator | Firestore `192.168.0.165:8080`、Auth `192.168.0.165:9099`（2026-09-13 实测可达） |
| Python | SERVER `.venv/Scripts/python.exe`（Windows）/ `.venv/bin/python`（macOS）；learn_system `.venv/Scripts/python.exe` |
| 既有测试基线 | SERVER pytest `5 failed, 568 passed, 3 xfailed`，FAILED 恰为 §8.1 五个既有 ID；REST `dart test` `+81: All tests passed!`；RULES `npm test -- community_rules` `Tests: 153 passed, 153 total`；CLIENT `flutter analyze` 无问题、`flutter test` `+296` |

## 2. 模块与集合

### 2.1 新增/修改文件（写入白名单）

| 仓 | 文件 | 内容 |
|---|---|---|
| SERVER | `xuan/community/pseudonyms.py` | **新增**：`get_or_create_actor_pseudonym(tx, client, owner_scope, candidate)`、`resolve_actor_pseudonym(client, owner_scope)`、`note_ref_for(actor_pseudonym, note_id)`、常量 `SERVER_PLATFORM = "server"`、`SERVER_APP_VERSION = "0.0.0"`、`CLIENT_EVENT_TYPES` |
| SERVER | `xuan/community/behavior_events.py` | **新增**：`ingest_client_events(owner_scope, events, now)`（校验 → 事务内 create-if-absent → `(accepted, duplicates)`）、`validate_client_event(event)`、`EVENT_TYPES` 19 值闭集、`MAX_EVENTS_PER_BATCH = 500`、`MAX_EVENTS_PER_TRANSACTION = 100` |
| SERVER | `xuan/handlers/analytics_events.py` | **新增**：`analytics_events_py`（`on_request`）承载 W17、R11 |
| SERVER | `xuan/community/command_service.py` | **修改**：仅 §3.1「Step 3.3 行为事件」一处，事务内事件文档补齐 §3.1 的六个外层字段；**其余行零改动** |
| SERVER | `xuan/config.py` | **修改**：仅在 `COLLECTIONS` 追加一个键 `community_analytics_rejections`（§2.2）；其余行零改动 |
| SERVER | `main.py` | **修改**：仅追加 `analytics_events_py` 的 import 与导出一行 |
| SERVER | `tests/conftest.py` | **修改**：仅在 `clean_collections` 的 `names` 追加 `community_analytics_rejections`（**只追加**） |
| SERVER | `tests/test_behavior_events.py` | **新增**：§8.3 的 26 个测试 |
| SERVER | `tests/test_community_validation.py` | **修改**：仅 `EXPECTED_SCHEMA_SHA256` 字典里 `community_behavior_event.schema.json` 一项的字面量改为 §9 的 `SCHEMA_SHA`；其余行零改动 |
| SERVER | `xuan/community/schemas/community_behavior_event.schema.json` | **修改**：与 `learn_system/openspec/schemas/community_behavior_event.schema.json` 逐字节相同（§9） |
| CLIENT | `lib/src/analytics/private_note_metrics.dart` | **新增**：§6 全部类型与默认实现 |
| CLIENT | `test/analytics/private_note_metrics_test.dart` | **新增**：§8.4 的 18 个测试 |
| REST | `openapi/openapi.yaml` | **修改**：按 §10 追加 W17、R11、4 个 Schema、2 个示例引用；既有 20+ 路径零改动 |
| REST | `test/community_openapi_contract_test.dart` | **修改**：末尾追加 4 个测试（§8.2）；`expectedCatalog` 追加 2 行；`interaction examples manifest ...greaterThanOrEqualTo(17)` 不动 |
| REST | `test/fixtures/openapi/examples/analytics_events_batch.json`、`analytics_pseudonym.json` | **新增** 2 个示例；`manifest.json` 末尾追加 2 项（20 → 22） |
| RULES | `server/functions/test/community_rules.test.ts` | **修改**：仅追加 §7 的 `describe`（4 个用例），既有 153 例零改动 |
| learn_system | `openspec/schemas/community_behavior_event.schema.json` | **规格侧已落位**（本契约作者于 2026-09-13 改写，§9）；执行者只复制不重写 |

禁止：上表以外任何文件。特别地 `xuan/community/content_service.py`、`discussion_service.py`、`interaction_service.py`、`access.py`、`errors.py`、`ids.py`、`community_hash.py`、`push.py`、`identity.py` 与 `tests/test_community_interactions.py`、`tests/test_community_comments.py`、`tests/test_registration.py`、`tests/test_main_exports.py`、`tests/community_helpers.py` 一律**零改动**（D-NC026-08）。

### 2.2 Firestore 集合与文档

| 键 | 集合 | 文档 ID | 写入者 | 字段 |
|---|---|---|---|---|
| `community_behavior_events`（既有） | 同名 | `event_id` | SERVER 命令事务（既有）+ 本任务上报端点 | §9 的 12 字段 |
| `community_pseudonym_mappings`（既有） | 同名 | `owner_scope` | SERVER（既有命令路径 + 本任务 R11） | `account_id`（= owner_scope）、`actor_pseudonym`、`created_at` |
| `community_analytics_rejections` | 同名 | `f"{owner_scope}__{date_utc}"` | 本任务 | `rejected_count`（integer ≥ 0）、`last_rejected_at`（UTC）；**只记计数与时间，不记任何事件内容或 event_id** |

`community_analytics_rejections` 只服务于 §5.4 的可观测性断言，读路径只有运维查询，不进任何 API。

## 3. 服务端事件（既有写入路径的补全）

### 3.1 事件文档外层字段（D-NC026-01）

`xuan/community/command_service.py` 的事务内事件写入（现状见 §12.1 取证）**当前只写 6 个字段**，而 `community_behavior_event.schema.json` 要求 12 个必填字段。本任务在**同一处**补齐为：

```python
tx.set(event_ref, {
    "event_id": event_id,
    "event_type": ctx.operation,
    "actor_pseudonym": actor_pseudonym,
    "occurred_at": committed_at_iso,
    "received_at": committed_at_iso,          # 服务端事件：与 occurred_at 同值（同一事务提交时刻）
    "schema_version": 1,
    "object_type": object_type,                # 见下表
    "object_id": object_id,                    # 见下表
    "note_ref": None,                          # 服务端事件恒为 null
    "platform": pseudonyms.SERVER_PLATFORM,    # "server"
    "app_version": pseudonyms.SERVER_APP_VERSION,
    "attributes": attributes,
})
```

`object_type` / `object_id` 取自 `outcome.resource_ids` 与 `ctx.operation`，映射唯一：

| operation | object_type | object_id |
|---|---|---|
| `content.publish` / `content.update` / `content.withdraw` / `content.trash` / `content.restore` / `content.purge` | `content` | `resource_ids["content_id"]` |
| `comment.create` / `comment.edit` / `comment.delete` | `comment` | `resource_ids["comment_id"]` |
| `reaction.set` | `resource_ids["target_type"]` | `resource_ids["target_id"]` |
| `bookmark.set` | `resource_ids["target_type"]` | `resource_ids["target_id"]` |
| `share.create` / `share.revoke` | `share_link` | `resource_ids["share_id"]` |
| `report.create` | `report` | `resource_ids["report_ref"]` |

映射缺失（`KeyError`）时 `object_type = ctx.operation` 前缀段、`object_id = ""`——**不允许**抛异常（抛出即整笔回滚，见 NC-009 §3.2）。该兜底分支不写测试（不可达），仅作防御。

### 3.2 attributes 冻结为「按 event_type 的封闭允许集」（D-NC026-02）

`attributes` 不再开放式 `{"type":"object"}`，改为 `oneOf` 之上的 `allOf`/`if-then` 分派（§9 Schema）：每个 `event_type` 只允许自己的键，未知键拒绝；**所有服务端事件的成员均为可选**，因此既有 producer（`content.publish` 只写 `{is_republish}`、其余 14 个 operation 写 `{}`）**无需改动即满足 Schema**。

| event_type | attributes 允许键（全部可选） | 现状 producer 实际写入 |
|---|---|---|
| `content.publish` | `is_republish` (bool)、`image_count` (integer ≥ 0) | `{is_republish}` |
| `reaction.set` | `value` (`like`/`dislike`/null)、`previous_value` (同) | `{}` |
| 其余 15 个服务端 operation（`content.update/withdraw/trash/restore/purge`、`comment.create/edit/delete`、`bookmark.set`、`share.create/revoke`、`report.create`、`backup.begin/complete/delete`） | 无（恰为空对象 `{}`） | `{}` |

`content.publish.image_count` 与 `reaction.set.{value,previous_value}` 是 DESIGN §11.4 点名的维度，但填充它们需要改 NC-009 / NC-012a 已验收文件的 producer，且 `tests/test_community_interactions.py:149` 断言 `reaction.set` 的 `attributes == {}`；本任务不填充，登记为待裁决 P1（§13）。

### 3.3 event_type 与 platform 封闭（D-NC026-03）

- `event_type` 为 19 值闭集：17 个服务端 operation（`community_api.md` §2 的操作枚举，含无端点的 `backup.*` 三个保留值）+ 2 个客户端事件（`private_note.revision_saved`、`private_note.session_ended`）。非闭集值一律拒绝。
- `platform` 为 7 值闭集：`server`、`android`、`ios`、`windows`、`macos`、`linux`、`web`。服务端事件恒 `server`；客户端事件由宿主上报（§6.2）。

### 3.4 只追加（D-NC026-10）

- 服务端代码**不提供**对 `community_behavior_events` 的 update / delete 路径；静态扫描断言 `xuan/**/*.py` 中不存在 `.collection(COLLECTIONS["community_behavior_events"])` 后接 `.update(` / `.delete(` / `.document(...).set(..., merge=True)` 的调用（§8.3 的 `server_code_has_no_update_or_delete_on_behavior_events`）。
- Firestore 规则不新增任何 `match`（沿用顶层默认拒绝；`server/firestore.rules` 现状见 §12.4）；RULES 仓追加 4 条**显式**用例（§7）。
- 需要修正历史事件时只升 `schema_version` 并追加新事件，不改写历史（DESIGN §11.5）。

## 4. 假名化（`xuan/community/pseudonyms.py`）

- `actor_pseudonym` 恒为 `psn_` + `secrets.token_hex(16)`（32 位小写 hex），**禁止**由 account_id 哈希或加密推导（DESIGN §11.3）。既有实现已满足（`command_service.py:72` 用 `ids.new_id("psn_")`，其内部为 `uuid4().hex`；本次改为 `secrets.token_hex(16)` **不要求**——见 D-NC026-17）。
- 映射文档 ID = `owner_scope`，字段 `account_id`（= owner_scope）、`actor_pseudonym`、`created_at`；一个账号一个假名、恒稳定。
- 事件文档**不含** `owner_scope` / `app_user_id` / `account_id`（§8.3 `event_documents_never_contain_account_id`）。
- 客户端事件与命令事件共用同一个映射文档（同一账号在两条路径得到同一假名）。

## 5. 客户端上报端点（`xuan/handlers/analytics_events.py`）

### 5.1 W17 `POST /v1/analytics/events`（非命令写，D-NC026-09）

- 认证：`Authorization: Bearer <ID token>`；`owner_scope` 服务端派生。无 `Idempotency-Key`、不进命令账本、不产生行为事件（`community_api.md` §3.2 的 17 操作枚举**不变**）。
- 请求体 `AnalyticsEventBatch{events: AnalyticsEventRequest[]}`，`events` 长度 1～500；`AnalyticsEventRequest{event_id, schema_version (const 1), event_type, occurred_at, note_ref, platform, app_version, attributes}`；`additionalProperties: false`。
  - `event_id`：`^bev_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$`（D-NC026-06：`bev_` + UUIDv4 去连字符 32 位小写 hex）。
  - `event_type`：本端点只接受 `private_note.revision_saved` / `private_note.session_ended`；其余（含 17 个服务端 operation）→ 400 `invalid_argument.event_type`。
  - `note_ref`：64 位小写 hex（必填，可显式 null 仅当客户端无法计算时——本契约要求私人笔记事件恒非 null）。
  - `platform`：§3.3 闭集去掉 `server`（`android/ios/windows/macos/linux/web`）。
  - `attributes`：§3.2 的两个私人笔记分支（§9），成员**必填**（D-NC026-04），额外允许可选 `dropped_before`（integer ≥ 1，D-NC026-11）。
- 服务端每条事件：`received_at` = 服务器 UTC 现在；`actor_pseudonym` = §4 的映射值（不存在则用密码学随机候选 create-if-absent 创建）；`object_type = object_id = null`、`note_ref` 原样采用客户端值（**服务端不重算**，它拿不到 note_id，这是刻意的信任边界，D-NC026-18）。
- 写入：`tx.create(事件文档)`（create-if-absent；`AlreadyExists` 记 `duplicates` 不抛错）。每事务最多 100 条（`MAX_EVENTS_PER_TRANSACTION`），超出批内顺序拆分为多个事务。
- 响应：200 `AnalyticsEventsAccepted{accepted (int ≥ 0), duplicates (int ≥ 0), actor_pseudonym (psn_)}`，`additionalProperties: false`。`accepted + duplicates == len(events)`。
- 语义：**at-least-once**。任一事务失败 → 503 `unavailable`，已提交部分不回滚；客户端以同一批重试，`event_id` 去重保证不重复落盘。**不得**在任何文档、注释或测试名中声称 exactly-once。
- 幂等：同批重复提交 → `accepted = 0`、`duplicates = len(events)`、事件条数不变。

### 5.2 R11 `GET /v1/analytics/pseudonym`（D-NC026-07）

- 200 `ActorPseudonym{actor_pseudonym (psn_)}`，`additionalProperties: false`。
- 首次调用 create-if-absent 建立 §4 的映射（幂等）；**不写行为事件**、不进命令账本。
- 存在理由：DESIGN §11.2 的 `note_ref = SHA256_hex(UTF8(actor_pseudonym + "/" + note_id))` 要求客户端持有假名，而 DESIGN 未定义假名交付通道；本契约补一个读端点，客户端按账户作用域缓存假名（§6.3）。
- 限流并入「全部读端点合计 600/分钟」（`community_api.md` §6）。

### 5.3 去重与计数

- 去重键恰为 `event_id`（文档 ID）。同批内重复 `event_id` 只算一条 `accepted`，其余计 `duplicates`。
- 服务器事件与客户端事件共用同一集合与同一 `bev_` 文档 ID 空间：客户端 UUIDv4 派生 ID 与服务端 SHA256 派生 ID 碰撞概率可忽略，不做额外命名空间（D-NC026-19）。

### 5.4 校验与错误

| 场景 | HTTP | `code` | 附加字段 |
|---|---|---|---|
| 未认证 | 401 | `unauthenticated` | — |
| 请求体 Schema 不通过（含 `events` 为空数组、`note_ref` 非 hex64、`platform` 非闭集、`attributes` 未知键或缺必填成员） | 400 | `invalid_argument.events` | `field`（JSON Pointer，前缀 `/events`，例 `/events/0/attributes/char_count`） |
| `event_type` 非本端点接受的 2 值 | 400 | `invalid_argument.event_type` | `field` |
| `events` 长度 > 500 | 413 | `too_large.events` | `limit` = 500 |
| 限流 | 429 | `rate_limited` | `retry_after_seconds` 1～60 |
| 写入失败 | 503 | `unavailable` | — |

被拒事件只在 `community_analytics_rejections` 记计数与时间（§2.2），不落 `community_behavior_events`。校验顺序：身份 → 批长度 → 逐条 Schema → 逐条 `event_type` 闭集（同一请求多错只报第一条）。

## 6. 私人笔记元数据（CLIENT，`lib/src/analytics/private_note_metrics.dart`）

### 6.1 契约与依赖（D-NC026-20）

```dart
abstract class AnalyticsTransport {
  Future<AnalyticsReportResult> postEvents(List<Map<String, Object?>> events); // 返回 server 的 accepted/duplicates
  Future<String> fetchActorPseudonym();                                        // R11，缓存于调用方
}

abstract class PrivateNoteMetricsStore {          // 注入式端口；默认实现 FilePrivateNoteMetricsStore(目录, 文件名)
  Future<List<Map<String, Object?>>> readAll();
  Future<void> append(Map<String, Object?> event);
  Future<void> removeIds(Set<String> eventIds);
  Future<int> dropOldest(int count);              // 返回实际丢弃条数
}

class PrivateNoteMetrics {
  PrivateNoteMetrics({
    required AnalyticsTransport transport, required PrivateNoteMetricsStore store,
    required Clock clock, required String platform, required String appVersion,
    required IdGenerator ids, int queueCap = 10000,
  });
  Future<void> onRevisionSaved({required String noteId, required String markdown,
      required int attachmentCount, required int mentionCount, required int bindingCount,
      required bool isRestore, required bool isMerge});
  Future<void> onSessionEnded({required int editDurationSeconds, required int revisionsSaved});
  Future<FlushResult> flush();
  int get pendingCount;
  Future<void> clearPseudonymCache();            // 账号切换时调用
}
```

- `Clock`、`IdGenerator` 复用 `lib/src/domain/clock.dart`、`lib/src/domain/ids.dart`（只读消费，不改这两个文件）。
- `FilePrivateNoteMetricsStore` 用追加式 JSONL 文件；写入追加、丢弃最旧时按行截断（写临时文件后 rename 原子替换）。
- 事件在 `onRevisionSaved` / `onSessionEnded` 内**先落本地队列再 flush**；`flush` 失败不抛穿给调用方（返回 `FlushResult.failed`），不阻塞编辑与自动保存（DESIGN §3 的编辑态机不在本任务范围内改动）。

### 6.2 事件构造

| 事件 | event_type | attributes（全部必填） |
|---|---|---|
| 新修订保存 | `private_note.revision_saved` | `char_count` = `markdown.runes.length`（**code point**）、`attachment_count`、`mention_count`、`binding_count`、`is_restore`、`is_merge` |
| 编辑会话结束 | `private_note.session_ended` | `edit_duration_seconds`、`revisions_saved` |

- `char_count` 按 code point，用 `String.runes.length`；**禁止**用 `utf8.encode(...).length` 或 `String.length`（UTF-16 码元）——含一个 4 字节字符（如 `𠀀` U+20000）的用例三者互不相等。
- `event_id` = `"bev_" + <UUIDv4 去连字符 32 位小写 hex>`（`ids` 生成，D-NC026-06）。
- `occurred_at` = 设备 UTC 时间（`clock.nowUtc()`），格式 `YYYY-MM-DDTHH:MM:SS(.fff)?Z`。
- `platform` / `appVersion` 由宿主注入（`platform` ∈ §5.1 闭集；`appVersion` 来自 `pubspec.yaml` 的版本字符串）。
- `note_ref` = `SHA256_hex(UTF8(actor_pseudonym + "/" + noteId))`；假名先经 R11 取得并缓存（§6.3）。**note_id 原值、标题、正文、附件名一律不出现在任何上报字节里**（DESIGN §11.4）。
- 事件不进入命令账本、不产生通知、不写 outbox。

### 6.3 假名缓存与账号隔离

- 假名按账户作用域缓存在 `FilePrivateNoteMetricsStore` 的队列文件旁（同目录 `<owner>__pseudonym.json`）；缓存缺失时 `flush` 先调 R11，再构造 `note_ref`。
- 账号切换必须 `clearPseudonymCache()`，否则会把上一个账号的 `note_ref` 写到新账号（测试 `pseudonym_cache_is_cleared_on_account_switch`）。
- `owner_scope` 由注入的仓储/账号上下文提供，不由本模块从 note_id 推导。

### 6.4 离线暂存、上限与 `dropped_before`（D-NC026-11）

- 队列上限 `queueCap = 10000`（DESIGN §11.4）。入队后若 `pendingCount > 10000`，丢弃**最旧**的 `pendingCount - 10000` 条并从队列删除。
- 存在丢弃时，**下一条**要上报的事件（按入队顺序的第一条）在 `attributes` 中追加 `dropped_before` = 本次丢弃条数；该字段只出现在这一条事件上，成功上报后不再重复携带。
- `flush` 成功后从队列删除已确认（`accepted + duplicates == 批长`）的事件；失败保留全部。
- 批大小 500（与服务端 `MAX_EVENTS_PER_BATCH` 一致）；`flush` 一次只发一个批，由调用方驱动下一批。

## 7. Firestore 安全规则（RULES）

- `server/firestore.rules` **零改动**：`community_behavior_events` 与 `community_pseudonym_mappings` 由顶层默认拒绝覆盖（§12.4）。
- `server/functions/test/community_rules.test.ts` 只追加一个 `describe`：

```ts
describe('BehaviorEvent is append-only (NC-026)', () => {
  // 两个上下文（unauthenticated / alice(authenticated)）× update / delete = 4 个用例，
  // 断言 assertFails，显式覆盖 DESIGN §11.5「禁止 update 与 delete」。
});
```

- 计数：`COMMUNITY_COLLECTIONS`（19）× 2 上下文 × 4 操作 + 1 回归 = 153，**加上本任务的 4 个用例 = 157**。期望 `Tests: 157 passed, 157 total`。

## 8. 测试判据

### 8.1 全量命令与期望（TDD.md §1 同源）

| # | 目录 | 命令 | 期望 |
|---|---|---|---|
| 1 | functions-py | `.venv/Scripts/python.exe -m pytest tests -q -rf -p no:cacheprovider`（带 Emulator 变量） | `5 failed, 568 passed, 3 xfailed`；FAILED 恰为下面五个 |
| 2 | xuan-server/server/functions | `npm test -- community_rules`（带 Emulator 变量） | `Tests: 157 passed, 157 total` |
| 3 | repository-rest-adapter | `dart test`（`PYTHON`/`OPENAPI_VALIDATOR` 已注入） | `+85: All tests passed!` |
| 4 | reading-notes | `flutter analyze`；`flutter test` | `No issues found!`；`+332: All tests passed!` |

既有失败（**不得修复、不得新增**）：`tests/test_config.py::test_集合名与_ts_逐项一致`、`tests/test_registration.py::test_全部_callable_已在入口注册`、`tests/test_registration.py::test_三个_trigger_已注册`、`tests/test_registration.py::test_与_入口总数对齐`、`tests/test_registration.py::test_没有多余的未声明导出`。

计数推导：SERVER `568 + 26 = 594` passed？**否**——pytest 既有 568 已含 NC-009/011/012a/013 的测试；本任务新增 26 个用例后按 ACT 分两步观察（act/02 后 `5 failed, 578 passed, 3 xfailed`＝568+10；act/03 后 `5 failed, 594 passed, 3 xfailed`＝568+26，3 xfailed 全部来自 E6 已转真的既有测试，本任务不新增 xfail）。REST `81 + 4 = 85`。CLIENT `314 + 18 = 332`（起草时基线 `+296`，NC-014 落地后升至 `+314`，见 D-NC026-26）。RULES `153 + 4 = 157`。

### 8.2 REST（act/01）—— `test/community_openapi_contract_test.dart` 末尾追加，名称逐字

```
analytics paths and methods match the catalog
analytics schemas are closed objects with pseudonym and batch bounds
analytics examples manifest has twenty two entries and validates
analytics rate limit and error rows are declared
```

另按 §10 授权改一处既有断言：`expectedCatalog` 追加两条：
`'/v1/analytics/events': {'post'},`、`'/v1/analytics/pseudonym': {'get'},`。

### 8.3 SERVER（act/02 + act/03）—— `tests/test_behavior_events.py`，名称 = `test_` + 下名

act/02（前 10 个，Schema 与信封）：

```
behavior_event_schema_is_closed_and_matches_frozen_copy
frozen_behavior_event_schema_sha256_matches_contract_literal
server_event_document_matches_frozen_schema_after_command
server_event_carries_object_type_and_object_id_per_operation_map
server_event_note_ref_is_null_and_platform_is_server
client_event_id_format_is_bev_prefixed_uuid_v4
attributes_allowlist_rejects_unknown_keys_per_event_type
private_note_event_requires_all_six_revision_attributes
private_note_event_rejects_server_only_attributes
behavior_event_examples_validate_two_valid_and_twenty_one_invalid
```

act/03（后 16 个，端点与假名）：

```
analytics_events_ingests_client_events_and_fills_received_at
analytics_events_is_idempotent_by_event_id_and_counts_duplicates
analytics_events_batch_over_500_is_413
analytics_events_rejects_server_event_type_on_client_endpoint
analytics_events_invalid_schema_reports_json_pointer
analytics_events_batch_splits_into_transactions_of_hundred
analytics_events_unauthenticated_is_401
analytics_events_rate_limit_row_matches_contract
analytics_events_does_not_touch_ledger_or_notifications
analytics_events_partial_failure_returns_503_and_retry_dedupes
pseudonym_endpoint_returns_stable_random_pseudonym
pseudonym_endpoint_creates_mapping_once_without_behavior_event
pseudonym_is_shared_between_command_and_client_event_paths
pseudonym_is_random_across_two_independent_projects
event_documents_never_contain_account_id
server_code_has_no_update_or_delete_on_behavior_events
```

`events` 逐条 `event_id` 去重、`accepted + duplicates == len(events)`、`note_ref` 字面量取自 §9 复算值；`pseudonym_is_random_across_two_independent_projects` 在**两个独立项目**（`demo-xuan-nc026-a` / `demo-xuan-nc026-b`）各建一次映射，断言两条假名不相等且都 ≠ `psn_` + SHA-256(scope)[:32]。

### 8.4 CLIENT（act/04）—— `test/analytics/private_note_metrics_test.dart`，名称逐字

```
revision_saved_emits_six_attribute_event
char_count_counts_code_points_not_utf16_or_bytes
session_ended_emits_duration_and_revision_count
event_id_is_bev_prefixed_uuid_v4
note_ref_is_sha256_of_pseudonym_and_note_id
raw_report_bytes_never_contain_note_id_title_body_or_attachment_name
pseudonym_is_fetched_once_and_cached
pseudonym_cache_is_cleared_on_account_switch
queue_keeps_events_when_flush_fails
queue_drops_oldest_beyond_ten_thousand
dropped_before_is_attached_to_next_report_only
dropped_before_absent_when_nothing_was_dropped
flush_sends_batches_of_at_most_five_hundred
flush_removes_only_acknowledged_events
flush_reports_failed_without_throwing
events_persist_across_store_restart
revision_saved_does_not_block_save_on_transport_failure
report_payload_has_no_extra_keys
```

## 9. Schema、参考值与复算

### 9.1 冻结 Schema（规格侧已落位）

`learn_system/openspec/schemas/community_behavior_event.schema.json` 已由本契约作者改写；SERVER 侧 `xuan/community/schemas/community_behavior_event.schema.json` 必须与它**逐字节相同**。

```
SCHEMA_SHA = f3467224ddafa5ff3ac2a43011521a5cc0b8acf6293244d632fa291c97451e42
```

（2026-09-13 用 `sha256sum` 对上述文件实算；`tests/test_community_validation.py` 的该字典项字面量改为此值。）

结构：外层 12 必填字段不变；新增 `$defs.eventType`（19 值闭集）、`$defs.platform`（7 值闭集）、`$defs.droppedBefore`（integer ≥ 1）、`$defs.attributesContentPublish`、`$defs.attributesReactionSet`、`$defs.attributesEmpty`、`$defs.attributesPrivateNoteRevisionSaved`、`$defs.attributesPrivateNoteSessionEnded`（后四者 `additionalProperties: false`）；顶层 `allOf` 5 条 `if/then` 按 `event_type` 分派 `attributes`，并对两个私人笔记事件强制 `object_type = object_id = null`、`note_ref` 为 hex64。

`openspec/schemas/verify_community.sh` 的 `exempt_pointers` 中 `community_behavior_event.schema.json#/properties/attributes` 一项**保留**：顶层 `properties.attributes` 仍是联合入口（`{"type":"object"}`），真正的封闭性在 `$defs` 与 `allOf` 分支，`verify_community.sh` 的 4(a) 检查对 `$defs` 下每个 object 已要求 `additionalProperties: false`（D-NC026-21）。

### 9.2 examples（learn_system/openspec/schemas/examples/）

| 文件 | 期望 |
|---|---|
| `community_behavior_event.valid.yaml`（服务端 `content.publish`） | 通过 |
| `community_behavior_event.private_note_revision_saved.valid.yaml` | 通过 |
| `community_behavior_event.invalid_unknown_field.yaml` | 拒绝（顶层未知字段） |
| `community_behavior_event.invalid_pseudonym_prefix.yaml` | 拒绝（actor_pseudonym 非 `psn_`） |
| `community_behavior_event.invalid_title.yaml` | 拒绝（标题） |
| `community_behavior_event.invalid_body.yaml` | 拒绝（正文） |
| `community_behavior_event.invalid_comment_text.yaml` | 拒绝（评论文本） |
| `community_behavior_event.invalid_change_summary.yaml` | 拒绝（修改说明） |
| `community_behavior_event.invalid_quote_selector.yaml` | 拒绝（原文引文与 selector） |
| `community_behavior_event.invalid_attachment_name_image.yaml` | 拒绝（附件文件名与图片） |
| `community_behavior_event.invalid_content_hash.yaml` | 拒绝（内容指纹） |
| `community_behavior_event.invalid_mention_target.yaml` | 拒绝（@ 的目标账号） |
| `community_behavior_event.invalid_note_id_and_binding.yaml` | 拒绝（私人笔记 note_id 原值与绑定目标） |
| `community_behavior_event.invalid_account_id.yaml` | 拒绝（account_id） |
| `community_behavior_event.invalid_token.yaml` | 拒绝（token） |
| `community_behavior_event.invalid_ip.yaml` | 拒绝（IP） |
| `community_behavior_event.invalid_device_fingerprint.yaml` | 拒绝（设备指纹） |
| `community_behavior_event.invalid_location.yaml` | 拒绝（精确位置） |
| `community_behavior_event.invalid_event_type.yaml` | 拒绝（event_type 非闭集） |
| `community_behavior_event.invalid_platform.yaml` | 拒绝（platform 非闭集） |
| `community_behavior_event.invalid_unknown_attribute.yaml` | 拒绝（attributes 未知键） |
| `community_behavior_event.invalid_private_note_missing_attribute.yaml` | 拒绝（私人笔记缺必填成员） |
| `community_behavior_event.invalid_private_note_wrong_attribute.yaml` | 拒绝（私人笔记带服务端专用键） |

即 2 正 21 负（2026-09-13 用 `check-jsonschema` 实跑：2 PASS / 21 拒绝）。

### 9.3 参考值（全部用真实代码复算后写死，测试内禁止现算）

服务端事件 ID（`ids.server_event_id`，`E` = `community_hash.encode`）：

| owner_scope | command_id | event_type | 期望字面量 |
|---|---|---|---|
| `acct_bev_demo` | `cmd_00000000000040008000000000000000` | `content.publish` | `bev_7238cb94b108c5479b32e4259ed4e147` |
| `acct_bev_demo` | `cmd_00000000000040008000000000000000` | `reaction.set` | `bev_35a1484fbe53c4b9c5c5f0ab19508dc2` |
| `acct_bev_demo` | `cmd_00000000000040008000000000000000` | `comment.create` | `bev_0cf02e53b9c67b679b53567c01484371` |

`note_ref`（`SHA256_hex(UTF8(actor_pseudonym + "/" + note_id))`），输入 `psn_0123456789abcdef0123456789abcdef` 与 `note_0123456789abcdef0123456789abcdef`：

```
2be56a4060534a55fda8d1767be56a551743236f617bfec52d4f0178fff80673
```

所有字面量禁止在测试内由公式现算（`community_hash` / `hashlib` / `sha256` 在断言路径上不得出现）；测试只能引用上表常量。

## 10. REST §14 补丁内容（`community_api.md` §14；`openapi.yaml` 落地）

- W17 `POST /v1/analytics/events`：非命令写（无 `Idempotency-Key`、不进命令账本、不写行为事件）；200 `AnalyticsEventsAccepted`。
- R11 `GET /v1/analytics/pseudonym`：200 `ActorPseudonym`。
- 新 Schema：`AnalyticsEventRequest`、`AnalyticsEventBatch`、`AnalyticsEventsAccepted`、`ActorPseudonym`（全部 `additionalProperties: false`；可空字段用 3.1 类型数组）。
- 错误行（§4.1 增补）：400 `invalid_argument.events` / `invalid_argument.event_type`；413 `too_large.events`（`limit` 500）。
- 限流（§6 表追加）：`analytics.events` 60/分钟；`GET /analytics/pseudonym` 并入读端点 600。
- 示例：`analytics_events_batch.json`、`analytics_pseudonym.json`；`manifest.json` 20 → 22 项；NC-013 的 twenty 测试断言改为 `greaterThanOrEqualTo(20)`（D-NC026-22）。
- 串行链：`REST/openapi/openapi.yaml` 顺序 `NC-003 → NC-013 → NC-021 → NC-026`，NC-021 处于 `BLOCKED`，NC-026 取下一棒（D-NC026-23）。

## 11. 可观测性与不变量

- 不变量：`community_behavior_events` 只增不改；`actor_pseudonym` 一账号一值且随机；事件任意字段不等于 `owner_scope`/`app_version` 之外不含任何账号标识；私人笔记上报字节不含内容。
- 可观测性断言（`caplog`）：`analytics_events.py` 与 `community/behavior_events.py` 的日志不含事件 `attributes` 值、`note_ref`、`event_id`、账号标识，只记计数与错误类名（沿用 D-NC009-19 口径：不记 `{exc}` / `str(exc)` / `exc_info`）。
- 拒收计数写 `community_analytics_rejections`，不落事件表。

## 12. 现状取证（2026-09-13，仓/文件:行）

### 12.1 服务端事件已由 NC-009 事务内写入

- `xuan-server/functions-py/xuan/community/command_service.py:177-197`（`run_command` 的 `_tx_step` committed 分支）：先读/建 `community_pseudonym_mappings/{owner_scope}`（`:156-162`、`:178-185`），再以 `ids.server_event_id(...)` 为文档 ID 写事件（`:187-197`）。当前**只写 6 个字段**：`event_id`、`event_type`、`actor_pseudonym`、`occurred_at`、`schema_version`、`attributes`。
- `xuan-server/functions-py/xuan/community/ids.py:51-55`：`server_event_id` = `"bev_" + sha256(community_hash.encode([owner_scope, command_id, event_type])).hexdigest()[:32]`。
- 落事件的 operation（14 个可达）：`content.publish/update/withdraw/trash/restore/purge`（`xuan/handlers/community_contents.py:97,112,127,142,157,226`）、`comment.create/edit/delete`（`community_comments.py:102,126,143`）、`reaction.set`（`community_interactions.py:127`）、`bookmark.set`（`:182`）、`share.create`（`:217`）、`share.revoke`（`:249`）、`report.create`（`:279`）。`backup.begin/complete/delete` 无端点、不产生事件。
- `attributes` 唯一非空的 producer：`xuan/community/content_service.py:288` = `{"is_republish": is_republish}`；其余 13 处为 `{}` 或缺失（`command_service.py:189` 用 `outcome.body.get("attributes", {})` 兜底）。

### 12.2 attributes 候选全集

`content_service.py:288`（`is_republish`）、其余 operation 无字段；DESIGN §11.4 另点名 `image_count`、`reaction.set` 的 `value`/`previous_value`。`tests/test_community_interactions.py:149` 断言 `reaction.set` 的 `attributes == {}`，`tests/test_community_comments.py:164` 断言 `comment.create` 的 `attributes == {}`。

### 12.3 私人保存链路（只读取证，不动代码）

- `xuan/reading-notes/lib/src/persistence/note_repository.dart:159` `saveSnapshot({noteId, snapshot, summaryTouched, expectedHeadId})` → 返回 `SaveResult(noteId, revisionId, outcome, contentHash)`（`SaveOutcome.unchanged` 时 `revisionId == null`）；写修订并插 outbox `op: 'revision_saved'`（`:241`）。
- `:271` `restoreRevision({noteId, sourceRevisionId})`（`is_restore` 来源）、`:367` `mergeHeads(...)`（`is_merge` 来源）。
- 会话边界：`lib/src/editor/note_editor_controller.dart:289` `dispose()`（`EditSession` 起止的现有挂点），`lib/src/editor/note_editor_page.dart:186-194` 页面 `dispose`。
- 会话内可用计数：`EditorSnapshot.text`（`lib/src/domain/editor_snapshot.dart`）、`attachmentRefs`、`mentionRefs`、`bindings`；`lib/src/domain/limits.dart` 提供既有上限常量。
- 现状**无** `lib/src/analytics/` 目录，无任何上报链路。

### 12.4 只追加现状

- `xuan-server/xuan-server/server/firestore.rules` 顶层默认拒绝（NC-009 §2.2 口径：八个社区集合不新增 match）；`grep community server/firestore.rules` 零命中。
- `server/functions/test/community_rules.test.ts:25-45` `COMMUNITY_COLLECTIONS` 19 项 × 2 上下文 × 4 操作 + 1 回归 = 153。

## 13. 已知缺口、DEFERRED 与待裁决

| 项 | 处置 |
|---|---|
| 注销（宿主注销 / 本人彻底删除账号）：删 `PseudonymMapping`、本系统业务数据去标识化、事件保留 | **DEFERRED（D-NC026-13）**。事件来源取自 NC-001 第⑩项，`SUBAGENT_TODO.md` NC-001 总项仍为 `PREPARING`、第⑩项证据缺失；缺证时不派发该子项。注销子项解锁条件：NC-001 第⑩项登记完成（来源、送达语义、测试方式）。 |
| `content.publish.image_count` 与 `reaction.set.{value, previous_value}` 的 producer 填充 | **已裁定不采纳（D-NC026-08 / D-NC026-29）**：需改 NC-009/NC-012a 已验收文件，且 `tests/test_community_interactions.py:149` 断言 `attributes == {}`；成本与回归面不成比例。本任务只冻结 Schema 允许集（这些键**合法但非必填**），不填充，登记为后续扩展候选。 |
| 私人笔记上报的默认开启/关闭开关（PRD 要求「默认上报」并写入隐私政策） | **已裁定不采纳（D-NC026-30）**：属 PRD 产品决策与宿主 UI 范围，本任务只保证默认开启的上报链路与字段白名单；开关 UI 与隐私政策文本归属留给宿主后续任务。 |
| 设备归属校验、宿主平台枚举实值 | 由宿主注入，本任务取闭集常量；宿主实值核实归 NC-001（E-WIRING）。 |
| `verify_community.sh` 在 Windows 不可运行（`.venv/bin`、`file:///d/...` base-uri） | **已知缺口**：本任务不动 NC-002 的脚本（D-NC026-21），守卫改用 `.venv/Scripts/check-jsonschema.exe` + `file:///D:/...` 直接校验（§14 K04）。 |
| 假名交付通道（R11）是 DESIGN 未定义的新增端点 | **已裁定采纳（D-NC026-07 / D-NC026-31）**：客户端无法自行生成合规假名（不得由账号 ID 推导），必须由服务端交付；已落 `GET /v1/analytics/pseudonym` 与四个测试名。 |
| `event_id` 前缀歧义（DESIGN §11.2 措辞） | **已裁定（D-NC026-06 / D-NC026-32）**：统一 `bev_` + UUIDv4 hex，服务端与客户端同构。 |
| 四查独立性（作者即主 Agent，无第三方审查者） | **已裁定豁免（D-NC026-28）**：由用户显式授权替代；`reviews/NC-026-REVIEW-R1.md` 降级为作者自查 + 冲突利益披露，如实标注独立性不满足。 |

## 14. 主 Agent 盲测清单（验收用，临时文件不入库，结束删除并以四仓 `git status --short` 为空证明）

1. 用 `command_service.run_command` 真跑一次 `content.publish`，把事件文档与冻结 Schema 做真校验（不是字段扫）。
2. 单独复算 §9.3 三组 `bev_` 与 `note_ref` 字面量（Python 独立进程，不经被测代码）。
3. 上报端点：同批 3 条含 1 条重复 → `accepted=2, duplicates=1`，事件表恰 2 条。
4. 501 条批次 → 413 `too_large.events`；非 2 值 `event_type` → 400；非法 `attributes` → 400 且 `field` 指向正确 JSON Pointer。
5. 两独立项目假名不相等，且 `psn_` ≠ `psn_`+SHA-256(scope)[:32]。
6. 客户端队列 10001 条 → 丢弃 1 条、下一条带 `dropped_before: 1`；重启 Store 后 `pendingCount` 不变。
7. 断言上报请求原始字节不含 fixture 的 `note_id` / 标题 / 正文片段 / 附件名。
8. 作弊扫描：无 `skip`、无新增 `xfail`、无永真断言、无测试内现算参考值、无真实外部网络；`exactly-once` 在三仓新增文件中零命中。

## 15. 决定登记（主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC026-01 | 服务端事件补齐 DESIGN §11.2 的六个缺失外层字段；`received_at == occurred_at`、`note_ref = null`、`platform = "server"`、`app_version = SERVER_APP_VERSION("0.0.0")` | 冻结 Schema 要求 12 必填；现状只写 6 个，是 NC-009 交付的隐性缺口（§12.1）；服务端事件无宿主，`server` 是其自身的平台枚举值 |
| D-NC026-02 | `attributes` 冻结为「按 event_type 的封闭允许集 + 成员可选」，不改任何既有 producer | DESIGN §11.4 的 attributes 描述用「例如」，且改 producer 会弄红 NC-012a 已验收断言；允许集已按 DESIGN 点名维度覆盖 |
| D-NC026-03 | `event_type` 19 值闭集、`platform` 7 值闭集 | DESIGN §11.2「§11.4 目录中的封闭字符串」；宿主平台枚举 DESIGN 未给，取 Flutter 六平台 + `server` |
| D-NC026-04 | 两个私人笔记事件的 attributes 成员**必填** | DESIGN §11.4 对这两个事件给的是完整对象（非「例如」） |
| D-NC026-05 | 私人笔记事件强制 `object_type = object_id = null`、`note_ref` 为 hex64；服务端事件强制 `note_ref = null` | DESIGN §11.2 逐字 |
| D-NC026-06 | 客户端事件 `event_id` = `bev_` + UUIDv4 去连字符 32 位小写 hex | DESIGN §11.2 该行措辞有歧义（「`bev_<32 hex>`」与「UUIDv4 去连字符后的 32 位小写 hex」），取与已冻结 NC-002 Schema（`behaviorEventId = ^bev_[0-9a-f]{32}$`）和 §2.1 前缀表一致的一读；登记供四查复核 |
| D-NC026-07 | 新增 R11 `GET /v1/analytics/pseudonym` 交付 `actor_pseudonym` | DESIGN §11.2 的 `note_ref` 公式要求客户端持有假名，而 §11.3 把映射限定为服务端；DESIGN 未定义交付通道，不补则 `note_ref` 无法在不泄漏 note_id 的前提下构造 |
| D-NC026-08 | 不填充 `content.publish.image_count` 与 `reaction.set.{value, previous_value}`（Schema 只允许不强制） | 需改 NC-009/NC-012a 已验收文件与断言；列入 §13 待裁决 P1 |
| D-NC026-09 | 上报端点是非命令写：无 `Idempotency-Key`、不进命令账本、不产行为事件；17 操作枚举不变 | 上报是遥测，不是社区业务命令；避免把客户端遥测污染防重复执行账本 |
| D-NC026-10 | 只追加靠顶层默认拒绝 + 4 条显式规则用例，`firestore.rules` 零改动 | DESIGN §11.5 只要求「禁止 update 与 delete」，默认拒绝已覆盖；不复活逐集合 match |
| D-NC026-11 | 队列上限 10000、超限丢最旧、`dropped_before`（integer ≥ 1，可选，仅客户端事件）只挂在下一条上报事件上 | DESIGN §11.4 逐字 |
| D-NC026-12 | 上报语义 at-least-once；服务端只按 `event_id` create-if-absent 去重 | DESIGN §11.4 只承诺「服务端按 event_id 去重」；不声称端到端 exactly-once |
| D-NC026-13 | 注销子项 DEFERRED | NC-001 第⑩项（宿主注销事件来源/送达语义/测试方式）证据缺失；TASKS NC-026 明示缺证时该子项 BLOCKED、其余继续 |
| D-NC026-14 | 私人笔记事件不进命令账本、不写 outbox、不产生通知 | 私人域数据按 DESIGN §4.3 只经本地与设备同步，遥测不触发公共链路 |
| D-NC026-15 | 参考值与 Schema SHA 必须字面量写死，测试内禁止现算 | 沿用 NC-009/NC-013 口径；§9.3 三组字面量与 §9.1 SHA 均为 2026-09-13 实机复算 |
| D-NC026-16 | 新增集合 `community_analytics_rejections` 只记拒收计数与时间 | §5.4 可观测性需要计数，同时不得把被拒事件内容落盘 |
| D-NC026-17 | 假名生成沿用既有 `ids.new_id("psn_")`（`uuid4().hex`），不改为 `secrets.token_hex(16)` | DESIGN §11.3 要求「密码学安全随机」且「禁止由账号 ID 推导」；`uuid4` 由 `os.urandom` 播种已满足，改动既有已验证路径无收益、徒增回归面（测试只断言随机性与稳定性） |
| D-NC026-18 | 服务端原样采用客户端 `note_ref`，不重算 | 服务端拿不到 note_id（上报字节不含它），重算不可能；这是刻意的信任边界，分析师侧只做聚合不做反查 |
| D-NC026-19 | 客户端与服务端事件共用同一集合与同一 `bev_` ID 空间 | DESIGN §11.2 只定义一套集合与一套前缀；SHA256 与 UUIDv4 派生空间碰撞概率可忽略 |
| D-NC026-20 | 客户端队列用注入式 `PrivateNoteMetricsStore` + 文件实现，不新建 Drift 表 | 新建 Drift 表要改 NC-004 已验收的 `note_database.dart` 与其 schema 版本；注入式端口使测试可用真实临时文件且零侵入 |
| D-NC026-21 | 不修改 `openspec/schemas/verify_community.sh` 的 `exempt_pointers` | 顶层 `properties.attributes` 仍是联合入口语义，封闭性由其下 `$defs` 承载；改动 NC-002 已验收脚本无必要 |
| D-NC026-22 | REST 示例清单 20 → 22 项；NC-013 的 twenty 断言改 `greaterThanOrEqualTo(20)` | 沿用 D-NC013-10 的「不锁死清单条数」口径 |
| D-NC026-23 | `REST/openapi/openapi.yaml` 串行链 NC-026 取 NC-021 之后的下一棒；`SERVER/xuan/config.py`、`SERVER/main.py` 的串行链（PLANS §1.2）同步追加 NC-026 槽位 | NC-021 处于 `BLOCKED`，不阻断；`main.py` 注册影响面已核实为安全（`tests/test_main_exports.py` 只断言 9 个既有 callable 存在与 3 个废弃导入不存在） |
| D-NC026-24 | 假名派生纯层单列 `SERVER/xuan/community/pseudonyms.py`，随 act/02 落地 | `command_service.py` 补事件字段需引用其常量（`PSN_PREFIX`/`SERVER_PLATFORM`）与复用 `ensure_pseudonym`，若纯层延到 act/03 会让 act/02 的补字段改动无宿主 |
| D-NC026-25 | 行为事件纯层与 Schema 校验单列 `SERVER/xuan/community/behavior_events.py`，随 act/02 落地 | 与 D-NC026-24 同因：act/02 的 Schema 封闭化与示例校验需要纯层先行，act/03 的端点只做 HTTP/权限/事务编排 |
| D-NC026-26 | CLIENT 基线因 NC-014 落地由 `+296` 升至 `+314`；契约、六件套与守卫的 CLIENT 基线、保护路径 diff 基准与期望计数同步更新（`107ec90` → `19afe37`，`+314` → `+332`） | NC-026 起草早于 NC-014 落地；`nc026_guard.sh` K08 的 `pubspec.yaml` 保护断言若仍以 `107ec90` 为基准会被 NC-014 的合法 pubspec 改动误判（与 nc014_guard.sh K06 同类修严） |
| D-NC026-27 | SERVER 线 act/02 与 act/03 由主 Agent 在同一会话实现、合并为**单提交**；范围证据取 `992088e..HEAD` 恰 10 文件；`pseudonyms.py`/`behavior_events.py` 两个纯层归 act/02（见 D-NC026-24/25） | ACCEPTANCE §2 的 SERVER 范围本定义为「`992088e..HEAD` 恰 10 文件」的区间口径、而非按 act 切分提交；act/03 测试文件头部共用导入（`analytics_events_py`）使部分暂存切分无收益、徒增回归面 |
| D-NC026-28 | 四查独立性**豁免**：NC-026 无「未参与编写且异厂商」的第三方审查者，`reviews/NC-026-REVIEW-R1.md` 降级为作者自查 + 冲突利益披露 | 用户显式授权同一会话全权接任主 Agent 并端到端完成 NC-026；契约与 `HANDOFF` §7.2 要求无法在单会话下同时满足，如实登记而非假装合规 |
| D-NC026-29 | P1 不采纳：不填充 `image_count`/`reaction.set.{value,previous_value}` | 见 §13；需改 NC-009/NC-012a 已验收文件与 `tests/test_community_interactions.py:149` 的 `attributes == {}` 断言 |
| D-NC026-30 | P2 不采纳：上报开关 UI 与隐私政策文本不归本任务 | 属 PRD 产品决策与宿主 UI 范围；本任务只落数据链路与字段白名单 |
| D-NC026-31 | P3 采纳：保留 `GET /v1/analytics/pseudonym` | 客户端不得由账号 ID 推导假名，服务端交付是唯一合规路径（D-NC026-07 的复核结论） |
| D-NC026-32 | P4 解读维持：`event_id` 统一 `bev_` + UUIDv4 hex | DESIGN §11.2 措辞未区分两模式；统一为 `bev_` 前缀与既有 `ids.server_event_id` 同构，避免双格式分支 |
