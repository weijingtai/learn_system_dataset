# NC-009 执行提示

发送前提：wjt-react 四查 READY；**NC-003 已 ACCEPTED**；磁盘已清理且 `functions-py/.venv` 由主 Agent 重建、README 基线已填；SUBAGENT_TODO 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-009：在 canonical SERVER 仓库 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`（git 根即此目录；`xuan-migration/xuan-server/server/functions-py` 是过期副本，绝不写）内实现注解社区的命令账本服务、发布/收回/回收站命令、详情/列表/命令查询端点、ACL 扫描与规则单测。测试跑在局域网 Emulator：`export XUAN_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`，Python 用 `.venv/bin/python`（不重装依赖）。规则单测在 RULES 仓 `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server/server/functions/`（git 根 `xuan-migration/xuan-server`），只新增 `test/community_rules.test.ts`。

**先读（按顺序）**：`/Users/jingtaiwei/Git/Public/learn_system/AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-009/` 下 README.md、BDD.md、TDD.md、ACT.yaml、act/01～04.yaml、ACCEPTANCE.md；`openspec/annotation-community/contracts/community_server.md`（全文）与 `community_api.md`（§2～§7）；SERVER 的 `xuan/identity.py`、`errors.py`、`config.py`、`handlers/playground_rest.py`（只读参考）、`tests/conftest.py`、`tests/test_playground_rest_writes.py`（只读参考 `create_test_id_token`）。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文（贴入报告），再实现。

**只允许写**：各 ACT 的 WRITE_NEW 清单。禁止：learn_system 任何写入；`idempotency.py`、`playground_rest.py`、`notifications.py`、`firestore.rules`；用 `with_idempotency` 包社区命令；事务回调内上传/推送/sleep；`skip`；`assert status in (...)`；内存 fake 代替 Emulator；新增依赖。

**判据来源**：只来自两份契约与 TDD/BDD。契约两种解释、Emulator 不可达、`.venv` 缺失、需要改 `firestore.rules` 或既有 handler：立即停止并原样报告。

**提交**：SERVER 四步各一个提交，RULES 一个提交，只 `git add` 本步文件，不 push。提交消息按 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。

**交付报告**（每步一节）：commit 哈希与 `git show --stat`；Red 原文；VERIFICATION 每条命令退出码与末 20 行；act/04 另附 `pytest tests -q` 末 5 行（含 xfailed 计数）、`npm test -- community_rules` 末 10 行、`nc009_guard.sh --require-impl` 退出码；跳过项与剩余风险。不要把附件发布、清理执行、评论、通知说成完成。
