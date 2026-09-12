# NC-009 独立验收

当前：NOT_EXECUTED。派发前置：NC-003 ACCEPTED（含 act/06，2026-09-11 已满足）；`functions-py/.venv` 已重建，基线 411 passed / 5 failed，5 个既有失败名称与 README 一致，验收比较失败用例名称集合。

1. ACT 审查：未参与编写者做 wjt-react 四查。
2. 范围：SERVER 恰 4 个提交（`30a868c` 之后），只含各 ACT WRITE_NEW；`config.py/main.py/conftest.py` 的 diff 只有追加行；`idempotency.py/playground_rest.py/notifications.py` 零改动；RULES 仓恰 1 个提交且只含一个 TS 测试文件。
3. 重跑 TDD §1 全部命令（Emulator）；`nc009_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时测试，不入库）：① 直接查 Emulator 集合：publish 后 `community_commands` 文档字段与 NC-002 Schema 用 jsonschema 校验通过；② 同一 `command_id` 两个不同 scope 各自成功（键含 scope）；③ 在事务回调内注入 Firestore 竞争（另一事务先改 access.version）→ 自动重跑后结果仍唯一且 outbox 只一条；④ 4 种失效原因（withdrawn/trashed/hidden + 未发布）对 R1 的 404 体做字节级 diff；⑤ `compact_once` 对未到期文档零改动；⑥ R6 游标篡改 → 400 `invalid_argument.cursor`；⑦ 读 `community_pseudonym_mappings` 与事件表：假名不可由 scope 哈希重算，事件无账号字段。
5. 作弊扫描：测试无 `skip`、无 `status in (`；ACL xfail 计数恰 9 且 `strict=True`；无内存 fake；`with_idempotency` 未出现在 `xuan/community/`。
6. 通过后：NC-009 `ACCEPTED`；NC-010（客户端列表/发布页）与 NC-011（评论）可派发。
