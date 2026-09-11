# NC-001-01 校验字段契约

状态：PREPARING（R1 返工版，见 [NC-001-REVIEW-R1](../../reviews/NC-001-REVIEW-R1.md)）。这是 `openspec/annotation-community/tools/check_integration_baseline.py` 的输入契约，不是业务 REST Schema。权威规格为 PRD/DESIGN/TASKS v1.5 与 TASKS NC-001。本文列出的键、枚举与固定值就是全部判据：执行者不得从输入 JSON 反推必填项，也不得自行增删。

## 1. 读取范围

- 输入 JSON 由 `--input` 指定；同目录的 `INTEGRATION_BASELINE.md` 一并读取。
- JSON 中的相对路径相对于输入 JSON 所在目录解析，绝对路径保持原值。
- 对外部路径只判断存在性（exists / is_file / is_dir），不读取外部文件内容、不执行 Git、不读取凭据；唯一读取内容的文件是输入 JSON 与同目录的 `INTEGRATION_BASELINE.md`。
- 两种 profile 都不得写文件或创建目录。

## 2. 顶层（两种 profile 共同）

| 路径 | 规则 |
|---|---|
| （根） | object |
| schema_version | 整数 1，bool 不接受 |
| spec_version | 字符串 `1.5` |
| task_id | 字符串 `NC-001` |
| scope | `LOCAL_PREPARATION` / `INTEGRATED` / `TEST_FIXTURE` |
| book_work | `DEFERRED_BY_USER` |
| resolution_status | `NOT_RUN` / `RESOLVED` |
| resolution_evidence | 键必须存在；NOT_RUN 时为 null，RESOLVED 时为存在的文件 |
| client、sdk、dependencies、dependency_policy、identity、openapi_validator、integration | object |
| repositories、ports | array |

## 3. 对象规则（两种 profile 共同）

**client**：path 非空字符串；package=`reading_notes`；state ∈ `PLANNED_NEW` / `EXISTING`；creation_owner 为字符串；vcs=`NEW_GIT_REPOSITORY`；runtime_verified 为 bool。
- PLANNED_NEW：creation_owner≠`NC-004` 报 `client.creation_owner`；path 的父目录不存在报 `client.path`；path 本身已存在报 `client.state`（防止建空目录冒充）。
- EXISTING：`<path>/pubspec.yaml` 不是文件、`<path>/lib` 不是目录、`<path>/.git` 不存在，任一成立报 `client.path`。

**sdk**：flutter=`3.44.6`；dart=`3.12.2`；evidence 为存在的文件；verification ∈ `CACHE_METADATA_ONLY` / `RUNTIME_VERIFIED`。

**dependencies**：恰好下列 8 个键，值逐字相等。多出键报 `dependencies`；缺键或值不等报 `dependencies.<键>`。

| 键 | 值 |
|---|---|
| flutter_markdown_plus | 1.0.12 |
| drift | 2.31.0 |
| drift_dev | 2.31.0 |
| drift_flutter | 0.2.8 |
| sqlite3 | 2.9.4 |
| sqlite3_flutter_libs | 0.5.42 |
| path_provider | 2.1.6 |
| build_runner | 2.15.1 |

**dependency_policy**：offline_failure=`ENV_BLOCKED`；flutter_markdown_plus_rationale 为非空字符串。

**identity**：policy=`HOST_SCOPE_ONLY`；new_identity_system 为 false（bool）；public_profile_id 为非空字符串。

**repositories**：name 恰为 SPEC、MIGRATION、STORAGE、SOCIAL、NOTIFICATION、REST、SERVER、NOTIFIER 各一次，集合不符报 `repositories`。每条 path 非空；write_policy ∈ `READ_ONLY` / `PER_TASK_WHITELIST`。
- MIGRATION：status=`UNAVAILABLE`，write_policy=`READ_ONLY`，不要求 git_root、head、tests。
- 其余 7 条：git_root 非空；head 为 40 位小写十六进制；dirty_entries 为非负整数（bool 不接受）；tests 为 object；tests.status ∈ `NOT_RUN` / `PASSED` / `FAILED`；NOT_RUN 时 tests.reason 非空。
- NOTIFIER 的 write_policy 必须为 `READ_ONLY`。

**ports**：name 恰为 HOST_INIT、ACCOUNT_SCOPE、HTTP、STORAGE、IM_NAVIGATION、MENTION、NOTIFICATION_RECEIVE、SERVER_IDENTITY 各一次，集合不符报 `ports`。每条：file 为存在的文件；symbol 匹配 `^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$`（纯行号、`文件:行` 均拒绝）；kind ∈ `EXISTING_IMPLEMENTATION`（直接调用既有实现）/ `NEW_ADAPTER`（CLIENT 或 SERVER 新增适配层后使用该符号）。符号是否真在文件中由主线程守卫核对，本工具不读外部文件内容。

**openapi_validator**：package=`openapi-spec-validator`；version=`0.9.0`；install_command 非空；offline_failure=`ENV_BLOCKED`；status ∈ `NOT_INSTALLED_IN_CURRENT_PYTHON` / `VERIFIED`；evidence 键存在，未验证态时为 null。

**integration 下的对象**：表中键必须全部存在。status 为未验证态时，验证字段必须全为 null，否则报该字段路径（防止半填冒充）。

| 对象 | 未验证态 / 验证态 | 验证字段 | 常驻字段 |
|---|---|---|---|
| integration.backend | UNVERIFIED / VERIFIED | project_id、namespace_prefix、credential_injection、evidence | — |
| integration.emulator | CONFIG_ONLY_NOT_CONTACTED / VERIFIED | start_command、evidence | firestore_config、auth_config、project_config 为非空字符串 |
| integration.rules | UNVERIFIED / VERIFIED | path、evidence | — |
| integration.notifier_binding | UNVERIFIED / VERIFIED | evidence | — |
| integration.notification_presentation | UNVERIFIED / VERIFIED | evidence | choice ∈ SOCIAL_NOTIFICATION_CENTER / NOTIFICATION_PACKAGE_PAGE；file 为存在的文件；symbol 同 ports 规则 |
| integration.mute_aggregation | UNVERIFIED / VERIFIED | content_mute、aggregation、evidence | — |
| integration.account_deletion | UNVERIFIED / VERIFIED | source、delivery_semantics、test_command、exit_code、count、evidence | consumer=`NC-026`；blocked_scope=`NC-026_ACCOUNT_DELETION` |

integration.devices、integration.account_pairs、integration.test_runs 为 array，local 允许空数组。

**INTEGRATION_BASELINE.md**：必须存在；含 `TBD` 或 `待定`（区分大小写）即报 `INTEGRATION_BASELINE.md`。不扫描 `?`，因为正文中的 URL 与中文问句会误报。

## 4. integrated 增量规则

integrated 先执行 §2～§3，再执行下表。

**状态闸门**：对象的 status 不是验证态时，只报 `<对象>.status`，不再报该对象的验证字段；status 为验证态时，逐个报不合格的验证字段。

| 路径 | 通过条件 |
|---|---|
| scope | `INTEGRATED` 或 `TEST_FIXTURE` |
| client.state | `EXISTING` |
| client.runtime_verified | true |
| sdk.verification | `RUNTIME_VERIFIED` |
| resolution_status | `RESOLVED` |
| integration.backend | VERIFIED；project_id 非空；namespace_prefix 匹配 `^nc_[0-9]{8}_[0-9a-f]{4,12}$`；credential_injection=`RUNTIME_ENV_VAR`；evidence 为存在的文件 |
| integration.emulator | VERIFIED；start_command 非空；evidence 为存在的文件 |
| integration.rules | VERIFIED；path 与 evidence 均为存在的文件 |
| integration.notifier_binding | VERIFIED；evidence 为存在的文件 |
| integration.notification_presentation | VERIFIED；evidence 为存在的文件 |
| integration.mute_aggregation | VERIFIED；content_mute 与 aggregation 各自 ∈ SUPPORTED / UNSUPPORTED_E_WIRING；evidence 为存在的文件 |
| integration.account_deletion | 见 §5 |
| openapi_validator | VERIFIED；evidence 为存在的文件 |
| integration.devices | 至少 2 条；每条 device_id、platform、os_version 非空，p2p_peer 为 bool；device_id 互不相同；至少一条 p2p_peer=true。任一不满足只报 `integration.devices` |
| integration.account_pairs | 至少 2 条；每条 uid、app_user_id 非空，两列各自不重复；任一条含 token 或 password 键即不合格。任一不满足只报 `integration.account_pairs` |
| integration.test_runs | repository 恰为 SPEC、STORAGE、SOCIAL、NOTIFICATION、REST、SERVER、NOTIFIER 各一条，集合不符只报 `integration.test_runs`；集合相符时逐条按执行证据规则报 `integration.test_runs[<名>].<字段>` |
| repositories[<名>].tests（MIGRATION 除外） | status 不是 PASSED 只报 `.status`；PASSED 时按执行证据规则报 `repositories[<名>].tests.<字段>` |

**执行证据规则**：command 为非空字符串；exit_code 为整数 0（bool 不接受）；count 为正整数（bool 不接受）；evidence 为存在的文件。结构检查不能证明命令真的执行过，独立验收者必须核对原始输出。

## 5. account_deletion

- UNVERIFIED：六个验证字段全为 null；local 通过；integrated 只报 `integration.account_deletion.status`。
- VERIFIED：source 为 object，其中 file 非空、symbol 非空、event_kind=`ACCOUNT_DELETED`（sign_out、logout 等任何其他值报 `integration.account_deletion.source.event_kind`；source 不是 object 报 `integration.account_deletion.source`）；delivery_semantics ∈ AT_LEAST_ONCE / EXACTLY_ONCE；test_command 非空；exit_code 为整数 0；count 为正整数；evidence 为存在的文件。
- 至少一次送达下的重复处理由 NC-026 验证，本工具不模拟。

## 6. 错误路径写法与输出

- 对象键用点号：`client.state`。数组中按 name 或 repository 定位的记录用方括号：`repositories[SPEC].tests.status`、`ports[HTTP].symbol`、`integration.test_runs[SERVER].evidence`。
- 缺键、类型错误、枚举不符、值不等，都报该键的完整路径；父级不是 object 时只报父级路径，不再下钻。
- 退出 0：stdout 恰好一行。local 为 `LOCAL_PREPARATION_PASS`，integrated 为 `INTEGRATED_STRUCTURE_PASS`；scope=TEST_FIXTURE 时行尾追加一个空格和 `(TEST_FIXTURE)`。
- 退出 1：stdout 每行一个路径，去重后按 Python `sorted()` 排序，不输出 PASS。
- 退出 2：`--input` 缺失或不可读、JSON 语法错误、`--profile` 缺失或不是 local/integrated；stderr 输出一行诊断，不输出 traceback，stdout 为空。缺键、类型或枚举错误属于退出 1，不得崩溃成退出 2。

## 7. 当前输入的期望输出

`--profile local` 对当前 `openspec/annotation-community/integration_baseline.json`：退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS`。

`--profile integrated` 对同一文件：退出 1，stdout 与下列 23 行逐字相同。

```text
client.runtime_verified
client.state
integration.account_deletion.status
integration.account_pairs
integration.backend.status
integration.devices
integration.emulator.status
integration.mute_aggregation.status
integration.notification_presentation.status
integration.notifier_binding.status
integration.rules.status
integration.test_runs
openapi_validator.status
repositories[NOTIFICATION].tests.status
repositories[NOTIFIER].tests.status
repositories[REST].tests.status
repositories[SERVER].tests.status
repositories[SOCIAL].tests.status
repositories[SPEC].tests.status
repositories[STORAGE].tests.status
resolution_status
scope
sdk.verification
```
