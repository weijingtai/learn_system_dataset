# NC-012a 契约与六件套 wjt-react 四查审查报告（R1）

- 审查对象：NC-012a（赞踩、收藏、分享、举报与 mention 文本校验）
- 审查日期：2026-09-12
- 审查角色：转译审查者
- 综合判定：**READY**（通过全部四查，返工 0 项，列 8 条非阻断实现建议与 2 项待裁决建议）

---

## 0. 规格守卫执行结果

在 `/Users/jingtaiwei/Git/Public/learn_system` 根目录执行规格级守卫：
```bash
bash docs/blackbox-spec-rework/reviews/nc012a_guard.sh
```
执行输出：
```text
PASS  K01 回归：v1.6 守卫与 verify.sh 均为 0
PASS  K02 契约：6 哈希 + ID/游标/ETag、27+26+4 测试名、M1～M8、文案、D-NC012-01～21、十五节；API §12
PASS  K03 六件套：BDD A01～A04/I01～I27/J01～J26、ACT 30–60 分钟、三线依赖链、ON_FAIL/WORKLOAD、无模糊词、计数与测试名
PASS  K04 SUBAGENT_TODO 已登记 NC-012a 工作包与契约
SKIP  K05 REST 产物（验收时 --require-impl rest，必须 PASS）
SKIP  K06 SERVER 产物（验收时 --require-impl server，必须 PASS）
SKIP  K07 CLIENT 产物（验收时 --require-impl client，必须 PASS）

NC-012a 失败条数：0
```
规格级检查 0 失败，全部前置断言通过。

---

## 1. 一查 忠实性（Faithfulness）

### 1.1 追溯性核对
六件套与专属契约中的每一项均严格追溯至原始意图：
1. **互动写命令（赞踩、收藏、分享、举报）**：
   - 追溯源：[`TASKS.md:190-199`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L190-L199) NC-012 整节、[`DESIGN.md:48-49`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/DESIGN.md#L48-L49) §2 领域模型、[`DESIGN.md:231-232`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/DESIGN.md#L231-L232) §6、[`DESIGN.md:281-282`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/DESIGN.md#L281-L282) §7 资源表、[`PRD.md:35-36`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/PRD.md#L35-L36) R-09/R-10。
   - 对应 ACT：REST act/01、SERVER act/02 与 act/03、CLIENT act/04 与 act/05。
2. **客户端命令恢复（RW-5 三项断言）**：
   - 追溯源：[`TASKS.md:168`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L168) NC-010 RW-5、[`TASKS.md:193`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L193) NC-012 指定复用命令队列并按 RW-5 验收。
   - 对应 ACT：CLIENT act/04（J05、J06、J07）。
3. **Mention 结构化三元组与纯文本子串校验**：
   - 追溯源：[`TASKS.md:194`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L194)、[`DESIGN.md:233`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/DESIGN.md#L233)。
   - 对应 ACT：CLIENT act/04（J09、J10、J11，`MentionRef` 统一与 `reconcileMentions`）。
4. **分享链接管理与撤销**：
   - 追溯源：[`TASKS.md:195`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L195)、[`PRD.md:223`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/PRD.md#L223) §6.6。
   - 对应 ACT：REST act/01、SERVER act/03、CLIENT act/05、act/06。
5. **举报受理确认与本地折叠**：
   - 追溯源：[`TASKS.md:195`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/TASKS.md#L195)、[`PRD.md:224`](file:///Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/PRD.md#L224) §6.6。
   - 对应 ACT：SERVER act/03、CLIENT act/05、act/06。

### 1.2 NC-012b 拆分合理性审查
- **拆分理由**：TASKS NC-012 明确要求「关系与互动的业务结果必须走实际宿主注入，不接受本地翻转/mock 关系」。由于宿主社交模块注入点依赖 NC-001-02 联调取证，目前处于 `BLOCKED` 状态。
- **是否漏掉本可立即交付的条目**：经核查，NC-012a 交付了所有无需宿主注入的闭环功能（纯数学/纯文本算法、全套互动命令与账本、独立存储与计数、端到端 UI 控制器与视图）。所拆出的 NC-012b 仅包含：
  1. `social_navigation_adapter.dart`（资料、关注、私信、拉黑跳转宿主页面）；
  2. 编辑器输入 `@` 弹出的候选列表来源与 `MentionInputEnhancer` 挂接；
  3. 编辑器保存前调用 `reconcileMentions` 解除关系的生命周期接线；
  4. 依赖真实宿主账号状态的三类无效 mention（user_id 不存在、账号已注销、已被目标拉黑）及宿主关系验收。
- **结论**：拆分边界清晰，符合 D-NC012-01，NC-012a 无遗漏项。

### 1.3 契约与上游冲突处逐条核实
| 决策编号 | 契约条目 | 与上游现状/原条目的关系 | 审查结论 |
|---|---|---|---|
| **D-NC012-05** | §12.1 写响应包装 | 原 `community_api.md` §2 声明 W10 返回 `ReactionState`、W11 返回 `BookmarkState`。但两者 Schema 设为 `additionalProperties: false`，无法容纳 `community_server.md` §3 / `community_api.md` §7 强制要求的 `command: CommandResult`。改为 `ReactionResponse` 与 `BookmarkResponse` 包装，与 NC-011 的 `CommentResponse` 完全一致。 | **合法且必须**，已同步补丁至 `community_api.md` §12.1。 |
| **D-NC012-06** | §12.2 新增 R7/R8 端点 | 原 `community_api.md` 缺少「查询当前用户分享链接列表」端点（PRD §6.6 明确要求）及「查询收藏状态」端点。新增 R7 `GET /me/share-links` 与 R8 `GET /bookmarks/{target_type}/{target_id}`。 | **合法且完备**，已同步补丁至 `community_api.md` §12.2。 |
| **D-NC012-07** | §12.3 R4 统一 404 | 原 `community_api.md` §2 R4 包含 400/404/410。根据 PRD §6.2「内容失效统一文案『该内容已不可访问』，不区分收回/删除/隐藏/拉黑」及 `community_server.md` §5 ACL 扫描矩阵 E4 规则，任何失效或未公开链接统一返回 HTTP 404 及 `SHARED_NOT_FOUND_CONTENT_BODY`，杜绝信息泄漏。 | **符合核心安全规则**，打通 ACL 扫描 E4。 |
| **D-NC012-12** | §6.1 / §12.3 R3 ETag | ETag 包含当前查看者版本与两项计数 `"{version}:{like}:{dislike}"`；鉴权与 ACL 判定先于 304。 | **符合 REST 缓存规范与安全基线**。 |

---

## 2. 二查 覆盖性（Coverage）

### 2.1 TASKS NC-012 验收基准反例与重点用例覆盖矩阵
| TASKS 原文验收要求 | 契约条款 | BDD 条目 | SERVER 测试 | CLIENT 测试 |
|---|---|---|---|---|
| like(v0) → v1，cancel(v1) → v2 | §5.1, §3.1 | I01, I03 | `test_reaction_like_writes_reaction_counts_outbox_event_atomically`, `test_reaction_cancel_keeps_null_row_and_decrements_count` | J01, J05 |
| 旧 like 同键重放后数据库仍 null/v2，UI 不被旧 v1 响应覆盖 | §5.1, §10.7 | I07, J13 | `test_reaction_old_like_replay_after_cancel_returns_original_and_state_stays_null` | `test_reaction_late_older_version_response_does_not_roll_back` |
| 重启后新动作使用读取版本 | §10.7 | J15 | — | `test_reaction_restart_restores_pending_value_and_next_action_uses_read_version` |
| 两设备同基线不同意图一个成功一个 412，禁止自动换版本抢写 | §5.1, §10.7 | I08, J14 | `test_reaction_two_devices_same_baseline_one_commits_one_412` | `test_reaction_412_refreshes_state_and_does_not_auto_retry` |
| 未执行旧键 / 旧版本（If-Match 校验） | §5.1 | I06 | `test_reaction_if_match_missing_400_stale_412_malformed_400_without_ledger` | J01 |
| 相同值不重复计数（幂等 no-op，不升版本） | §5.1 | I05 | `test_reaction_same_value_is_noop_without_version_bump` | — |
| 10 个并发操作计数恰 10 | §8.2 | I10 | `test_reaction_ten_concurrent_accounts_count_exactly_ten` | — |
| 目标 purge 后旧命令不复活 | §8.2 | I13 | `test_reaction_after_target_purge_replay_does_not_revive` | — |
| 快速切换乱序 / 重试，串行合并至已确认版本 | §10.7 | J12 | — | `test_reaction_rapid_toggle_coalesces_to_serial_commands_with_confirmed_version` |
| 两账号计数互不干扰，共享计数正确 | §8.2 | I09 | `test_reaction_two_accounts_have_independent_values_and_shared_counts` | — |
| 失权目标统一 404（withdrawn / trashed / hidden） | §4.3, §6.3 | I11, I17, I19, I25 | `test_reaction_on_non_public_content_is_404_for_others`（参数化 3 例）, `test_share_resolve_returns_target_and_all_failures_share_one_404`（参数化 8 例） | J19, J24 |
| RW-5 ①：真实文件库关闭重开以原键重试 | §11 | J05 | — | `test_interaction_restart_with_real_file_close_reopen_resends_same_key` |
| RW-5 ②：响应丢失后对账不新建操作 | §11 | J06 | — | `test_interaction_lost_response_reconciles_by_get_command_without_new_report` |
| RW-5 ③：410 与 503 绝不换键重放 | §11 | J07 | — | `test_interaction_410_and_503_never_change_key` |
| Code point 偏移判定与同昵称多处独立判定 | §9, §10.6 | J10, J11 | — | `test_reconcile_mentions_matches_python_reference_vectors`, `test_reconcile_mentions_counts_code_points_not_utf16_units` |
| 举报受理确认与本地折叠 | §10.7, §10.9 | J17, J21, J22 | `test_report_create_201_keyed_by_command_id_with_exact_fields` | `test_report_marks_reported_locally_before_send_and_clears_on_rejection`, `test_report_sheet_submits_...`, `test_reported_fold_survives_restart_...` |
| 分享解析检查当前权限与撤销 | §5.4, §6.3 | I18, I19, I20 | `test_share_create_by_author_...`, `test_share_resolve_...`, `test_share_revoke_...` | J18, J19, J23 |

**覆盖性结论**：所有基准反例、核心业务场景、边界与异常分支均有明确测试断言，无仅测 Happy Path 的现象。

---

## 3. 三查 可执行性（Executability）

### 3.1 既有路径与符号真实存在性审查
经实地代码检索与比对，所有 SCOPE 内引用符号均真实存在：
1. **服务端权限判定**：[`xuan-server/functions-py/xuan/community/access.py:39-73`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/access.py#L39-L73) 的 `resolve_access(content_id, viewer_scope, client=None, tx=None)` 返回 `("owner"|"visible"|"not_found", access_dict)`。
2. **命令账本构造与响应合成**：
   - [`xuan-server/functions-py/xuan/community/command_service.py:56-87`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/command_service.py#L56-L87) 提供了 `build_command_context(..., extra_new_ids=...)`，接受外部传入的新 ID 字典。
   - [`xuan-server/functions-py/xuan/community/command_service.py:271-277`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/command_service.py#L271-L277) 与 [`lines 256-262`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/command_service.py#L256-L262) 证实 `run_command` 会将 `outcome.body` 复制并追加 `"command": _make_command_result(...)`。
3. **载荷校验与 JSON Pointer**：[`xuan-server/functions-py/xuan/community/validation.py:24`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/validation.py#L24) 存在 `_REGISTRY`；[`lines 113-129`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/validation.py#L113-L129) 的 `validate_comment_create` 实现了首个错误绝对路径拼为 `/{sub}` 或 `/` 的逻辑。
4. **错误模型与共用响应体**：
   - [`xuan-server/functions-py/xuan/community/errors.py:101-115`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/errors.py#L101-L115) 的 `problem()` 显式包含 `"field"`、`"limit"`、`"current_version"` 等白名单附加属性。
   - [`xuan-server/functions-py/xuan/community/errors.py:68-73`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/errors.py#L68-L73) 存在 `SHARED_NOT_FOUND_CONTENT_BODY`。
5. **Schema 时间格式**：[`xuan-server/functions-py/xuan/community/schemas/community_common.schema.json:116-118`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/schemas/community_common.schema.json#L116-L118) 的 `timestamp` 正则为 `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{1,6})?Z$`，完美兼容 6 位微秒。
6. **Handler 前置提取写法**：[`xuan-server/functions-py/xuan/handlers/community_comments.py:26-75`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/handlers/community_comments.py#L26-L75) 提供了清晰的鉴权、UID 映射、路径剥离、Query 解析与 If-Match 处理范式。
7. **服务端测试辅助与 ACL 扫描**：
   - [`xuan-server/functions-py/tests/community_helpers.py:41, 112, 172`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/tests/community_helpers.py#L41) 存在 `call`、`seed_access`、`seed_comment`。
   - [`xuan-server/functions-py/tests/test_community_acl_sweep.py:40-43, 174-181`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/tests/test_community_acl_sweep.py#L40) 存在 `E4` 分支与 xfail 标记。
8. **客户端命令队列与 Drift 表**：
   - [`xuan-migration/reading-notes/lib/src/community/command_queue.dart:57-100`](file:///Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src/community/command_queue.dart#L57-L100) 存在 `enqueue`、`drain`、`recover`、`ownerScope`。
   - [`xuan-migration/reading-notes/lib/src/community/command_queue.dart:382`](file:///Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src/community/command_queue.dart#L382) 证实 `_handleExecutionResult` 严格依赖 `(val as dynamic).toJson()`。
   - [`xuan-migration/reading-notes/lib/src/community/community_database.dart:64-75`](file:///Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src/community/community_database.dart#L64-L75) 与 [`community_database.g.dart:1691, 1775`](file:///Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src/community/community_database.g.dart#L1691) 存在 `CommunityMetaTable`、`communityMetaTable` 访问器与 `CommunityMetaTableCompanion`。
9. **客户端 MentionRef 单一化调用点**：
   - [`xuan-migration/reading-notes/lib/src/domain/note_revision.dart:51-76`](file:///Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src/domain/note_revision.dart#L51-L76) 的 `MentionRef` 具有 `fromMap` 与 `toMap`。
   - [`xuan-migration/reading-notes/lib/src/community/models.dart:557, 567, 722, 734, 755, 763`](file:///Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src/community/models.dart#L557) 的全部反序列化/序列化调用点已精准识别并与契约 §2.2 规则对齐。
10. **REST 仓 OpenAPI 组件**：
    - [`xuan-migration/repository-rest-adapter/openapi/openapi.yaml:3774, 3862`](file:///Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/openapi/openapi.yaml#L3774) 存在 `403ForbiddenThreadClosed` 与 `413TooLarge`。
    - [`openapi.yaml:1167-1170`](file:///Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/openapi/openapi.yaml#L1167-L1170) R6 参数列表清晰。
    - [`openapi.yaml:3181-3206`](file:///Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/openapi/openapi.yaml#L3181-L3206) `CommandResult.resource_ids` 已包含 `target_type`、`target_id`、`reaction_id`、`bookmark_id`、`share_id`、`report_ref`。

### 3.2 验证命令与工具链可用性
- 所有工具链均已实测存在且具有执行权限：
  - `/Users/jingtaiwei/Git/Public/xuan-server/functions-py/.venv/bin/python`
  - `/Users/jingtaiwei/flutter/bin/dart` 与 `flutter`
  - `/opt/homebrew/bin/npm`
  - `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/tool/validate_openapi`
  - `/Users/jingtaiwei/Git/Public/learn_system/.venv/bin/python`

### 3.3 测试计数一致性核验表
| 线 / 阶段 | 增量测试项数 | 单模块断言/测试期望 | 全量期望 | 守卫/基线核对依据 |
|---|---|---|---|---|
| **REST act/01** | +4 个测试 | `dart test test/community_openapi_contract_test.dart` -> `+27` | `dart test` -> `+77: All tests passed!`（基线 +73） | 契约 §12.2、TDD §2、`nc012a_guard.sh:113` |
| **SERVER act/02** | 17 个测试名（19 例） | `test_community_interactions.py` -> `19 passed`（I11 参数化 3 例） | pytest -> `5 failed, 515 passed, 9 xfailed`（基线 496 passed）；npm rules -> `129 passed`（基线 89） | 契约 §8.2、TDD §3、`nc012a_guard.sh:89` |
| **SERVER act/03** | 10 个测试名（17 例） | `test_community_interactions.py` 累计 `36 passed`（I19 参数化 8 例）；ACL 扫描 -> `12 passed, 6 xfailed` | pytest -> `5 failed, 535 passed, 6 xfailed`（+17 新例 + 3 E4 xfail转真 = +20 passed，FAILED 集合保持 5 个既有 ID） | 契约 §8.2、§8.3、TDD §4、`nc012a_guard.sh:137` |
| **CLIENT act/04** | +11 个测试 | `interactions_test.dart` -> `+11` | `flutter test` -> `+281: All tests passed!`（基线 +270） | 契约 §11、TDD §5、`nc012a_guard.sh:89` |
| **CLIENT act/05** | +8 个测试 | `interactions_test.dart` -> `+19` | `flutter test` -> `+289: All tests passed!` | 契约 §11、TDD §6、`nc012a_guard.sh:89` |
| **CLIENT act/06** | +7 个测试 | `interactions_test.dart` -> `+26` | `flutter test` -> `+296: All tests passed!` | 契约 §11、TDD §7、`nc012a_guard.sh:167` |

### 3.4 规范合规与工作量
- **模糊词检测**：全套文件经正则 `适当|优雅|合理|必要时|酌情|尽量|大致|视情况` 扫描，0 命中。
- **ON_FAIL**：act/01～06 全部具备明确的 `ON_FAIL` 处理逻辑与停手协议。
- **工作量评估**：
  - 各 ACT 预估用时在 40～60 分钟区间内，符合 30～60 分钟标准。
  - act/05（两个控制器 + resolveShare，共 410 行代码与 8 个测试 520 行）和 act/06（5 个界面组件 + 2 处可选挂载，共 450 行代码与 7 个 widget 测试 450 行）工作量处于 60 分钟上限边缘，但因测试结构清晰且均有现成模板参考，判定在可控范围内。

---

## 4. 四查 独立性（Independence）

### 4.1 三线并行无文件踩踏
- REST 线：仅操作 `xuan-migration/repository-rest-adapter` 仓库。
- SERVER 线：仅操作 `xuan-server/functions-py` 仓库与 `xuan-migration/xuan-server` 规则目录。
- CLIENT 线：仅操作 `xuan-migration/reading-notes` 仓库。
- 三线互不重叠，完全支持三个执行者并行推进。

### 4.2 仓库内依赖与符号前置完整性
1. **REST 依赖**：`act/01` 独立无依赖（`DEPENDS_ON: []`）。
2. **SERVER 依赖链**：`act/02` -> `act/03`。
   - `act/02` 中 `main.py` 需同时导出四个 handler 函数，契约与 `act/02.yaml` 明确要求将 `community_share_py` 与 `community_report_py` 预先占位定义为返回 404，成功防止了 `main.py` 导出报错或注册测试失败。
   - `act/03` 承接 `act/02`，正式交付分享与举报逻辑及 E4 ACL 真实断言。
3. **CLIENT 依赖链**：`act/04` -> `act/05` -> `act/06`。
   - `act/04` 交付底层模型、纯函数 `reconcileMentions`、API 方法与 `command_queue` case。
   - `act/05` 消费 `act/04` 交付的模型与 API，实现两大控制器。
   - `act/06` 消费 `act/05` 交付的控制器，完成 Widget 构建与可选参数挂载。
   - 后置步骤所依赖符号均在前置步骤中严密交付，依赖链严格闭环。

---

## 5. 审查结论

综上四查结果，NC-012a 契约与六件套在**忠实性**、**覆盖性**、**可执行性**和**独立性**上均通过严格检验。

- **最终判定**：`READY`
- **返工项**：0 项

---

## 6. 建议（非阻断性实现提示）

为确保执行者在编码时不产生歧义并顺利通过验收，提出以下 8 项关键技术建议：

1. **`CommandOutcome.resource_ids` 字典语法 vs 集合简写**：
   - *现象*：契约 §5.1 第 150 行、§5.2 第 161 行写作 `ids = {"target_type", "target_id", "reaction_id"}`。在 Python 中这是 `set` 类型。
   - *证据*：[`command_service.py:206`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/community/command_service.py#L206) 执行 `"resource_ids": {str(k): str(v) for k, v in outcome.resource_ids.items()}`，若传入 `set` 会引发 `AttributeError`。
   - *实现指引*：执行者必须将其实现为 `dict`，例如 `resource_ids={"target_type": target_type, "target_id": target_id, "reaction_id": reaction_id}`，与 OpenAPI 及契约 §12.3 示例保持一致。
2. **`InteractionController.refreshPending` 的重入防范**：
   - *现象*：契约 §10.7 中 `refreshPending()` 处理 committed 时若 `_hasPendingReaction` 成立会触发 `_sendReaction`，而 `_sendReaction` 末尾又 `await refreshPending()`。
   - *实现指引*：在调用 `_sendReaction` 之前，必须先将本地标志清空并取出目标意图（`final next = _pendingReaction; _hasPendingReaction = false; _pendingReaction = null; _sendReaction(next);`），防止状态重入死循环。
3. **I10 10 线程并发在 Firestore Emulator 上的事务重试**：
   - *现象*：10 个线程同时竞争更新同一个 `community_reaction_counts` 投影文档，Firestore 事务会频繁触发 `Aborted` 并转换为 503。
   - *实现指引*：I10 客户端重试循环中建议加入轻微随机扰动（`time.sleep(random.uniform(0.01, 0.05))`），避免 10 个线程以完全同步的频率重试导致耗尽 5 次重试上限。
4. **R3 304 响应必须使用空响应体**：
   - *现象*：[`community_contents.py:295-308`](file:///Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/handlers/community_contents.py#L295-L308) 的 `_make_response` 会对 `{}` 进行 JSON 序列化，返回 `"{}"`。
   - *实现指引*：严格按照契约 §7 第 228 行，304 分支直接构造 `https_fn.Response(response="", status=304, headers={"ETag": etag})`，绝不走 `_make_response`。
5. **Drift `community_meta` 表删除与查询语法**：
   - *证据*：[`community_database.g.dart:1775`](file:///Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src/community/community_database.g.dart#L1775) 生成的表访问器名为 `communityMetaTable`。
   - *实现指引*：删除被拒举报折叠记录时使用 `(db.delete(db.communityMetaTable)..where((t) => t.key.equals('reported:$targetKey'))).go()`。
6. **`ContentDetailPage` 缺省渲染结构严格保持原样**：
   - *证据*：[`content_detail_page.dart:138-154`](file:///Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src/community/content_detail_page.dart#L138-L154) 默认直接在 SingleChildScrollView 的 Column 下平铺三项。
   - *实现指引*：当 `widget.snapshotWrapper == null` 时，直接展开原三个子组件，不可无条件嵌套外层 `Column`，以确保既有七状态测试与 Widget 树深度零变化。
7. **`models.dart` 删除 `MentionRef` 后的调用点替换**：
   - *证据*：[`models.dart:557, 567, 722, 734, 755, 763`](file:///Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src/community/models.dart#L557)。
   - *实现指引*：反序列化使用 `MentionRef.fromMap((e as Map).cast<String, Object?>())`，序列化使用 `e.toMap()`，严格替换全部 6 处调用。
8. **REST 示例与 `tool/check_examples.py` 校验**：
   - *证据*：[`openapi.yaml:3181-3206`](file:///Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/openapi/openapi.yaml#L3181-L3206) `CommandResult.resource_ids` 已提前声明所有互动 ID 字段。
   - *实现指引*：执行者按契约 §12.3 录入示例即可直接通过 `tool/check_examples.py`，无需改动已有 Schema 结构。

---

## 7. 待裁决（无阻断分歧，记录备忘）

1. **关于 Firestore 复合索引部署的延后（D-NC012-20）**：
   - 裁决记录：R7 `list_my_share_links` 在服务端执行 `where("created_by", "==", owner_scope).order_by("created_at", DESCENDING).order_by("id", DESCENDING)`。在生产环境此组合查询需要 Firestore 复合索引，而在 Emulator 环境中此查询无需预先部署索引即可运行。主 Agent 裁定将云端复合索引部署延后至 NC-019/NC-020，本次在 Emulator 下直接通过，该裁决保持生效。
2. **关于 Mention 校验与编辑器接线的分阶段交付（D-NC012-01）**：
   - 裁决记录：本次通过纯函数 `reconcileMentions` 先行固化跨端与 emoji code point 判定向量，待 NC-001-02 宿主社交端点交付后在 NC-012b 接入编辑器与讨论区，该裁决保持生效。
