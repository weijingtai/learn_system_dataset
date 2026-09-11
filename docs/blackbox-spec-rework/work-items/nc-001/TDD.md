# NC-001-01 验证计划

工作目录固定 `/Users/jingtaiwei/Git/Public/learn_system`。只用 Python 标准库；不读凭据、不连 Emulator、不访问网络。判据全部以 [VALIDATION_CONTRACT.md](VALIDATION_CONTRACT.md) 为准。

## 1. 分两步提交

| 步骤 | ACT | 实现范围 | 覆盖 BDD |
|---|---|---|---|
| 1 | [act/01.yaml](act/01.yaml) | CLI 与退出 2、契约 §1～§3 与 §6、local 档输出；本步 `--profile integrated` 暂时退出 2，stderr 为 `integrated profile not implemented` | B01、B03、B04、B05、B07、B08、B10、B11（local 部分）、B14、B15、B16、B17 |
| 2 | [act/02.yaml](act/02.yaml) | 契约 §4、§5、§7；删除步骤 1 的临时退出 2 | B02、B06、B09、B11（integrated 部分）、B12、B13 |

## 2. 命令

1. `python3 -m unittest discover -s openspec/annotation-community/tools -p 'test_check_integration_baseline.py' -v` → 0。
2. `python3 openspec/annotation-community/tools/check_integration_baseline.py --profile local --input openspec/annotation-community/integration_baseline.json` → 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS`。
3. （步骤 2 起）同一命令改为 `--profile integrated` → 退出 1，stdout 与契约 §7 的 23 行逐字相同。
4. `LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh` → 0；`bash openspec/annotation-community/verify.sh` → 0；`git diff --check` → 0。
5. （步骤 2 完成后）`bash docs/blackbox-spec-rework/reviews/nc001_r1_guard.sh --require-impl` → 0。

## 3. 测试文件与方法

测试文件：`openspec/annotation-community/tools/test_check_integration_baseline.py`。

公共夹具 `make_fixture(tmp)`：在 `tempfile.TemporaryDirectory()` 中写出一份键与当前 `integration_baseline.json` 完全相同的 JSON，把所有外部路径改到临时目录内（sdk.evidence、ports[].file、notification_presentation.file 各建一个空文件；client.path 指向临时父目录下尚不存在的子目录），同目录写一份不含占位的 `INTEGRATION_BASELINE.md`。单测不得依赖真实外部路径；真实输入只由命令 2、3 覆盖。每个证据字段使用各自独立的文件，删除一个文件只影响一个路径。

通过 `subprocess.run([sys.executable, CHECKER, ...], capture_output=True, text=True)` 调用，`CHECKER = Path(__file__).with_name("check_integration_baseline.py")`；断言退出码与 stdout 全文（「含」指按行拆分后包含）。

步骤 1 的 13 个方法：

| 方法 | 断言 |
|---|---|
| test_local_fixture_pass | 夹具 local 退出 0，stdout 恰为 `LOCAL_PREPARATION_PASS\n`（B01） |
| test_missing_required_keys | 契约 §2～§3 每个必填键逐个删除（subTest），退出 1 且 stdout 含该键路径（B03） |
| test_planned_new_rules | creation_owner 改为 NC-005、父目录不存在、path 已存在三例，分别含 `client.creation_owner`、`client.path`、`client.state`；运行后临时目录列表不变（B04） |
| test_existing_client_rules | state=EXISTING 时分别缺 pubspec.yaml、lib、.git，均含 `client.path`（B05） |
| test_sdk_evidence_missing | 删除 sdk.evidence 指向的文件，含 `sdk.evidence`（B05） |
| test_pins_rules | drift 改为 2.34.0 含 `dependencies.drift`；多加一个键含 `dependencies`；sdk.flutter 改为 3.44.7 含 `sdk.flutter`（B16） |
| test_identity_and_book_rejected | new_identity_system=true 含 `identity.new_identity_system`；book_work=ACTIVE 含 `book_work`（B07） |
| test_cli_errors_exit2 | JSON 语法错误、`--input` 指向不存在文件、缺 `--profile`、`--profile foo` 四例：退出 2，stdout 为空，stderr 不含 `Traceback`（B08） |
| test_inputs_unchanged | 运行 local 前后，JSON 与 MD 的 sha256 相同，临时目录文件列表相同（B10） |
| test_account_deletion_unverified_local | 当前形态 local 通过；test_command 改为 `"x"` 后含 `integration.account_deletion.test_command`（B11） |
| test_ports_rules | 删除 MENTION 条目含 `ports`；HTTP 的 symbol 写成 `42` 含 `ports[HTTP].symbol`；HTTP 的 file 指向不存在文件含 `ports[HTTP].file`（B14） |
| test_placeholder_rules | MD 追加 `TBD` 含 `INTEGRATION_BASELINE.md`；删除 MD 同样含该路径（B15） |
| test_half_filled_unverified_rejected | rules.status=UNVERIFIED 但 path 为 `"x"`，含 `integration.rules.path`（B17） |

步骤 2 的 8 个方法：

| 方法 | 断言 |
|---|---|
| test_integrated_current_golden | 夹具（scope 与各状态保持当前输入的值）integrated 退出 1，stdout 与契约 §7 的 23 行逐字相同；期望值在测试文件中以字面量写出（B02、B11） |
| test_integrated_fixture_pass | 把夹具补成完整验证态：scope=TEST_FIXTURE；client 为 EXISTING 并建 pubspec.yaml、lib、.git；全部对象为验证态并配证据文件；两台设备（一台 p2p_peer=true）、两组账号；7 条 test_runs 与 7 个 PASSED tests；resolution_status=RESOLVED；sdk.verification=RUNTIME_VERIFIED；runtime_verified=true。退出 0，stdout 恰为 `INTEGRATED_STRUCTURE_PASS (TEST_FIXTURE)\n`（B09） |
| test_integrated_fixture_evidence_removed | 在完整夹具上逐个删除证据文件（subTest：backend、emulator、rules.path、rules.evidence、notifier_binding、notification_presentation、mute_aggregation、openapi_validator、account_deletion、repositories[STORAGE].tests、integration.test_runs[SERVER]），每例退出 1 且 stdout 恰为对应的一行路径 |
| test_fake_test_pass_rejected | 当前夹具中把 repositories[STORAGE].tests.status 改为 PASSED，stdout 含该记录的 `.command`、`.count`、`.evidence`、`.exit_code`；在完整夹具上把 exit_code 改为 true，含 `repositories[STORAGE].tests.exit_code`（B06） |
| test_account_deletion_verified_missing_fields | 完整夹具中逐个把六个验证字段置 null（subTest），含对应路径（B12） |
| test_account_deletion_kind_and_delivery_rejected | event_kind=`sign_out` 含 `integration.account_deletion.source.event_kind`；delivery_semantics=`BEST_EFFORT` 含 `integration.account_deletion.delivery_semantics`（B13） |
| test_devices_and_pairs_rules | 完整夹具中：只剩 1 台设备、两台 device_id 相同、全部 p2p_peer=false 三例均含 `integration.devices`；一组账号加 token 键含 `integration.account_pairs` |
| test_test_runs_set_rules | 完整夹具删除 SPEC 那条 test_runs，stdout 恰为 `integration.test_runs` |

## 4. Red→Green

- 每步先写该步的测试，再建一个只解析参数、恒 `sys.exit(0)` 的空壳（步骤 2 沿用步骤 1 的实现），运行命令 1，记录非 0 退出码与至少一条真实断言失败原文，作为 Red。0 tests、ImportError、语法错误、文件不存在导致的退出 2 都不算 Red。
- 然后实现，运行命令 1～4（步骤 2 加命令 5），作为 Green。空壳不单独提交。
- 禁止：skip、永真断言、从 checker 输出或本文件生成期望值、捕获异常后放行、为了通过测试修改 JSON、MD 或契约。
