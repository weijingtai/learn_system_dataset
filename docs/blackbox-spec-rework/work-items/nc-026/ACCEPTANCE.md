# NC-026 验收（主 Agent 独立执行，不采信执行方自述）

当前状态：`ACCEPTED`（2026-09-13；四查独立性按 D-NC026-28 由用户授权替代，见 `reviews/NC-026-REVIEW-R1.md`）。

1. ACT 审查：未参与编写、且不同厂商的审查者按 wjt-react 四查（忠实性、覆盖性、可执行性、独立性）判定 READY；返工不超过 2 轮；记录于 `reviews/NC-026-REVIEW-R1.md`。重点复核：契约 §13 的三条待裁决（P1 attributes 填充、P2 上报开关、R11 假名端点新增）与 DESIGN §11.2 的措辞歧义（D-NC026-06）。
2. 范围（`git diff-tree -r --name-only`，不用 `git diff`）：
   - REST `b60bfbd..HEAD`：恰 5 个文件（openapi.yaml、契约测试、2 示例、manifest）。
   - SERVER `992088e..HEAD`：恰 10 个文件（schemas 副本、test_community_validation.py、command_service.py、pseudonyms.py、behavior_events.py、analytics_events.py、config.py、main.py、conftest.py、test_behavior_events.py）；`content_service.py`、`discussion_service.py`、`interaction_service.py`、`access.py`、`errors.py`、`ids.py`、`community_hash.py`、`push.py`、`identity.py`、`tests/test_community_interactions.py`、`tests/test_community_comments.py`、`tests/test_registration.py`、`tests/test_main_exports.py`、`tests/community_helpers.py` 零改动。
   - CLIENT `19afe37..HEAD`：恰 2 个文件（`19afe37` 为 NC-014 落地后基线，D-NC026-26）。
   - RULES `a354463..HEAD`：恰 1 个文件；`server/firestore.rules` 零改动。
3. 重跑 TDD §1 全部命令：pytest `5 failed, 594 passed, 3 xfailed`（FAILED 恰为五个既有 ID）；rules `157 passed`；dart `+85`；flutter `analyze` 0 与 `+332`；`nc026_guard.sh --require-impl all` 退出 0。
4. 主 Agent 盲测（临时文件不入库，结束删除并以四仓 `git status --short` 为空证明；清单 = 契约 §14 八项）：① 真跑 publish 并把事件文档做真 Schema 校验；② 三组 `bev_` 与 `note_ref` 独立进程复算；③ 重复批 `accepted=2, duplicates=1`；④ 501 → 413、错 `event_type` → 400、非法 attributes → 400 且 JSON Pointer 正确；⑤ 两独立项目假名不同且 ≠ 哈希推导值；⑥ 10001 条丢 1 且下一条带 `dropped_before: 1`、重启后 `pendingCount` 不变；⑦ 上报原始字节不含 note_id/标题/正文/附件名；⑧ 作弊扫描。
5. 作弊扫描：无 `skip`、无新增 `xfail`、无永真断言；`SCHEMA_SHA`、3 组 `bev_`、`note_ref` 为字面量；`tx.create()` 真实 create-if-absent（并发/重试用真实事务）；`_send_multicast` 不涉及；无真实外部网络；`exactly-once` 在三仓新增文件中零命中；`server/firestore.rules` 与 `COMMUNITY_COLLECTIONS` 清单数组未被触碰。
6. 注销子项：确认**未派发**且契约 §13 已登记 DEFERRED 与其解锁条件（NC-001 第⑩项）。
7. 通过后：NC-026 `ACCEPTED`；更新 `SUBAGENT_TODO.md`、本文件验收记录、推送四仓；handbook 能力条目 `social.community-behavior-events` 按 PROTOCOL §4 回写（`status` → `branch`/`landed`，`evidence.sha` 填业务仓真实提交，接入手册 `integration/social.community-behavior-events.md` 按 §9 铁律补写，删除 claim 文件）。

## 待裁决登记（执行中追加）

| 编号 | 事项 | 裁定 |
|---|---|---|
| D-NC026-26 | NC-026 起草早于 NC-014 落地，CLIENT 基线 `+296` → `+314` | 同步契约/六件套/守卫：保护路径 diff 基准 `107ec90` → `19afe37`、期望计数 `+314` → `+332` |
| D-NC026-27 | SERVER act/02 与 act/03 同会话实现 | 合并单提交；范围证据取 `992088e..HEAD` 恰 10 文件 |
| D-NC026-28 | 四查无第三方审查者 | 用户授权替代；评审记录降级为作者自查 + 冲突披露 |

## 待裁决（规格期已登记，供四查或主 Agent 裁定）

| 编号 | 事项 | 契约位置 |
|---|---|---|
| P1 | 是否由本任务填充 `content.publish.image_count` 与 `reaction.set.{value, previous_value}`（需改 NC-009/NC-012a 已验收文件与 `tests/test_community_interactions.py:149` 断言） | 契约 §3.2、§13、D-NC026-08 |
| P2 | 私人笔记上报的默认开关 UI 与隐私政策文本归属（PRD 要求默认上报并写入隐私政策） | 契约 §13 |
| P3 | R11 `GET /v1/analytics/pseudonym` 是 DESIGN 未定义的新增端点，需确认接受该补口 | 契约 §5.2、D-NC026-07 |
| P4 | DESIGN §11.2 客户端事件 `event_id` 措辞歧义（裸 32 hex vs `bev_` + hex）的解读 | 契约 §3「D-NC026-06」、§15 |

P1～P4 的裁定结果见契约 §13 与 D-NC026-29～32：P1/P2 不采纳（P1 只冻结允许集不填充，P2 归宿主产品范围）；P3/P4 采纳（保留假名端点、统一 `bev_` + UUIDv4 hex）。

## 验收记录 R1（2026-09-13，主 Agent）

### 范围证据（`git diff-tree -r --name-only`）

| 仓 | 区间 | 文件数 | 结果 |
|---|---|---|---|
| REST | `b60bfbd..c1afba3` | 5 | 与 §2 一致（openapi.yaml、契约测试、2 示例、manifest） |
| SERVER | `992088e..dd04f27` | 10 | 与 §2 一致；保护清单 `git diff-tree` 输出为空 |
| CLIENT | `19afe37..613f6ba` | 2 | 与 §2 一致；`note_database.dart`/`note_repository.dart`/`editor`/`pubspec.yaml` 零改动 |
| RULES | `a354463..f74b9a5` | 1 | 只追加用例；`server/firestore.rules` 零改动 |

### 命令证据（§3 重跑）

- `nc026_guard.sh --require-impl all`：**K01～K09 全 PASS，失败条数 0**（日志 `scratchpad/nc026/guard_all.log`）。
- 其中 K07 内含全量 pytest：`5 failed, 594 passed, 3 xfailed`，FAILED 集合恰为 §5 的五个既有 ID（未修复）。
- K06 `dart test` ≥85；K08 `flutter analyze` 0 且 `flutter test` ≥332；K09 `157 passed, 157 total`。

### 盲测（临时探针，已删除，四仓 `git status --short` 为空）

| # | 探针 | 结果 |
|---|---|---|
| ① | 真跑 `POST /v1/community/contents`，落库文档交 `Draft202012Validator` + 服务端 schemas Registrar 真校验 | PASS（`platform == server`、`note_ref is None`） |
| ② | 独立进程复算 3 组 `bev_`（`ids.server_event_id`）与 `note_ref`（`hashlib.sha256` 直接算） | 全 MATCH |
| ③ | 同批重复 `event_id`：`accepted=2, duplicates=1`；整批重投 `0/3` | PASS |
| ④ | 501 → 413 `too_large.events`（limit 500）；服务端 `event_type` → 400 `invalid_argument.event_type` + `/events/0/event_type`；未知 attributes 键 → 400 `invalid_argument.events` + Pointer 前缀命中；被拒批零落盘 | PASS |
| ⑤ | 两独立项目假名不同，且均 ≠ `psn_`+`sha256(scope)[:32]` | PASS |
| ⑥ | 10001 条 → `pendingCount=10000`、`droppedPending=1`；重启后两者不变；`dropped_before` 恰出现在本批 1 条上且值为 1；flush 后归零 | PASS |
| ⑦ | 上报原始 JSON 不含 `note_id` 原值、标题/正文标记、附件名 | PASS |
| ⑧ | 作弊扫描：新增文件 `skip`/`xfail`/`exactly-once` 零命中；`SCHEMA_SHA`/3 组 `bev_`/`note_ref` 为字面量；`transaction.create(ref, …)` 真事务；无真实外部网络 | PASS |

### 执行期发现的缺陷与修正

- **永真断言**：`tests/test_behavior_events.py` 曾有 `assert document["received_at"] != event["occurred_at"] or True`（恒真）。已改为 `re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", document["received_at"])`（提交 `dd04f27`），改后 26 passed。
- 该缺陷属 §5 作弊扫描项，若不是盲测/扫描阶段回头查会被漏过——已如实记录。

### 其余 §5 项

- `SCHEMA_SHA`、3 组 `bev_`、`note_ref` 均字面量；Schema 副本与规格侧 `cmp` 逐字节相同。
- `server/firestore.rules` 与 `COMMUNITY_COLLECTIONS` 清单数组未被触碰（`git diff-tree` 证实）。
- `push.py`、`identity.py` 未改动；无 `_send_multicast` 相关改动。

### §6 注销子项

确认**未派发**；契约 §13 已登记 `DEFERRED`（D-NC026-13）与解锁条件（NC-001 第⑩项登记完成）。

### 结论

**ACCEPTED**。四仓已推送（REST `c1afba3`、SERVER `dd04f27`、CLIENT `613f6ba`、RULES `f74b9a5`）；learn_system 规格与评审已推送；handbook 能力条目按 PROTOCOL §4 回写。
