# NC-001-01 可观察行为

判据见 [VALIDATION_CONTRACT.md](VALIDATION_CONTRACT.md)；「报 X」指退出 1 且 stdout 含路径 X。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 当前计划新建客户端、父目录存在、建包归 NC-004，十项中未验证项均按契约登记 | 校验 local | 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS`，不声称运行就绪 |
| B02 | 同一份当前快照 | 校验 integrated | 退出 1，stdout 与契约 §7 的 23 行逐字相同 |
| B03 | 删除契约 §2～§3 中任一必填键 | 校验 local | 报该键完整路径，无 PASS |
| B04 | PLANNED_NEW 但创建责任不是 NC-004、父目录不存在或 path 已存在 | 校验 local | 分别报 `client.creation_owner`、`client.path`、`client.state`，不创建目录 |
| B05 | EXISTING 但缺 pubspec.yaml、lib 或 .git；或 sdk.evidence 指向的文件不存在 | 校验 local | 报 `client.path` 或 `sdk.evidence`，不修改任何文件 |
| B06 | 某仓库 tests 只把 NOT_RUN 改成 PASSED，没有 command/exit_code/count/evidence | 校验 integrated | 报该仓库 tests 下缺失的每个字段 |
| B07 | new_identity_system=true，或 book_work 不是 DEFERRED_BY_USER | 校验 local | 报 `identity.new_identity_system` 或 `book_work` |
| B08 | JSON 语法错误、输入文件不存在、缺 `--profile` 或 profile 未知 | 执行校验 | 退出 2，stdout 为空，stderr 一行且无 Traceback |
| B09 | 临时目录中 scope=TEST_FIXTURE、全部对象为验证态且证据文件齐全 | 校验 integrated | 退出 0，stdout 恰为 `INTEGRATED_STRUCTURE_PASS (TEST_FIXTURE)` |
| B10 | 任一次校验结束 | 比较运行前后输入与目录 | 内容与目录列表均未改变 |
| B11 | 注销事件 UNVERIFIED 且六个验证字段为 null | 校验 local / integrated | local 通过；integrated 报 `integration.account_deletion.status`；其中一个字段非 null 时 local 报该字段 |
| B12 | 注销事件 VERIFIED 但缺来源、送达语义或执行证据中任一项 | 校验 integrated | 报对应字段路径，不接受只改状态 |
| B13 | 注销事件 event_kind 为 sign_out，或送达语义不在枚举内 | 校验 integrated | 报 `integration.account_deletion.source.event_kind` 或 `integration.account_deletion.delivery_semantics` |
| B14 | ports 缺一个名字、symbol 写成行号、file 不存在 | 校验 local | 分别报 `ports`、`ports[<名>].symbol`、`ports[<名>].file` |
| B15 | 同目录 INTEGRATION_BASELINE.md 含 TBD 或待定，或该文件不存在 | 校验 local | 报 `INTEGRATION_BASELINE.md` |
| B16 | dependencies 或 sdk 版本与契约固定值不同，或 dependencies 多出一个键 | 校验 local | 报 `dependencies.<键>`、`sdk.<键>` 或 `dependencies` |
| B17 | integration 下某对象为未验证态，但验证字段已填值 | 校验 local | 报该验证字段路径，拒绝半填冒充 |
| B18 | integration 下某对象为未验证态，但验证字段已填值 | 校验 integrated | 同时报该验证字段路径与 `<对象>.status`；§4 状态闸门不抑制 §3 的半填报告 |
| B19 | 完整验证态夹具中：设备少于两台、device_id 重复或无 P2P 对端；账号对含 token 键；test_runs 缺 SPEC 一条 | 校验 integrated | 分别只报 `integration.devices`、`integration.account_pairs`、`integration.test_runs` |
| B20 | scope=TEST_FIXTURE 且其余同 B01 | 校验 local | 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS (TEST_FIXTURE)` |
| B21 | 类型、枚举或固定值错误：schema_version 为 bool、head 非 40 位小写 hex、dirty_entries 为 bool 或负数、write_policy/kind/choice/status 不在枚举、NOTIFIER 允许写入、MIGRATION 状态不是 UNAVAILABLE、openapi_validator 五个固定值任一不等、emulator 常驻字段为空、account_deletion.consumer/blocked_scope 不等、client/identity/sdk/dependency_policy 固定值不等、仓库或端口集合缺项或重复 | 校验 local | 退出 1，报对应键的完整路径（集合问题只报数组路径） |
| B22 | JSON 根不是 object（`[]`、`"x"`、`null`） | 校验 local / integrated | 退出 1，stdout 恰为一行 `root` |
| B23 | 完整验证态夹具中 §4 取值规则任一被改坏：namespace_prefix 不匹配正则、credential_injection 不是 RUNTIME_ENV_VAR、project_id 或 start_command 为空、content_mute/aggregation 不在枚举、某容器类型错误（sdk 为数组、devices 为对象） | 校验 integrated | 退出 1，stdout 恰为对应的一行路径 |
