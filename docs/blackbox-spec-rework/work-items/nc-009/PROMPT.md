# NC-009 执行提示

发送前提：wjt-react 四查 READY；**NC-003 与其补丁 act/06 已 ACCEPTED**；磁盘已清理且 `functions-py/.venv` 由主 Agent 重建、README 基线已填；SUBAGENT_TODO 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-009：在 canonical SERVER 仓库 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`（git 根即此目录；`xuan-migration/xuan-server/server/functions-py` 是过期副本，绝不写）内实现注解社区的命令账本服务、发布/收回/回收站命令、详情/列表/命令查询端点、ACL 扫描与规则单测。测试跑在局域网 Emulator：`export XUAN_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`，Python 用 `.venv/bin/python`（不重装依赖）。规则单测在 RULES 仓 `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server/server/functions/`（git 根 `xuan-migration/xuan-server`），只新增 `test/community_rules.test.ts`。

**先读（按顺序）**：`/Users/jingtaiwei/Git/Public/learn_system/AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-009/` 下 README.md、BDD.md、TDD.md、ACT.yaml、act/01～04.yaml、ACCEPTANCE.md；`openspec/annotation-community/contracts/community_server.md`（全文）与 `community_api.md`（§2～§7）；SERVER 的 `xuan/identity.py`、`errors.py`、`config.py`、`handlers/playground_rest.py`（只读参考）、`tests/conftest.py`、`tests/test_playground_rest_writes.py`（只读参考 `create_test_id_token`）。

**既有失败基线**：`pytest tests -q` 在开工前即为 `411 passed, 5 failed`，5 个失败是 `tests/test_config.py::test_集合名与_ts_逐项一致` 与 `tests/test_registration.py` 的 `test_全部_callable_已在入口注册`、`test_三个_trigger_已注册`、`test_与_入口总数对齐`、`test_没有多余的未声明导出`；它们与本任务无关，**不要修改这两个测试文件**；每步只要求失败集合与这 5 个名称完全相同，最终 `450 passed, 5 failed, 9 xfailed`。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文（贴入报告），再实现。

**只允许写**：各 ACT 的 WRITE_NEW 清单。禁止：learn_system 任何写入；`idempotency.py`、`playground_rest.py`、`notifications.py`、`firestore.rules`；用 `with_idempotency` 包社区命令；事务回调内上传/推送/sleep；`skip`；`assert status in (...)`；内存 fake 代替 Emulator；新增依赖。

**判据来源**：只来自两份契约与 TDD/BDD。契约两种解释、Emulator 不可达、`.venv` 缺失、需要改 `firestore.rules` 或既有 handler：立即停止并原样报告。

**提交**：SERVER 四步各一个提交，RULES 一个提交，只 `git add` 本步文件，不 push。提交消息按 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**写入 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-009/DELIVERY_REPORT.md`（不 git add），每步一节：commit 哈希与 `git show --stat`；Red 原文；VERIFICATION 每条命令退出码与末 20 行；act/04 另附 `pytest tests -q` 末 5 行（含 xfailed 计数）、`npm test -- community_rules` 末 10 行、`nc009_guard.sh --require-impl` 退出码；跳过项与剩余风险。不要把附件发布、清理执行、评论、通知说成完成。


# NC-009 act/05 返工执行提示（2026-09-11 验收后追加）

发送前提：act/01～04 已提交（SERVER `c29a31a`…`55f3980`，RULES `ea8c9b8`）。把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-009 的返工步 act/05：在 canonical SERVER 仓库 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`（git 根即此目录；过期副本 `xuan-migration/xuan-server/server/functions-py` 绝不写；learn_system 只读）以 `55f3980` 为基线修三处缺陷。测试跑 Emulator：`export XUAN_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`。

**先读**：`/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-009/act/05.yaml`、`TDD.md` §5b、`BDD.md` B31～B37、`ACCEPTANCE.md` 末尾「验收记录 R1」；契约 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/contracts/community_server.md` §10 全文（逐字照做）。

**要做的事**：① `requirements.txt` 追加 `jsonschema==4.26.0` 并 `.venv/bin/python -m pip install jsonschema==4.26.0`（本任务唯一允许的新依赖）；② 把 `/Users/jingtaiwei/Git/Public/learn_system/openspec/schemas/community_*.schema.json` 12 份文件逐字节复制到 `xuan/community/schemas/`，新建 `xuan/community/validation.py` 按 §10.1 组装快照 Schema 校验；③ W1/W2 载荷阶段按 §10.1 固定顺序插入 mentions 超 50（413）、快照 Schema（400，`field` 为 JSON Pointer）、content_hash hex64（400）；④ 畸形 `If-Match`（不匹配 `^"[0-9]+"$`）在调用 `run_command` 前返回 400 `invalid_argument.if_match`，不写账本；⑤ 503 的 `detail` 改为固定文案、日志只记异常类名与 command_id；⑥ 按 §10.4 把 `tests/test_community_publications.py`、`tests/test_community_acl_sweep.py` 里的非法绑定改为合法取值（只改取值）。

**既有失败基线**：全量 `pytest tests -q` 当前为 `450 passed, 5 failed, 9 xfailed`，5 个失败是 `test_config.py::test_集合名与_ts_逐项一致` 与 `test_registration.py` 的 4 个用例，与本任务无关、不要修改；最终应为 `457 passed, 5 failed, 9 xfailed`。

**先写测试再改实现**：先写 `tests/test_community_validation.py` 的 7 个测试（名称逐字取 TDD §5b）并改绑定取值，对 `55f3980` 取得 Red 原文，再实现。

**只允许写**：act/05.yaml 的 WRITE_NEW 清单。禁止：learn_system 写入；其他 SERVER 文件；RULES 仓；jsonschema 以外的依赖；改 Schema 复制品内容；`skip`；二选一断言；改既有测试除绑定取值外的断言。

**判据**：契约 §10 与 TDD §5b。jsonschema 无法安装、复制品与规格不一致、需要改清单外文件：立即停止并原样报告。

**提交**：一个提交，只 `git add` 本步文件，不 push；提交消息按 act/05 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

**交付报告**：追加到 `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items/nc-009/DELIVERY_REPORT.md`（不 git add）：commit 哈希与 `git show --stat`；Red 命令/退出码/原文；VERIFICATION 每条命令的退出码与末 20 行；`nc009_guard.sh --require-impl` 退出码。另请**补上此前缺失的 act/04 Red 原文**（ACL 扫描与规则单测在实现前的失败输出；若当时未保存，如实写明）。
