# NC-009 独立验收

当前：`ACCEPTED`（2026-09-11 主 Agent 验收 R3，见文末；R1 为 REWORK_ACT05，R2 为 REWORK_ACT06）。派发前置：NC-003 ACCEPTED（含 act/06，2026-09-11 已满足）；`functions-py/.venv` 已重建，基线 411 passed / 5 failed，5 个既有失败名称与 README 一致，验收比较失败用例名称集合。

1. ACT 审查：未参与编写者做 wjt-react 四查。
2. 范围：SERVER 恰 4 个提交（`30a868c` 之后），只含各 ACT WRITE_NEW；`config.py/main.py/conftest.py` 的 diff 只有追加行；`idempotency.py/playground_rest.py/notifications.py` 零改动；RULES 仓恰 1 个提交且只含一个 TS 测试文件。
3. 重跑 TDD §1 全部命令（Emulator）；`nc009_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时测试，不入库）：① 直接查 Emulator 集合：publish 后 `community_commands` 文档字段与 NC-002 Schema 用 jsonschema 校验通过；② 同一 `command_id` 两个不同 scope 各自成功（键含 scope）；③ 在事务回调内注入 Firestore 竞争（另一事务先改 access.version）→ 自动重跑后结果仍唯一且 outbox 只一条；④ 4 种失效原因（withdrawn/trashed/hidden + 未发布）对 R1 的 404 体做字节级 diff；⑤ `compact_once` 对未到期文档零改动；⑥ R6 游标篡改 → 400 `invalid_argument.cursor`；⑦ 读 `community_pseudonym_mappings` 与事件表：假名不可由 scope 哈希重算，事件无账号字段。
5. 作弊扫描：测试无 `skip`、无 `status in (`；ACL xfail 计数恰 9 且 `strict=True`；无内存 fake；`with_idempotency` 未出现在 `xuan/community/`。
6. 通过后：NC-009 `ACCEPTED`；NC-010（客户端列表/发布页）与 NC-011（评论）可派发。


---

## 验收记录 R1（主 Agent，2026-09-11）：act/01～04 REWORK，追加 act/05

- 提交：SERVER `c29a31a`（A）、`74ea5c1`（B）、`00d5552`（C）、`55f3980`（D），RULES `ea8c9b8`；各提交只含对应 WRITE_NEW；`idempotency.py`、`playground_rest.py`、`notifications.py`、`test_config.py`、`test_registration.py`、`requirements.txt` diff 为空；`config.py`、`main.py`、`conftest.py` 只有追加行。
- 全量 `pytest tests -q`（Emulator）：`450 passed, 5 failed, 9 xfailed`；5 个失败名称与 README 基线逐一相同；9 个 xfail 均为 `strict=True` 且所有者为 NC-008/NC-012/NC-013。规则单测 `65 passed`。守卫 `nc009_guard.sh --require-impl` K01～K05 全 PASS。
- 交付报告 `work-items/nc-009/DELIVERY_REPORT.md`（未入库）：act/01～03 有 Red 原文；**act/04 缺 Red 原文**（只列 Green），需补。
- 源码审阅：账本事务先读账本与假名映射再执行业务，业务异常整笔回滚返回 503；`new_ids` 事务外生成；`server_event_id` 按 DESIGN §11.2；读路径 404 共用体为常量；非本人写入先 `resolve_access`（事务内读）；事务回调内无网络/推送/sleep。
- 盲测（Emulator，临时文件已删除）：
  - 通过：① 账本文档用 NC-002 `community_command_record.schema.json` 校验 VALID；② 同一 command_id 两个账号各自 201，账本两份；③ 四种失效（收回/回收站/隐藏/不存在）R1 404 体逐字节相同，带匹配的 `If-None-Match` 仍 404 不 304；④ `compact_once` 对未到期零改动、15 天后精简 1 条；⑤ R6 篡改游标两种形式均 400 `invalid_argument.cursor`；⑥ 假名不等于 `psn_`+SHA-256(scope)，事件 ID 等于 §11.2 公式，事件无账号字段；⑦ 两个并发 withdraw 同 If-Match 恰一个 200 一个 412，`content.withdrawn` outbox 恰 1 条；⑧ markdown 262144 字节 201、262145 字节 413；⑨ 服务端 `compute_payload_hash` 对 NC-010 契约 §8 输入得 `c8e2c2b0…b72b5`，与客户端参考值逐字相等。
  - **缺陷 1**：发布/更新不按 NC-002 Schema 校验快照——`bindings` 含 `relation: "cites"`、`target_kind: "passage"`（均不在枚举）返回 201 并写入公共关联索引；标题 201 个 code point 返回 201。违反契约 §4 W1「`snapshot` 通过 Schema」。
  - **缺陷 2**：`If-Match: abc` 解析为 -1 后按版本不符返回 412 `conflict.version`，应为 400 `invalid_argument.if_match`（community_api §3.2 头格式 `^"[0-9]+"$`；契约原文只写了「缺失 → 400」，畸形值未写明，主 Agent 契约缺口）。
  - **缺陷 3**：事务失败的 503 体 `detail` 为异常原文 `str(exc)`，可能泄露内部路径与数据片段。
- 契约缺口记录（不计本次返工）：拒绝终态的重放只返回 `code` 与状态，丢失 `current_version` 等附加字段（契约 §3.2 第 4 步规定 rejected 的 `result_fields` 为空）；DESIGN §7.4 第 4 条允许保留「必要非敏感错误字段」，留待 NC-011 复用账本时统一裁定。
- 判定：**REWORK**；契约 §10（D-NC009-15～17）+ act/05；act/05 通过后复跑缺陷 1～3 盲测与全量失败集合，再关闭 NC-009。

---

## 验收记录 R2（主 Agent，2026-09-11）：act/05 三处缺陷已修复，追加 act/06

- 提交：SERVER `52d8330`（E），`git diff-tree` 20 个文件，全部在 act/05 WRITE_NEW 内；工作树干净；`idempotency.py`、`playground_rest.py`、`notifications.py` 自 `30a868c` 零改动。
- 全量 `pytest tests -q`（Emulator，主 Agent 复跑）：`457 passed, 5 failed, 9 xfailed`；5 个失败名称与 README 基线相同。守卫 `nc009_guard.sh --require-impl` 失败条数 0。12 份 Schema 复制品与规格 `cmp` 全部一致。
- 交付报告：act/05 Red 原文 `7 failed`，红因与 TDD §5b 预期一致。act/04 Red 原文执行方如实说明未保存、只补了机制描述——接受，记为过程缺陷。
- 源码：`validation.py` 的快照 Schema 与 §10.1 字面量一致，Registry 注册 12 份；载荷顺序 ①～⑤ 与 §10.1 一致；handler 六个写入口均在 `run_command` 前预检 If-Match；503 文案逐字一致，`run_command` 日志只记类名与 command_id。
- 盲测（Emulator，临时文件已删除）：
  - 通过：① 51 个 mention 且绑定非法 → 413（① 先于 ②）；② 绑定非法且哈希非 hex64 → 400 snapshot，指针 `/snapshot/bindings/0/relation`；合法快照 + 大写哈希 → 400 content_hash；③ 标题 200 个 emoji → 201、201 个 → 400 `/snapshot/title`（按 code point 计）；④ 未知顶层键 → 400 `/snapshot`；⑤ 非法绑定被拒后无 access、无绑定文档，账本有记录，同键重放状态码相同；⑥ 已发布内容 W2 带 `target_kind: "passage"` → 400，access.version 仍为 1；⑦ W1～W6 × `W/"1"`、`""`、`"1a"`、`'1'` 共 24 次均 400 `invalid_argument.if_match` 且账本无记录；⑧ W3 事务抛含路径与中文的异常 → 503 固定文案，响应体与 DEBUG 级日志均不含异常文本。
  - **偏差 1**：执行方在 W1/W2 校验前给快照补 `attachments/mentions/bindings = []`，使 Schema 的 `required` 失效——快照只有 `title`、`markdown` 时返回 201（REST 仓 OpenAPI `PublicSnapshot.required` 含四键）；该取舍未停手上报。另 `dict(body.get("snapshot") or {})` 遇非对象快照会抛 ValueError，经事务变 503 而非 400。
  - **偏差 2**（§10.3 只写了 `run_command`，主 Agent 缺口）：社区代码另有 4 处日志仍写 `{exc}`。
  - 已知缺口复现（不计返工，仍留 NC-011）：拒绝终态重放丢失 `field` 附加字段。
- 判定：**REWORK**（小）；契约 §10.6（D-NC009-18～19）+ act/06；act/06 通过后复跑偏差 1、2 盲测与全量失败集合，关闭 NC-009。

---

## 验收记录 R3（主 Agent，2026-09-11）：act/06 通过，NC-009 ACCEPTED

- 提交：SERVER `df5c3da`（F），7 个文件均在 act/06 WRITE_NEW 内。逐文件对比 `52d8330`：`content_service.py` 两处只把默认值补齐与 `dict()` 换成 `body.get("snapshot")`；4 处日志只把 `{exc}` 换成 `{type(exc).__name__}`；`test_community_publications.py` 只补 `mentions`/`bindings` 空数组 6 处；`test_community_validation.py` 追加 2 个测试。
- 命令经 tmux + agy 执行（只运行、存原始输出于 `~/tmux-agents/runs/nc010v/`），主 Agent 读原始输出判定：全量 `459 passed, 5 failed, 9 xfailed`，5 个失败名称与基线相同；`nc009_guard.sh --require-impl` 失败条数 0；社区源码无 `{exc}`、`str(exc)`、`repr(exc)`、`exc_info`；工作树干净。
- 交付报告：act/06 Red 原文 `2 failed, 7 passed`，红因（201；caplog 含 `SECRET-LOG`）与 TDD §5c 一致。
- 盲测（主 Agent 编写，临时文件已删除）5 passed：① W1 快照缺必填键（两种）、字符串、空数组、null、数字、缺 `snapshot` 键共 7 种 → 均 400 `/snapshot` 且无 access 文档；② `mentions: "abc"` → 400 `/snapshot/mentions`；③ 51 个 mention 且缺 bindings → 413（① 先于 ②）；④ 已发布内容 W2 快照只有 title → 400 `/snapshot`，version 仍为 1；⑤ 命令查询 handler 身份解析抛含路径的异常 → 401，响应体与 DEBUG 日志均无异常文本。
- 遗留（不阻塞）：拒绝终态重放丢失 `field` 等附加字段，留 NC-011 复用账本时统一裁定。
- 判定：**ACCEPTED**。SERVER `c29a31a`→`df5c3da`（6 个提交），RULES `ea8c9b8`。
