# NC-001-01 验证计划

工作目录固定 `/Users/jingtaiwei/Git/Public/learn_system`。测试仅Python标准库；不读取凭据、不连Emulator。

## 命令

1. `python3 -m unittest discover -s openspec/annotation-community/tools -p test_check_integration_baseline.py -v`
2. `python3 openspec/annotation-community/tools/check_integration_baseline.py --profile local --input openspec/annotation-community/integration_baseline.json` → 0，LOCAL_PREPARATION_PASS。
3. 同一命令将 profile 改为 integrated → 1，至少包含 devices/account_pairs/rules/notifier_binding/test_runs/resolution_status 的失败路径，不能输出 PASS。
4. `LC_ALL=C bash openspec/annotation-community/review_final_guard.sh` → 0。
5. `bash openspec/annotation-community/verify.sh` → 0；`git diff --check` → 0。

## 真实 Red→Green

先新建测试文件，使用 tempfile.TemporaryDirectory 构造独立输入与存在性证据，通过 subprocess.run([sys.executable, checker, ...], capture_output=True, text=True) 调用CLI。先运行命令1，确认至少B01因缺checker/无预期输出失败；不能把0 tests或环境错误当行为Red。随后实现checker，再跑全部案例。若测试发现阶段就失败，先修测试发现再记录Red。

测试方法至少包含：test_local_planned_pass、test_integrated_current_rejected、test_missing_fields（每必填字段subTest）、test_missing_parent、test_missing_creation_owner、test_existing_empty_directory_rejected、test_missing_sdk_evidence、test_fake_test_pass_rejected、test_new_identity_rejected、test_book_scope_rejected、test_bad_json_exit2、test_unknown_profile_exit2、test_integrated_fixture_structure_pass、test_inputs_unchanged。

完整联调fixture必须在临时目录生成两个不同device_id、两个uid/appUserId映射、规则证据文件、已验证通知绑定证据、EXISTING客户端pubspec/lib、解析成功证据、全部外部仓库测试记录（command、exit_code=0、count>0、evidence文件）。各删除一个证据应失败。测试fixture的status必须标 TEST_FIXTURE；生产输入不能使用此状态求真实联调验收。checker仅验证结构，不验证云端真实性；ACCEPTANCE由人复核真实证据。

禁止测试从被测checker生成预期值；不得把“有字段”当作测试通过记录。CLI错误字段路径按JSON路径写明，如 integration.devices；排序输出保证可对比。
