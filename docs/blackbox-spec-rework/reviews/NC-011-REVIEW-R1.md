# NC-011 契约与六件套 wjt-react 四查审查报告（R1）

审查日期：2026-09-12  
审查对象：NC-011（两级评论与讨论区）契约与六件套  
审查者：转译审查员（wjt-react 四查，单线只读审查）  
审查判定：**READY**（R1 判定返工 4 项，经 R2 复核全部关闭达标）

---

## 目录

1. [一查：忠实性审查（Faithfulness）](#1-一查忠实性审查faithfulness)
2. [二查：覆盖性审查（Coverage）](#2-二查覆盖性审查coverage)
3. [三查：可执行性审查（Actionability）](#3-三查可执行性审查actionability)
4. [四查：独立性审查（Independence）](#4-四查独立性审查independence)
5. [返工项清单（按严重程度排序）](#5-返工项清单按严重程度排序)
6. [建议清单（非阻断）](#6-建议清单非阻断)
7. [待裁决事项](#7-待裁决事项)
8. [R2 复核（2026-09-12）](#8-r2-复核2026-09-12)

---

## 1. 一查：忠实性审查（Faithfulness）

### 1.1 TASKS 溯源核对
每个 ACT 均可清晰追溯至上游计划与任务定义，无凭空新增，无遗漏任务：
- **act/01 (REST)**：承接 OpenAPI 3.1.0 契约增量（R2 的 `root_id`/`order`、`CommentPage` 的 `reply_previews` 与两计数、W7 的 409 `oneOf` 复合组件），对应 [community_api.md §11](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/community_api.md#L275-L296)。
- **act/02 (SERVER W7)**：承接评论创建事务、主题与作者计数、mentions 过滤、Schema 校验，对应 [TASKS.md NC-011](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L180-L184)。
- **act/03 (SERVER W8/W9/R2)**：承接评论编辑、删除墓碑保留回复、一级倒序/正序与楼内正序分页、稳定游标与 ETag，对应 [TASKS.md NC-011](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L180-L185)。
- **act/04 (SERVER 并发与 RULES)**：承接 R2-05 受控并发屏障测试（withdraw 先提交、comment 先提交、三方竞争、回调重跑新 ID 固定）以及安全规则 89 项断言，对应 [TASKS.md NC-009 R2-05](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L161) 与 [TASKS.md NC-011](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L188)。
- **act/05 (CLIENT 基础)**：承接评论模型、API 方法、Drift 持久队列接入（RW-5 三项断言与离线重启）、评论计数端口，对应 [TASKS.md NC-010 RW-5](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L168) 与 [TASKS.md NC-011](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L180-L181)。
- **act/06 (CLIENT 讨论区)**：承接控制器、面板、滚动保持、两种空态、七状态必答矩阵，对应 [TASKS.md NC-011](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L180-L185)。

### 1.2 契约一致性与上游冲突清单
- **签名与字段一致性**：
  - `community_discussion.md` 中的 `Comment`、`CommentRevision`、`Thread` 结构与 `community-models.md §2.4` 严格吻合。
  - HTTP 端点、状态码、Problem Details `code` 字段与 `community_api.md §11` 及 `DESIGN.md §7.3` 目录一致。
  - 服务端 `run_command` 事务语义与 `community_server.md §3、§10` 规则一致。
  - 客户端 payload_hash 规范化算法与 `community_client.md §10` 严格一致。
- **与上游冲突/演化决议登记**：
  1. **D-NC011-05**：替代 D-NC003-07 的 ETag 定义。原设计仅取末条评论键，无法反映评论编辑与删除，且无法区分分页参数差异。现演进为 `"<ContentAccess.version>:<h>"`，包含 `thread_version` 与各查询参数哈希截断。
  2. **D-NC011-07**：mention 超额错误码统一。原 `DESIGN.md` 第 303 行表格写 `400`，但 `community_api.md §4.1` 错误目录与 NC-009 §10.1 均冻结为 `413 too_large.mentions`（limit=50）。契约与 DESIGN 第 303 行已同步对齐为 413。
  3. **D-NC011-18**：W7 409 响应组件扩展。原组件强制包含 `current_access_version`，但同键异载荷触发的幂等冲突（`conflict.idempotency`）不含该字段，故扩展为 `oneOf` 复合响应。

---

## 2. 二查：覆盖性审查（Coverage）

对 [TASKS.md](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md) NC-011 及关联任务（NC-009 R2-05、NC-010 RW-5）的验收要求进行逐项矩阵对照：

| 验收要求项 | 覆盖的 ACT 与测试 ID | 断言与边界覆盖说明 | 判定 |
|---|---|---|---|
| **RW-5 ①：真实文件库关闭重开后以原键重试** | act/05 (`K06`) | 模拟网络首发 `SocketException`，真实关闭 Drift 数据库文件句柄并重新打开，验证新队列重试保持相同 `Idempotency-Key`。非 happy path。 | PASS |
| **RW-5 ②：响应丢失后调用端点对账** | act/05 (`K07`) | 假服务器已入库，客户端本地状态置为 `sending` 并关库重开；恢复时先 `GET /commands/{id}` 对账得 committed，不再发送重复 POST。 | PASS |
| **RW-5 ③：410/503 不换键重放** | act/05 (`K08`) | 503 保持原键重试；410 标记 rejected 且不调用内容层 `onGone410`。全程 key 唯一。 | PASS |
| **离线重启并在服务端确认后标记消除** | act/06 (`K14`) | 离线发评入库，面板与待处理队列出现「待发送」；关库重开后新控制器保持该标记；联网 drain 后服务端仅写 1 次，两处标记同时清除。 | PASS |
| **R2-05 ①：withdraw 先提交，评论重跑** | act/04 (`T31`) | 受控屏障强制 withdraw 先提交，评论事务回调重跑，断言 404 `not_found.content`、零评论/事件、hook 触发恰 2 次。 | PASS |
| **R2-05 ②：comment 先提交，收回隐藏** | act/04 (`T32`) | 受控屏障强制 comment 先提交，评论 201 成功，随后收回 200 并隐藏主题；非作者 R2 404，作者 R2 仍可见评论。 | PASS |
| **R2-05 ③：三方竞争（2 评论 + 1 收回）** | act/04 (`T33`) | `threading.Barrier(3)` 连续 3 轮并发竞争，断言评论/事件/计数与 201 个数严格等价不变式。 | PASS |
| **R2-05 ④：回调重跑新 ID 固定** | act/04 (`T34`) | 事务竞争重跑下，断言重跑前后的 `comment_id`、`comment_revision_id` 保持不变，无多余幽灵对象。 | PASS |
| **仍可读旧版本（作者视角）** | act/03 (`T30`), act/04 (`T32`) | 内容收回后，非作者 404，作者本人调用 R2 仍返回 200 且包含全部历史评论。 | PASS |
| **迟到评论成功不恢复公开 UI** | act/06 (`K17`) | 评论发送返回 201，但后续 R2 探测主题已收回（404），面板展示「内容已不可见」，不恢复公开列表展示。 | PASS |
| **两种讨论区空态** | act/06 (`K13`, `K20`) | 区分已公开空态（「还没有人评论，来写第一条」，输入可用）与已收回/已关闭空态（「该内容不接受新评论」，输入禁用）。 | PASS |
| **评论正文 4000/4001 code points 成对边界** | act/02 (`T11`), act/06 (`K15`) | 服务端 T11：4000 个 4 字节 emoji (`\U0001F600`) 返回 201，4001 个返回 413 `too_large.comment_body`；客户端 K15 对应 1 行入队 vs 0 行入队拦截。 | PASS |
| **删除一级评论墓碑与禁止新回复** | act/02 (`T09`), act/03 (`T24`), act/06 (`K18`) | W9 删除 root 返回 200，`current_revision` 置 null；R2 仍展示已删除墓碑且已有楼内回复仍展示；针对该 root 的新回复直接拒绝（403 `forbidden.thread_closed`）。 | PASS |
| **跨 thread/root 拒绝** | act/02 (`T07`, `T08`) | 目标 root/reply 属于不同主题或 root_id 指向 depth 1 均返回 404 `not_found.comment`。 | PASS |
| **楼内回复保持 depth 1** | act/02 (`T04`, `T05`) | 回复 root 或回复楼内 reply 均锁定 depth 1，保持两级结构不无限嵌套。 | PASS |
| **排序 tie-break UTF-8 字节序** | act/03 (`T27`) | 相同 `created_at` 下，按评论 ID 的 ASCII/UTF-8 字节序升序排序，newest 与 oldest 精准相反。 | PASS |
| **日志脱敏不含评论正文** | act/04 (`T35`) | caplog 断言覆写 W7/W8/W9/R2/403/409，正文任意 20 字片段不出现在日志。 | PASS |

覆盖性审查结论：**全面覆盖，无漏网项**。

---

## 3. 三查：可执行性审查（Actionability）

### 3.1 路径与代码符号真实性核验
逐一核查执行者依赖的代码路径与符号，全部验证存在：
1. `resolve_access` 签名：
   - 路径：`xuan-server/functions-py/xuan/community/access.py:39-44`
   - 签名：`def resolve_access(content_id: str, viewer_scope: Optional[str], client: Any = None, tx: Optional[gcf.Transaction] = None) -> tuple[str, Optional[dict[str, Any]]]`
   - 核验：存在。返回 `(kind, access_dict)`，符合契约 §5.1。
2. `build_command_context` 与 `extra_new_ids`：
   - 路径：`xuan-server/functions-py/xuan/community/command_service.py:56-65`
   - 核验：参数 `extra_new_ids: Optional[dict] = None` 存在且合并至 `new_ids`。
3. `run_command` 对 `outcome.body` 与 `attributes` 的处理：
   - 路径：`xuan-server/functions-py/xuan/community/command_service.py:189, 272-273`
   - 核验：`outcome.body` 会被放入 HTTP 响应，且其 `attributes` 会成为事件属性。契约 D-NC011-12 明确要求 `outcome.body` 不含 `attributes`，从而保证响应体仅含 `comment` 与 `command`，设计吻合。
4. `validation.py` 的 `_REGISTRY`：
   - 路径：`xuan-server/functions-py/xuan/community/validation.py:24`
   - 核验：`_REGISTRY = _build_registry()` 存在。
5. `community_contents.py` 的工具函数：
   - 路径：`xuan-server/functions-py/xuan/handlers/community_contents.py:25, 295`
   - 核验：`_parse_if_match` 与 `_make_response` 均存在。
6. `playground_rest.py` 的 `_extract_auth_uid`：
   - 路径：`xuan-server/functions-py/xuan/handlers/playground_rest.py:689`
   - 核验：存在。
7. 客户端核心符号：
   - `CommandQueue.computePayloadHash`：`reading-notes/lib/src/community/command_queue.dart:74`（存在）
   - `ContentAccessPublic.version`：`reading-notes/lib/src/community/models.dart:33`（存在）
   - `PendingOpConflict`：`reading-notes/lib/src/community/command_queue.dart:108`（存在）
   - `onGone410`：`reading-notes/lib/src/community/command_queue.dart:62`（存在）
   - `ConfirmationDialogs.withdrawMessage`：`reading-notes/lib/src/community/confirmation_dialogs.dart:7`（存在）

### 3.2 工具链与测试计数一致性
- 工具链可用性：
  - `functions-py/.venv/bin/python`：可用（Python 3.14）
  - `/Users/jingtaiwei/flutter/bin/flutter` 与 `dart`：可用
  - `npm`：可用（`/opt/homebrew/bin/npm`）
  - `repository-rest-adapter/tool/validate_openapi`：可用（可执行脚本）
  - `learn_system/.venv/bin/python`：可用
- 测试计数一致性：
  - **REST**：基线 `+69` -> act/01 `+73: All tests passed!`（单文件 19 -> 23）。契约、TDD、act/01、守卫脚本严格一致。
  - **SERVER**：基线 `459 passed, 5 failed, 9 xfailed`。
    - act/02：+20 passed（T01~T18 共 18 个测试名，T14 参数化 3 例，增量恰为 20）-> `479 passed`。
    - act/03：+12 passed（T19~T30）-> `491 passed`。
    - act/04：+5 passed（T31~T35）-> `496 passed`。RULES 65 -> `89 passed`。
    契约 §9.2、README、TDD §1、act/02~04、守卫脚本严格一致。
  - **CLIENT**：基线 `+214`。
    - act/05：+10 passed（K01~K10）-> `+224: All tests passed!`。
    - act/06：+15 passed（K11~K25，含七状态 7 例）-> `+239: All tests passed!`。
    契约 §12、README、TDD §1、act/05~06、守卫脚本严格一致。
  - 守卫脚本验证：在 learn_system 根目录运行 `bash docs/blackbox-spec-rework/reviews/nc011_guard.sh` 结果为 `PASS K01~K04`，退出码为 0。

### 3.3 无模糊词核验
对契约与六件套执行敏感模糊词检索（`适当|优雅|合理|必要时|酌情|尽量|大致|视情况`）：
检索结果为空，全套文档未出现任何违禁模糊词。

### 3.4 技术可行性深度诊断（发现的问题）
在逐行推演执行代码与测试时，发现以下技术风险与潜在缺陷：

1. **Firestore Python SDK `start_after` 字典入参陷阱（严重：阻断执行）**：
   - 契约 `community_discussion.md §6.4` 第 191 行写：`有游标时 start_after({"created_at": c, "id": i})`。
   - 证据与分析：在 Google Cloud Firestore Python SDK (`google-cloud-firestore`) 中，`base_query.py:1384` 的 `_cursor_pb` 实现为 `[_helpers.encode_value(value) for value in data]`。当 `data` 为字典时，Python 迭代字典产生的是 key（即字符串 `"created_at"` 和 `"id"`），而非字段的值！经 Python 3.14 实际测试验证：
     `_cursor_pb(({'created_at': '2026-09-11', 'id': 'cmt_1'}, False))` 生成的 protobuf 游标为：
     ```protobuf
     values { string_value: "created_at" }
     values { string_value: "id" }
     ```
     这会导致 Firestore 查询接收到无意义的字段名字符串作为游标，游标分页逻辑彻底失效！
   - 对比证据：同模块既有已验收代码 `xuan/handlers/community_contents.py:199` 采用的是列表传值：`query = query.start_after([cursor_updated_at, cursor_content_id])`。
   - 判定：阻断执行缺陷，必须返工修正。

2. **Flutter Widget 测试中 Element 保持在默认视口下的不可测性（严重：阻断执行）**：
   - 契约 `community_discussion.md §12` 第 383 行（K11）与 `BDD.md` 第 68 行要求：在点「加载更多评论」追加 20 条至 40 条后，「首批 20 个 ValueKey 仍在且为同一 Element」。
   - 证据与分析：Flutter widget 测试环境的默认虚拟视口尺寸为 800×600。当渲染 20 条评论时，列表高度将远远超出 600px。在未对 `ListView` 设置 `cacheExtent: double.infinity` 或未显式扩大测试 Viewport（如 `tester.view.physicalSize`）的情况下，超出屏幕视口的 Item 会被 Flutter 的视口渲染管道自动回收（deactivate/unmount）以释放内存。此时使用 `tester.element(find.byKey(ValueKey('comment-<id>')))` 查找视口外的已回收元素会直接抛出找不到 Widget 的异常，无法断言 `identical(elementBefore, elementAfter)`。
   - 判定：阻断执行缺陷，需在测试规则中补齐视口尺寸或 cacheExtent 规范。

3. **`DiscussionController.refreshPending()` 中 `ownerScope` 的获取途径歧义（两种解释）**：
   - 契约 `community_discussion.md §11.6` 第 330 行定义的构造函数：
     `DiscussionController({required CommunityApi api, required CommandQueue queue, required CommunityDatabase db, required String contentId, required Future<ContentAccessPublic?> Function(String contentId) accessLookup, required CommunityClock clock})`。
     参数中未包含 `ownerScope`。
   - 而第 342 行的判定规则要求：`读 db.communityCommands 中本 owner、operation 以 comment. 开头...`。
   - 证据与分析：执行者无法从自身属性直接获得 `ownerScope`，可能产生歧义：是修改构造函数传入 `ownerScope`（触碰契约签名），还是从 `queue.ownerScope` 取值（`command_queue.dart:61` 中其为 public 字段）？
   - 判定：歧义项，必须明确规范。

4. **`refreshPending()` 中 `committed → load()` 重复触发与死循环风险（两种解释）**：
   - 契约 `community_discussion.md §11.6` 第 342 行规定：`自上次调用以来变为 committed → load()`。
   - 证据与分析：若实现仅通过检查 `row.state == 'committed'`，当 `refreshPending()` 被连续调用（例如 `send` 之后调用、面板定时器或外部通知触发）时，已提交的行如果未在控制器内存中登记「已处理」，将导致每次调用都重复触发 `load()`，产生不必要的网络开销甚至死循环。
   - 判定：实现语义不明确，需补充去重集合规范。

---

## 4. 四查：独立性审查（Independence）

### 4.1 三线文件写入隔离性
三线划分在物理路径上绝对隔离，绝无交叉写同一文件：
- **REST 线 (act/01)**：独占 `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter`。
- **SERVER 线 (act/02~04)**：独占 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py` 与 `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server/server/functions/test/community_rules.test.ts`。
- **CLIENT 线 (act/05~06)**：独占 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`。
三线完全可以无锁并行开发。

### 4.2 依赖链条与前置条件
- `act/01 (REST)`：`DEPENDS_ON: []`。独立开工。
- `act/02 (SERVER)`：`DEPENDS_ON: []`。独立开工。
- `act/03 (SERVER)`：`DEPENDS_ON: [NC-011-B]`。严格依赖 act/02 提交。
- `act/04 (SERVER)`：`DEPENDS_ON: [NC-011-C]`。严格依赖 act/03 提交。
- `act/05 (CLIENT)`：`DEPENDS_ON: []`。独立开工。
- `act/06 (CLIENT)`：`DEPENDS_ON: [NC-011-E]`。严格依赖 act/05 提交。
依赖关系单向无环，严格串行。

### 4.3 跨步骤符号依赖
- act/03 使用的 `thread_id_for`、`comment_dto`、`after_access_read_hook` 均在 act/02 完整交付并注册。
- act/04 并发测试调用的 `run_command(cctx, discussion_service.comment_create)` 及 hook 变量在 act/02 已就位。
- act/06 使用的 `Comment`、`CommentPage`、`CommunityApi.listComments`、`ApiCommentCountPort` 均在 act/05 完整交付并导出。
无任何后一步越级使用未交付符号的违规情况。

---

## 5. 返工项清单（按严重程度排序）

### 返工项 1【阻断执行】
- **问题位置**：契约 `contracts/community_discussion.md §6.4`（第 191 行）
- **问题描述**：契约写 `有游标时 start_after({"created_at": c, "id": i})`。在 Google Cloud Firestore Python SDK 中，传入字典会被 `_cursor_pb` 迭代为键名字符串序列 `["created_at", "id"]`，导致查询接收到错误的游标值，分页必然失败。
- **修正标准**：将契约 §6.4 中的游标调用描述修正为 `start_after([c, i])`，与 `xuan/handlers/community_contents.py:199` 保持一致，明确必须按 `order_by` 字段顺序传入包含字段值的列表或元组。

### 返工项 2【阻断执行】
- **问题位置**：契约 `contracts/community_discussion.md §12`（第 383 行 K11）及 `work-items/nc-011/act/06.yaml`（RULES 与 ON_FAIL）
- **问题描述**：K11 要求在 Flutter widget 测试中断言「首批 20 个 ValueKey 仍在且为同一 Element」。在测试默认 800×600 视口下，20 条评论超出视口，非可见列表项会被 Flutter 视口机制自动卸载/回收，导致 `tester.element()` 抛出找不到 Widget 异常而无法断言 Element 保持。
- **修正标准**：在契约 §12 K11 说明及 act/06.yaml RULES 中补充规范：测试执行时需配置足够大的视口高度（如 `tester.view.physicalSize = const Size(800, 10000)` 并 `addTearDown(tester.view.resetPhysicalSize)`），或 `DiscussionPanel` 的 `ListView` 在测试时配置 `cacheExtent`，确保首批 20 个元素稳定保持在树上。

### 返工项 3【两种解释】
- **问题位置**：契约 `contracts/community_discussion.md §11.6`（第 330 行与 342 行）
- **问题描述**：`DiscussionController` 构造器未声明 `ownerScope` 参数，而 `refreshPending()` 规则要求「读 db.communityCommands 中本 owner...」，导致执行者对如何获取本账号 ownerScope 存在不同理解。
- **修正标准**：在契约 §11.6 明确说明：控制器内部通过 `queue.ownerScope` 获取当前账号的 `ownerScope`，禁止修改构造函数签名。

### 返工项 4【两种解释】
- **问题位置**：契约 `contracts/community_discussion.md §11.6`（第 342 行）
- **问题描述**：`refreshPending()` 规定「自上次调用以来变为 committed → load()」，缺乏明确的状态跃迁记忆机制，执行者易写成「凡是 committed 均触发 load()」，导致高频调用时无限循环触发网络刷新。
- **修正标准**：在契约 §11.6 明确补充实现规则：控制器需持有 `final Set<String> _processedCommittedCommandIds = {};`，仅当某行从非终态跃迁为 `committed` 且未在集合中时，才触发 `load()` 并将其加入集合。

---

## 6. 建议清单（非阻断）

1. **Firestore Emulator 锁与并发屏障监控**：
   - 契约 §8 中的受控屏障依赖 `wait(10)`。由于 Firestore Emulator 在单机多线程下的行锁行为与生产环境 Spanner/wound-wait 存在差异，执行者在 act/04 运行测试时应保持关注，若发生超时严格执行停手条件。
2. **`http.Client.delete` 严格保持无体**：
   - 客户端 `deleteComment` 必须使用 `client.delete(uri, headers: headers)`，切勿传递 `body` 参数，以防底层平台适配层（如某些浏览器或代理）丢弃请求头或拒收带有 body 的 DELETE。
3. **Draft 2020-12 校验器实例缓存**：
   - 服务端 `validation.py` 在追加 `COMMENT_CREATE_SCHEMA` 与 `COMMENT_EDIT_SCHEMA` 时，建议预编译 `Draft202012Validator` 为模块级单例常量，避免在每次写命令调用中重复编译 Schema。

---

## 7. 待裁决事项

无新增架构分歧。R1 提出的 4 项问题已在 R2 阶段全部按标准闭环，无遗留待裁决事项。

---

## 8. R2 复核（2026-09-12）

主 Agent 已针对 R1 审查报告指出的 4 项问题完成逐项修正。经对修改后的契约与六件套进行精准复核（对照代码与规格上下文）：

### 8.1 逐项复核结论

1. **返工项 1 复核（契约 §6.4 第 191 行）**：
   - 检查内容：契约已修改为 `有游标时 start_after([c, i])（按 order_by 字段顺序传值列表，与 handlers/community_contents.py 既有写法一致；禁止传字典，审查 R1 返工项 1）`。
   - 判定：**PASS**。彻底消除了 Google Cloud Firestore Python SDK 底层 `_cursor_pb` 将字典键作为游标字段名的阻断缺陷，与既有实现风格完全统一，无新歧义。

2. **返工项 2 复核（契约 §12 K11、BDD.md K11）**：
   - 检查内容：契约 §12 K11 修改为默认测试视口下先断言 `scrollController.position.maxScrollExtent > 0`，`jumpTo(maxScrollExtent)` 后记录 `pixels` 与 `tester.getTopLeft(find.byKey(ValueKey('comment-<第 20 条 id>')))`；追加后断言 `pixels` 与第 20 条的 `TopLeft` 均保持不变，明确注明「不断言屏幕外 Element，审查 R1 返工项 2」。BDD.md K11 同样对齐。
   - 判定：**PASS**。通过测试可测的滚动范围、滚动位置与处于视口底部的锚点 Item 相对坐标，严谨且可重复地证明了「加载更多时不跳动」，彻底规避了 Flutter Widget 视口自动回收机制导致的断言失败，无新歧义。

3. **返工项 3 复核（契约 §11.6 `refreshPending`）**：
   - 检查内容：契约 §11.6 明确写明「本 owner 取 `queue.ownerScope`（构造函数签名不变，审查 R1 返工项 3）」，并在查询中指定 `ownerScope == queue.ownerScope`。
   - 判定：**PASS**。在不改动已定构造函数签名和破坏既有外部调用的前提下，消除了执行者无法获取当前 `ownerScope` 的歧义，无新歧义。

4. **返工项 4 复核（契约 §11.6 `refreshPending`）**：
   - 检查内容：契约 §11.6 增加规范「控制器持有 `final Set<String> _trackedCommandIds = {}`。读 db.communityCommands... 非终态 → 加入 `_trackedCommandIds`... 仅对 `_trackedCommandIds` 中的行判定终态并随即移出集合... 本次有任一 committed → 调用一次 load()；cancelled → 只移出；rejected → 处理提示」。
   - 判定：**PASS**。精确定义了状态机跃迁的记忆跟踪集合，杜绝了多次调用 `refreshPending()` 时因历史 committed 行反复触发 `load()` 的死循环风险，批处理单次 `load()` 调用逻辑清晰明确，无新歧义。

### 8.2 守卫回归验证
在 learn_system 根目录运行 `bash docs/blackbox-spec-rework/reviews/nc011_guard.sh`：
输出 `K01~K04 全部 PASS，失败条数：0`。

### 8.3 最终判定
全部 4 项返工项均已达到修正标准，未引入任何新歧义，契约与六件套达到 wjt-react 四查基线要求，判定：**READY**。

---

审查结论确认行见对话结束输出。

