# NC-001-01 验证计划

工作目录固定 `/Users/jingtaiwei/Git/Public/learn_system`。只用 Python 标准库；不读凭据、不连 Emulator、不访问网络。判据全部以 [VALIDATION_CONTRACT.md](VALIDATION_CONTRACT.md) 为准。

## 1. 分四步提交

| 步骤 | ACT | 实现范围 | 本步新增方法（累计） | 覆盖 BDD |
|---|---|---|---|---|
| 1 | [act/01.yaml](act/01.yaml) | `make_fixture`、CLI 与退出 2、契约 §2 顶层规则、§6 输出格式；`--profile integrated` 暂时退出 2，stderr 为 `integrated profile not implemented` | 5（5） | B01、B08、B10、B20、B22、B21（顶层部分） |
| 2 | [act/02.yaml](act/02.yaml) | 契约 §3 的 client、sdk、dependencies、dependency_policy、identity、openapi_validator、`INTEGRATION_BASELINE.md` 占位扫描 | 8（13） | B04、B05、B07、B15、B16、B21（对应对象） |
| 3 | [act/03.yaml](act/03.yaml) | 契约 §3 的 repositories、ports、integration 各对象；必填键全表 | 9（22） | B03、B11（local 部分）、B14、B17、B21（其余） |
| 4 | [act/04.yaml](act/04.yaml) | 契约 §4、§5、§7；删除步骤 1 的临时退出 2 | 10（32） | B02、B06、B09、B11（integrated 部分）、B12、B13、B18、B19、B23 |

每步的 Red 都以「本步新增方法」取得真实断言失败；前几步的方法在后续步骤必须保持绿。

## 2. 命令

1. `python3 -m unittest discover -s openspec/annotation-community/tools -p 'test_check_integration_baseline.py' -v` → 0。
2. `python3 openspec/annotation-community/tools/check_integration_baseline.py --profile local --input openspec/annotation-community/integration_baseline.json` → 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS`。
3. （步骤 4 起）同一命令改为 `--profile integrated` → 退出 1，stdout 与契约 §7 的 23 行逐字相同。
4. `LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh` → 0；`bash openspec/annotation-community/verify.sh` → 0；`git diff --check` → 0。开工基线（提交 `aadd1fc` 时实测）三者均为 0；其中前两条读取共享文件 `docs/blackbox-spec-rework/SUBAGENT_TODO.md`，`git diff --check` 覆盖整个工作树。任一失败时先运行 `git diff --stat`：失败来源不在本任务两个文件之内的，判为外部失败，只在报告中记录，不返工、不停工。`nc001_r2_guard.sh` 的 K01 失败同样按外部失败处理；其 K02～K11 失败仍按本任务失败停工。
5. （步骤 4 完成后）`bash docs/blackbox-spec-rework/reviews/nc001_r2_guard.sh --require-impl` → 0。

## 3. 测试文件与方法

测试文件：`openspec/annotation-community/tools/test_check_integration_baseline.py`。

公共夹具 `make_fixture(tmp)`：在 `tempfile.TemporaryDirectory()` 中写出一份键与当前 `integration_baseline.json` 完全相同的 JSON，把所有外部路径改到临时目录内（sdk.evidence、ports[].file、notification_presentation.file 各建一个空文件；client.path 指向临时父目录下尚不存在的子目录），同目录写一份不含占位的 `INTEGRATION_BASELINE.md`。单测不得依赖真实外部路径；真实输入只由命令 2、3 覆盖。每个证据字段使用各自独立的文件，删除一个文件只影响一个路径。

通过 `subprocess.run([sys.executable, CHECKER, ...], capture_output=True, text=True)` 调用，`CHECKER = Path(__file__).with_name("check_integration_baseline.py")`；断言退出码与 stdout 全文（「含」指按行拆分后包含；「恰为」指与整个 stdout 相等）。所有负例都断言退出码为 1，且 stdout 不含 `PASS`。

### 3.1 必填键全表（`test_missing_required_keys` 的唯一依据）

测试文件必须在模块顶层以字面量写出 `REQUIRED_KEY_PATHS = [...]`，内容恰为下列 103 条路径，顺序不限；`test_missing_required_keys` 对每条做一个 `subTest`：从夹具中删除该路径对应的键（数组元素按 `[名]` 定位），运行 local，断言退出 1 且 stdout 含该路径原文。守卫会核对这 103 个字符串逐一出现在测试文件中。

```text
schema_version
spec_version
task_id
scope
book_work
resolution_status
resolution_evidence
client
sdk
dependencies
dependency_policy
identity
openapi_validator
integration
repositories
ports
client.path
client.package
client.state
client.creation_owner
client.vcs
client.runtime_verified
sdk.flutter
sdk.dart
sdk.evidence
sdk.verification
dependencies.flutter_markdown_plus
dependencies.drift
dependencies.drift_dev
dependencies.drift_flutter
dependencies.sqlite3
dependencies.sqlite3_flutter_libs
dependencies.path_provider
dependencies.build_runner
dependency_policy.offline_failure
dependency_policy.flutter_markdown_plus_rationale
identity.policy
identity.new_identity_system
identity.public_profile_id
openapi_validator.package
openapi_validator.version
openapi_validator.install_command
openapi_validator.offline_failure
openapi_validator.status
openapi_validator.evidence
repositories[SPEC].path
repositories[SPEC].write_policy
repositories[SPEC].git_root
repositories[SPEC].head
repositories[SPEC].dirty_entries
repositories[SPEC].tests
repositories[SPEC].tests.status
repositories[SPEC].tests.reason
repositories[MIGRATION].path
repositories[MIGRATION].status
repositories[MIGRATION].write_policy
ports[HTTP].file
ports[HTTP].symbol
ports[HTTP].kind
integration.devices
integration.account_pairs
integration.test_runs
integration.backend
integration.emulator
integration.rules
integration.notifier_binding
integration.notification_presentation
integration.mute_aggregation
integration.account_deletion
integration.backend.status
integration.backend.project_id
integration.backend.namespace_prefix
integration.backend.credential_injection
integration.backend.evidence
integration.emulator.firestore_config
integration.emulator.auth_config
integration.emulator.project_config
integration.emulator.status
integration.emulator.start_command
integration.emulator.evidence
integration.rules.status
integration.rules.path
integration.rules.evidence
integration.notifier_binding.status
integration.notifier_binding.evidence
integration.notification_presentation.choice
integration.notification_presentation.file
integration.notification_presentation.symbol
integration.notification_presentation.status
integration.notification_presentation.evidence
integration.mute_aggregation.status
integration.mute_aggregation.content_mute
integration.mute_aggregation.aggregation
integration.mute_aggregation.evidence
integration.account_deletion.status
integration.account_deletion.source
integration.account_deletion.delivery_semantics
integration.account_deletion.test_command
integration.account_deletion.exit_code
integration.account_deletion.count
integration.account_deletion.evidence
integration.account_deletion.consumer
integration.account_deletion.blocked_scope
```

另有 2 个定位键用例并入同一方法：删除 `repositories[SPEC]` 的 `name` 键 → 含 `repositories`；删除 `ports[HTTP]` 的 `name` 键 → 含 `ports`。

### 3.2 步骤 1 的 5 个方法

| 方法 | 断言 |
|---|---|
| test_local_fixture_pass | 夹具 local 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS\n`（B01） |
| test_local_test_fixture_suffix | 夹具 scope 改为 `TEST_FIXTURE`，local 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS (TEST_FIXTURE)\n`（B20） |
| test_cli_errors_exit2 | JSON 语法错误、`--input` 指向不存在文件、缺 `--profile`、`--profile foo` 四例：退出 2，stdout 为空，stderr 不含 `Traceback`（B08） |
| test_root_not_object | 输入文件内容分别为 `[]`、`"x"`、`null` 三例（subTest）：local 退出 1，stdout 恰为 `root\n`（B22） |
| test_top_level_values | subTest：schema_version=true 含 `schema_version`；schema_version="1" 含 `schema_version`；spec_version="1.4" 含 `spec_version`；task_id="NC-002" 含 `task_id`；scope="X" 含 `scope`；book_work="ACTIVE" 含 `book_work`；resolution_status="DONE" 含 `resolution_status`；resolution_status="RESOLVED" 且 resolution_evidence=null 含 `resolution_evidence`；resolution_status="RESOLVED" 且 resolution_evidence 指向不存在文件含 `resolution_evidence`；client=[] 恰为 `client\n`（父级不是 object 只报父级）（B21、B07 的 book_work 部分） |

### 3.3 步骤 2 的 8 个方法

| 方法 | 断言 |
|---|---|
| test_planned_new_rules | creation_owner 改为 NC-005、父目录不存在、path 已存在三例，分别含 `client.creation_owner`、`client.path`、`client.state`；运行后临时目录列表不变（B04） |
| test_existing_client_rules | state=EXISTING 时分别缺 pubspec.yaml、lib、.git，均含 `client.path`（B05） |
| test_client_and_identity_values | subTest：client.package="notes" 含 `client.package`；client.state="OTHER" 含 `client.state`；client.vcs="SUBMODULE" 含 `client.vcs`；client.runtime_verified="no" 含 `client.runtime_verified`；client.path="" 含 `client.path`；sdk.verification="X" 含 `sdk.verification`；sdk.dart="3.12.3" 含 `sdk.dart`；identity.policy="X" 含 `identity.policy`；identity.public_profile_id="" 含 `identity.public_profile_id`；dependency_policy.offline_failure="IGNORE" 含 `dependency_policy.offline_failure`；dependency_policy.flutter_markdown_plus_rationale="" 含该路径（B21） |
| test_sdk_evidence_missing | 删除 sdk.evidence 指向的文件，含 `sdk.evidence`（B05） |
| test_pins_rules | drift 改为 2.34.0 含 `dependencies.drift`；多加一个键含 `dependencies`；sdk.flutter 改为 3.44.7 含 `sdk.flutter`（B16） |
| test_identity_and_book_rejected | new_identity_system=true 含 `identity.new_identity_system`；new_identity_system="false"（字符串）含同路径；book_work=ACTIVE 含 `book_work`（B07） |
| test_openapi_validator_rules | subTest：package="x" 含 `openapi_validator.package`；version="0.8.0" 含 `openapi_validator.version`；install_command="" 含 `openapi_validator.install_command`；offline_failure="IGNORE" 含 `openapi_validator.offline_failure`；status="INSTALLED" 含 `openapi_validator.status`；status 保持未验证态但 evidence="x" 含 `openapi_validator.evidence`（B21） |
| test_placeholder_rules | MD 追加 `TBD` 含 `INTEGRATION_BASELINE.md`；MD 追加 `待定` 含同路径；删除 MD 同样含该路径（B15） |

### 3.4 步骤 3 的 9 个方法

| 方法 | 断言 |
|---|---|
| test_missing_required_keys | 按 §3.1 全表 103 条 + 2 个定位键用例（B03） |
| test_repositories_rules | subTest：SPEC head="ABC" 含 `repositories[SPEC].head`；head 为 40 位大写 hex 含同路径；dirty_entries=true 含 `repositories[SPEC].dirty_entries`；dirty_entries=-1 含同路径；write_policy="WRITE_ALL" 含 `repositories[SPEC].write_policy`；NOTIFIER write_policy="PER_TASK_WHITELIST" 含 `repositories[NOTIFIER].write_policy`；MIGRATION status="AVAILABLE" 含 `repositories[MIGRATION].status`；MIGRATION write_policy="PER_TASK_WHITELIST" 含 `repositories[MIGRATION].write_policy`；SPEC tests.status="SKIPPED" 含 `repositories[SPEC].tests.status`；tests.status=NOT_RUN 且 reason="" 含 `repositories[SPEC].tests.reason`；删除 STORAGE 整条恰为 `repositories\n`；SPEC 整条复制一份恰为 `repositories\n`；某条替换为字符串 `"x"` 恰为 `repositories\n`（B21） |
| test_ports_rules | 删除 MENTION 条目恰为 `ports\n`；HTTP 的 symbol 写成 `42` 含 `ports[HTTP].symbol`；symbol 写成 `a.dart:42` 含同路径；HTTP 的 file 指向不存在文件含 `ports[HTTP].file`；HTTP kind="MOCK" 含 `ports[HTTP].kind`；HTTP 整条复制一份恰为 `ports\n`（B14、B21） |
| test_emulator_constants | subTest：firestore_config="" 含 `integration.emulator.firestore_config`；auth_config=null 含 `integration.emulator.auth_config`；project_config=123 含 `integration.emulator.project_config`；status="RUNNING" 含 `integration.emulator.status`（B21） |
| test_notification_presentation_rules | subTest：choice="OTHER" 含 `integration.notification_presentation.choice`；file 指向不存在文件含 `.file` 全路径；symbol="42" 含 `.symbol` 全路径；status="DONE" 含 `.status` 全路径（B21） |
| test_account_deletion_constants | subTest：consumer="NC-025" 含 `integration.account_deletion.consumer`；blocked_scope="X" 含 `integration.account_deletion.blocked_scope`；status="DONE" 含 `integration.account_deletion.status`（B21） |
| test_account_deletion_unverified_local | 当前形态 local 通过；test_command 改为 `"x"` 后含 `integration.account_deletion.test_command`（B11） |
| test_half_filled_unverified_rejected | subTest：rules.status=UNVERIFIED 但 path="x" 含 `integration.rules.path`；backend.status=UNVERIFIED 但 project_id="p" 含 `integration.backend.project_id`；mute_aggregation.status=UNVERIFIED 但 aggregation="SUPPORTED" 含 `integration.mute_aggregation.aggregation`；backend.status="VERIFYING"（非枚举）含 `integration.backend.status`（B17、B21） |
| test_inputs_unchanged | 分别运行 local 与 integrated 前后，JSON 与 MD 的 sha256 相同，临时目录文件列表相同；本方法只断言哈希与目录列表，不断言两次运行的退出码或 stdout（B10） |

### 3.5 步骤 4 的 10 个方法

| 方法 | 断言 |
|---|---|
| test_integrated_current_golden | 夹具（scope 与各状态保持当前输入的值）integrated 退出 1，stdout 与契约 §7 的 23 行逐字相同；期望值在测试文件中以字面量写出（B02、B11） |
| test_integrated_fixture_pass | 把夹具补成完整验证态：scope=TEST_FIXTURE；client 为 EXISTING 并建 pubspec.yaml、lib、.git；全部对象为验证态并配证据文件；两台设备（一台 p2p_peer=true）、两组账号；7 条 test_runs 与 7 个 PASSED tests；resolution_status=RESOLVED 且 resolution_evidence 为存在文件；sdk.verification=RUNTIME_VERIFIED；runtime_verified=true；openapi_validator.status=VERIFIED 并配证据文件。完整夹具的取值必须在测试文件中逐字写死：backend.project_id=`"demo-xuan-test"`、namespace_prefix=`"nc_20260910_ab12cd"`、credential_injection=`"RUNTIME_ENV_VAR"`；emulator.start_command=`"firebase emulators:start --only firestore,auth"`；mute_aggregation.content_mute=`"SUPPORTED"`、aggregation=`"UNSUPPORTED_E_WIRING"`；account_deletion.source=`{"file": "<临时文件路径>", "symbol": "AuthCoordinator.deleteAccount", "event_kind": "ACCOUNT_DELETED"}`、delivery_semantics=`"AT_LEAST_ONCE"`、test_command=`"python3 -m unittest"`、exit_code=0、count=1；每条 test_runs 与 tests 的 command=`"flutter test"`、exit_code=0、count=1。退出 0，stdout 恰为 `INTEGRATED_STRUCTURE_PASS (TEST_FIXTURE)\n`（B09） |
| test_integrated_fixture_evidence_removed | 在完整夹具上逐个删除证据文件（subTest），每例退出 1 且 stdout 恰为对应的一行路径：删 backend 证据 → `integration.backend.evidence`；emulator → `integration.emulator.evidence`；rules.path 指向的文件 → `integration.rules.path`；rules.evidence → `integration.rules.evidence`；notifier_binding → `integration.notifier_binding.evidence`；notification_presentation → `integration.notification_presentation.evidence`；mute_aggregation → `integration.mute_aggregation.evidence`；openapi_validator → `openapi_validator.evidence`；account_deletion → `integration.account_deletion.evidence`；repositories[STORAGE].tests → `repositories[STORAGE].tests.evidence`；integration.test_runs[SERVER] → `integration.test_runs[SERVER].evidence` |
| test_fake_test_pass_rejected | 当前夹具中把 repositories[STORAGE].tests.status 改为 PASSED，stdout 含该记录的 `.command`、`.count`、`.evidence`、`.exit_code`；在完整夹具上把 exit_code 改为 true，含 `repositories[STORAGE].tests.exit_code`；把 count 改为 0，含 `repositories[STORAGE].tests.count`（B06） |
| test_integrated_half_filled_unverified | 当前形态夹具中 rules.status=UNVERIFIED 但 path="x"，integrated 退出 1，stdout 同时含 `integration.rules.path` 与 `integration.rules.status`（B18） |
| test_account_deletion_verified_missing_fields | 完整夹具中逐个把六个验证字段置 null（subTest），含对应路径（B12） |
| test_account_deletion_kind_and_delivery_rejected | event_kind=`sign_out` 含 `integration.account_deletion.source.event_kind`；delivery_semantics=`BEST_EFFORT` 含 `integration.account_deletion.delivery_semantics`；source="x"（非 object）含 `integration.account_deletion.source`（B13） |
| test_devices_and_pairs_rules | 完整夹具中：只剩 1 台设备、两台 device_id 相同、全部 p2p_peer=false、某台 p2p_peer="yes" 四例均恰为 `integration.devices\n`；一组账号加 token 键、两组 uid 相同两例均恰为 `integration.account_pairs\n`（B19） |
| test_test_runs_set_rules | 完整夹具删除 SPEC 那条 test_runs，stdout 恰为 `integration.test_runs\n`；SERVER 那条 exit_code=1，stdout 恰为 `integration.test_runs[SERVER].exit_code\n`；SERVER 那条 command=""，恰为 `integration.test_runs[SERVER].command\n`；SERVER 那条 count=0，恰为 `integration.test_runs[SERVER].count\n`（B19） |
| test_integrated_value_rules | 在完整夹具上逐项改坏 §4 的取值规则（subTest），每例退出 1 且 stdout 恰为对应的一行路径：namespace_prefix=`"nc_2026_ab"` → `integration.backend.namespace_prefix`；namespace_prefix=`"NC_20260910_ab12"` → 同路径；credential_injection=`"FILE"` → `integration.backend.credential_injection`；project_id=`""` → `integration.backend.project_id`；start_command=`""` → `integration.emulator.start_command`；content_mute=`"YES"` → `integration.mute_aggregation.content_mute`；aggregation=`"PARTIAL"` → `integration.mute_aggregation.aggregation`；sdk 改为 `[]` → `sdk`；integration.devices 改为 `{}` → `integration.devices`（B23） |

方法总数 32（5 + 8 + 9 + 10），名称不得重复；守卫按本节表格核对。

## 4. Red→Green

- 每步先写该步的测试，再建一个只解析参数、恒 `sys.exit(0)` 的空壳（步骤 2 起沿用上一步的实现），运行命令 1，记录非 0 退出码与至少一条本步新增方法的真实断言失败原文，作为 Red。0 tests、ImportError、语法错误、文件不存在导致的退出 2 都不算 Red。
- 然后实现，运行命令 1～4（步骤 4 加命令 3、5），作为 Green。空壳不单独提交。
- 禁止：skip、永真断言、从 checker 输出或本文件生成期望值、捕获异常后放行、为了通过测试修改 JSON、MD 或契约。
