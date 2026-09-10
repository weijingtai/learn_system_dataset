# NC-001-01 校验字段契约

状态：PREPARING；这是规划快照检查器的输入契约，不是业务 REST Schema。权威规格为 PRD/DESIGN/TASKS v1.5。所有相对证据路径相对于输入 JSON 所在目录解析，绝对路径保持原值；只检查文件存在，不读取凭据或执行证据中的命令。

## 公共规则

- 输入根必须是 object；必填顶层键为 schema_version、spec_version、task_id、scope、book_work、client、sdk、dependencies、resolution_status、repositories、identity、openapi_validator、integration。
- schema_version 为整数 1（bool 不接受）；spec_version 为字符串 `1.5`；task_id 为 `NC-001`；scope 为 `LOCAL_PREPARATION` 或 `TEST_FIXTURE`。TEST_FIXTURE 不可被当成真实联调完成。
- client、sdk、dependencies、identity、openapi_validator、integration 必须为 object；repositories 为非空数组。当前 JSON 内的子字段均必填；不得用 truthy 检查误拒绝 false/0，也不得把缺键当 null。
- client.state 只允许 PLANNED_NEW/EXISTING；前者 creation_owner=NC-004 且父目录存在，后者必须有 pubspec.yaml 文件和 lib 目录。package=reading_notes。
- sdk 版本及 dependencies 各键值与 INTEGRATION_BASELINE.md §4 一致；sdk.evidence 是存在的文件。sdk.verification 只允许 CACHE_METADATA_ONLY/RUNTIME_VERIFIED。
- identity.policy=HOST_SCOPE_ONLY，new_identity_system=false；book_work=DEFERRED_BY_USER。
- resolution_status 只允许 NOT_RUN/RESOLVED。RESOLVED 必须增加 resolution_evidence（存在的文件）；集成校验还要求 client.runtime_verified=true、sdk.verification=RUNTIME_VERIFIED、resolution_status=RESOLVED。
- repositories 恰含 SPEC/MIGRATION/STORAGE/SOCIAL/NOTIFICATION/REST/SERVER/NOTIFIER，每个 name 唯一；MIGRATION.status=UNAVAILABLE 表示非 Git 父目录，不要求伪造 HEAD。其他记录的 head 为 40 位小写十六进制、path/git_root 非空；tests.status 只允许 NOT_RUN/PASSED/FAILED，NOT_RUN 必须有非空 reason。
- 未知状态枚举一律拒绝；可接受额外说明字段，但额外字段不能替代任何必填字段。

## integrated 增量规则

local 仍校验上述字段和下表对象的必填键/类型，但允许当前快照中已列明的空数组和未验证状态。integrated 必须逐项满足下表，不可首次失败就停止收集错误。

| 路径 | 集成结构通过的条件 |
|---|---|
| integration.devices | 至少两个 object，device_id 非空且不同，platform/os_version 非空，p2p_peer 为 bool，至少一个 true |
| integration.account_pairs | 至少两个 object，uid/app_user_id 均非空且各自唯一；不记录 token/password |
| integration.emulator | 保留三个 config 非空字段；status=VERIFIED，另含存在的 evidence 文件；CONFIG_ONLY_NOT_CONTACTED 仅 local 接受 |
| integration.rules | status=VERIFIED，path 与 evidence 均为存在的文件；UNVERIFIED 仅 local 接受 |
| integration.notifier_binding | status=VERIFIED，evidence 为存在文件；UNVERIFIED 仅 local 接受 |
| integration.test_runs | 非空，包含 STORAGE/SOCIAL/NOTIFICATION/REST/SERVER/NOTIFIER 各自一条 repository 记录；每条满足下述执行证据规则 |
| repositories[].tests | 除 MIGRATION 外均 PASSED，且满足执行证据规则；不可只改 status |
| openapi_validator | package=openapi-spec-validator，version=0.9.0；status=VERIFIED，evidence 存在；NOT_INSTALLED_IN_CURRENT_PYTHON 仅 local 接受 |
| integration.account_deletion | 按下节 |

执行证据规则：command 非空字符串、exit_code 是整数 0（不接受 bool）、count 是正整数（不接受 bool）、evidence 是存在文件。FAILED 可以记录非零 exit_code，但 integrated 必须拒绝。结构检查不验证这些记录真实发生，独立验收者必须核原始输出。所有正例用临时文件，不读取真实用户资料。

## account_deletion 精确规则

当前 UNVERIFIED 记录的必填字段：status、source、delivery_semantics、test_command、exit_code、count、evidence、consumer、blocked_scope。consumer=NC-026；blocked_scope=NC-026_ACCOUNT_DELETION。status 只允许 UNVERIFIED/VERIFIED。

UNVERIFIED 时 source/delivery_semantics/test_command/exit_code/count/evidence 必须全为 null，local 接受，integrated 输出 `integration.account_deletion.status` 错误。

VERIFIED 时 source 为 object：file 非空、symbol 非空、event_kind=`ACCOUNT_DELETED`；delivery_semantics 只允许 AT_LEAST_ONCE/EXACTLY_ONCE。test_command 非空，exit_code 为整数 0，count 为正整数，evidence 为存在文件。任何 sign_out/logout 或其他 event_kind 均拒绝。source 的文件符号仅登记，不在本工具越权扫描外部源码；真实性由 NC-001-02 独立取证。至少一次事件的重复处理验证属于 NC-026，不由规划校验器伪装执行。

## 输出

退出 0：local 单行 LOCAL_PREPARATION_PASS；integrated 单行 INTEGRATED_STRUCTURE_PASS。退出 1：stdout 每行一个完整字段路径，去重后字典序，无 PASS。退出 2：输入不可读/JSON 错误/CLI 错误，stderr 简短诊断，无 traceback。缺键、类型或枚举错误属于退出 1，不能崩溃成退出 2。两种 profile 均不得写文件或创建目录。
