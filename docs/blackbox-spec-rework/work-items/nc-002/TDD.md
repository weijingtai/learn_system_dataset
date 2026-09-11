# NC-002 验证计划

工作目录：learn_system 步骤（act/01～05）在 `/Users/jingtaiwei/Git/Public/learn_system`；act/06 在 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`。只用 Python 标准库、仓库既有 `.venv/bin/check-jsonschema`（0.38.0）与 `.venv` 内既有 jsonschema 4.26.0 / PyYAML 6.0.3（仅 `verify_community.sh` 结构块 import）。判据来自 `contracts/community-models.md`、`contracts/state-machines.md` 与 `fixtures/community/*.json`。

## 1. 命令

| # | 命令 | 期望 | 自哪一步起 |
|---|---|---|---|
| 1 | `bash openspec/schemas/verify_community.sh` | 退出 0；`PASS community_metaschema`、每个参与逐例校验的正例一行 `PASS community_<schema>_valid[_<变体>]`、每个参与逐例校验的反例一行 `PASS community_<schema>_<reason>`、`PASS community_structure`（act/02 起）、末行 `PASS community_all` | act/01 |
| 2 | `bash openspec/schemas/verify.sh` | 退出 0 且内容与派发基线零 diff（本任务**不修改**它，决定 D-NC002-11） | 每步 |
| 3 | `python3 -m unittest discover -s openspec/annotation-community/tools -p 'test_validate_fixtures.py' -v` | 退出 0，`Ran 7 tests` | act/05 |
| 4 | `python3 openspec/annotation-community/tools/validate_fixtures.py openspec/annotation-community/fixtures/community/` | 退出 0，stdout 末行 `FIXTURES_OK 9 files 198 cases` | act/05 |
| 5 | `cd /Users/jingtaiwei/Git/Public/xuan-server/functions-py && python3 -m unittest tests.test_community_hash_parity -v` | 退出 0，`Ran 8 tests` | act/06 |
| 6 | `cmp openspec/annotation-community/fixtures/community/content_hash_cases.json /Users/jingtaiwei/Git/Public/xuan-server/functions-py/tests/fixtures/community_content_hash_cases.json` | 退出 0 | act/06 |
| 7 | `LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh`；`bash openspec/annotation-community/verify.sh`；`git diff --check` | 均 0；失败时按 README 外部失败规则处理 | 每步 |
| 8 | `bash docs/blackbox-spec-rework/reviews/nc002_guard.sh --require-impl` | 退出 0 | act/06 之后 |

命令 4 的 198 = content_hash 44（cases 18 + encoding_vectors 16 + invalid_snapshots 7 + invalid_json_texts 3）+ id_format 33 + command_id 10 + limit 16 + mention 13 + state_combinations 24 + lifecycle_transition 35 + comment_reply 12 + revision 11；校验器把四段都计入 cases 数。

## 2. Schema 与示例（act/01～04）

全部放 `openspec/schemas/`，示例放 `openspec/schemas/examples/`。所有 `$ref` 写成 `community_common.schema.json#/$defs/<名>`；`verify_community.sh` 用 `"$CJ" --base-uri "file://$REPO_ROOT/openspec/schemas/"` 解析。每个 Schema：`$schema` 为 draft 2020-12，顶层与全部嵌套对象 `additionalProperties: false`（唯三豁免见 §2.3 步 4(a)），`required` 列出该对象**全部**字段（契约中「默认」只影响 hash 规范化，存储记录必须显式携带）。`maxLength`/`minLength` 按 JSON Schema 语义计 code point（已实测：3 个 4 字节字符对 `maxLength: 3` 通过）。

### 2.1 `community_common.schema.json`（只含 `$defs`）

| $def | 定义 |
|---|---|
| noteId … actorPseudonym（17 个，名称为 `<对象>Id`；假名为 `actorPseudonym`） | `type: string, pattern: ^<前缀>[0-9a-f]{32}$`（前缀见 community-models §0.1） |
| upstreamRevisionId / upstreamReleaseId | `^rev_[0-9a-f]{32}$` / `^rel_[0-9a-f]{32}$` |
| commandId | DESIGN §2.1.1 正则 |
| accountId | `type: string, minLength: 1, maxLength: 128, pattern: ^[^/]+$`（code point 近似，字节上限由服务端校验，契约 §0） |
| attachmentId | `^[A-Za-z0-9_-]{1,128}$` |
| hex64 | `^[0-9a-f]{64}$` |
| timestamp | `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$` |
| version | `type: integer, minimum: 0` |
| operationName | enum：17 个操作（community-models §3.2） |
| targetKind | enum `knowledge_entry` `assertion` `source_span` `source_anchor` |
| relation | enum `about` `quotes` |
| targetRef | `type: string, minLength: 1, maxLength: 200` |

### 2.2 各 Schema 与示例文件

示例中的 ID 一律用 `0123456789abcdef0123456789abcdef` 及其变体；时间戳用 `2026-09-10T12:00:00Z`。「结构块专属」表示 Schema 层合法、由 §2.3 步 4 判定，不参与步 2/3。

| Schema 文件 | 关键约束（其余字段按契约表） | 示例文件（`community_<schema>.` 前缀省略） |
|---|---|---|
| `community_note`（act/01） | required 9；`kind` enum；`head_revision_ids` minItems 1 uniqueItems；`lifecycle` enum SM-3；`pending_op` enum SM-5；`trashed_at` timestamp 或 null | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_upstream_art_prefix.yaml`（id=art_…）；`invalid_empty_heads.yaml`；`invalid_duplicate_heads.yaml`；`invalid_pending_op_value.yaml`（pending_op=purge_pending）；`invalid_preferred_head_not_in_heads.yaml`（结构块专属）——共 7 |
| `community_note_revision`（act/02） | required 13；`$defs` attachmentRef(5 字段, alt maxLength 200, caption 500, object_version minimum 1)、mentionRef(4 字段, start_offset minimum 0, length minimum 2, display_name minLength 1 maxLength 64)、bindingRef(4 字段；target_ref $ref targetRef；`if relation=quotes then anchor type object`)、anchorRef(7 字段)、selector(`schema const selector/v0-provisional`, ranges minItems 1, 每段 start/end integer minimum 0；`end > start` 由结构块 4(d) 判定)；`title` maxLength 200；`change_summary` maxLength 500；`attachment_refs` maxItems 20；`mentions` maxItems 50；`parent_ids` uniqueItems；三数组 `uniqueItems: true`；`content_hash` hex64；`restored_from` nrev 或 null | `valid.yaml`（含 quotes+anchor（双段 selector）与 about+null）；`invalid_unknown_field.yaml`；`invalid_rev_as_note_revision.yaml`（id=rev_…）；`invalid_quotes_without_anchor.yaml`；`invalid_mention_length_1.yaml`；`invalid_selector_float.yaml`（start: 1.5）；`invalid_attachment_id_prefix.yaml`（attachment_id 含 `/`）；`invalid_21_attachments.yaml`；`invalid_duplicate_mention.yaml`；`invalid_duplicate_parent_ids.yaml`；`invalid_title_201.yaml`（201 个 CJK 字符）；`invalid_range_end_le_start.yaml`（结构块专属）——共 12 |
| 配对示例（act/02，结构块专属） | `community_pair_annotation.valid.yaml`：`{note: <kind=annotation>, revision: <含 quotes+anchor binding>}`；`community_pair_annotation.invalid_no_anchor.yaml`：note kind=annotation 但 revision 的 bindings 全为 anchor null | 共 2 |
| `community_publication`（act/03） | required 7；`state` enum SM-2b；`if state=draft then published_at type null else timestamp` | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_draft_with_published_at.yaml`；`invalid_live_without_published_at.yaml`——共 4 |
| `community_content_access`（act/03） | required 8；三枚举；`allOf`: `if visibility=never_published then moderation_state const allowed`；`if visibility=published then lifecycle const active`；`current_publication_id` pub 或 null；`version` $ref version | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_combo_published_trashed.yaml`；`invalid_combo_never_published_hidden.yaml`；`invalid_version_negative.yaml`——共 5 |
| `community_comment`（act/03） | required 11；`depth` enum [0,1]；`status` enum；`if depth=1 then root_id,reply_to_id type string`；`if depth=0 then root_id,reply_to_id type null` | `valid.yaml`（depth 0）；`valid_reply.yaml`（depth 1）；`invalid_unknown_field.yaml`；`invalid_depth_2.yaml`；`invalid_depth1_without_root.yaml`；`invalid_thread_id_cmt_prefix.yaml`——共 6 |
| `community_comment_revision`（act/03） | required 6；`body` maxLength 4000；`mentions` maxItems 50 uniqueItems | `valid.yaml`；`valid_4000_emoji.yaml`（body 为 4000 个 😀，必须通过）；`invalid_unknown_field.yaml`；`invalid_body_4001.yaml`——共 4 |
| `community_reaction`（act/03） | required 7：`id, target_type, target_id, actor_id, value, version, updated_at`；`target_type` enum content/comment；`value` enum like/dislike/null | `valid.yaml`；`valid_cancelled.yaml`（value null, version 2）；`invalid_unknown_field.yaml`；`invalid_value.yaml`（value: love）——共 4 |
| `community_command_record`（act/04） | required 13（DESIGN §2.1.1）；`operation` $ref operationName；`outcome` enum committed/rejected；`applied_version` version 或 null；`result_http_status` integer 100–599；`payload_hash` hex64；`resource_ids` object（**开放对象**，`additionalProperties: {type: string}`）；`result_fields` object（**开放对象**）；`result_code` string 或 null；`result_compacted_at` timestamp 或 null；`if outcome=rejected then applied_version type null, result_code type string minLength 1, result_http_status minimum 400`；`if result_compacted_at type string then result_fields maxProperties 0` | `valid.yaml`（committed）；`valid_rejected.yaml`；`valid_compacted.yaml`；`invalid_unknown_field.yaml`；`invalid_operation.yaml`；`invalid_outcome_running.yaml`；`invalid_payload_hash_len.yaml`；`invalid_rejected_with_version.yaml`；`invalid_compacted_with_fields.yaml`——共 9 |
| `community_notification_record`（act/04） | required 8；`notification_id` ntf；`target` object {kind enum content/comment, id string minLength 1, thread_id thr（可选）} additionalProperties false；`delivery_state` enum SM-7；`attempt_count` version | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_delivery_state.yaml`——共 3 |
| `community_notifier_delivery_binding`（act/04） | required 8；`write_source` enum；`notifier_delivery_id`、`source_ref` minLength 1 | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_write_source_client.yaml`——共 3 |
| `community_behavior_event`（act/04） | required 12（DESIGN §11.2 外层）；`event_id` bev；`actor_pseudonym` psn；`schema_version` integer minimum 1；`note_ref` hex64 或 null；`object_type`/`object_id` string 或 null；`attributes` object（**开放对象**，本期不收紧） | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_pseudonym_prefix.yaml`（psn 写成 account id）——共 3 |

示例总数 62：参与逐例校验 58（正例 14 + 反例 44），结构块专属 4（2 配对 + `invalid_preferred_head_not_in_heads` + `invalid_range_end_le_start`）。act/04 中 `community_command_record.valid_rejected.yaml` 与 `valid_compacted.yaml` 承接 TASKS「完整/精简/拒绝终态」的通用约束；按 operation 的成对白名单推迟 NC-003（ACT.yaml `DEFERRED`）。

### 2.3 `verify_community.sh`

`set -euo pipefail`；定位 `REPO_ROOT`、`CJ="$REPO_ROOT/.venv/bin/check-jsonschema"`、`PY="$REPO_ROOT/.venv/bin/python"`；任一不可执行则 `echo ERROR >&2; exit 1`。**排除规则**：文件名以 `community_pair_` 开头，或文件名为 `community_note.invalid_preferred_head_not_in_heads.yaml`、`community_note_revision.invalid_range_end_le_start.yaml` 的，不参与步 2、3，只由步 4 处理。

1. `"$CJ" --check-metaschema` 对 `openspec/schemas/community_*.schema.json` 的全部文件（glob，不断言数量）→ `PASS community_metaschema`。
2. 对每个未被排除的 `examples/community_*.valid.yaml` 与 `examples/community_*.valid_*.yaml`：以文件名 `community_<schema>.` 前缀推断 schema，校验必须通过 → `PASS community_<schema>_valid` 或 `PASS community_<schema>_valid_<变体>`。
3. 对每个未被排除的 `examples/community_*.invalid_*.yaml`：校验必须失败（失败即通过）→ `PASS community_<schema>_<reason>`；若意外通过则 `FAIL: <文件> should have failed` 并 `exit 1`。
4. Python 结构块（`"$PY" - <<'PY'`，act/02 起；可 import jsonschema、yaml）：
   (a) 递归遍历全部 `community_*.schema.json`（glob），所有 `type: object` 节点（含 `$defs`、`items`、`then`、`allOf` 内）必须 `additionalProperties: false`，**豁免三处**：`community_command_record.properties.resource_ids`、`community_command_record.properties.result_fields`、`community_behavior_event.properties.attributes`（照仓库既有 `verify.sh` 对 `payload`/`counts` 的写法断言其 `additionalProperties` 不为 false）；
   (b) 读取全部 `community_note*.yaml`（非配对）：`preferred_head_id ∈ head_revision_ids` 对 valid 文件必须成立，对 `invalid_preferred_head_not_in_heads.yaml` 必须不成立；
   (c) 配对文件：用 jsonschema 库（RefResolver/registry 以 `openspec/schemas/` 为基）分别校验 note/revision 通过后，`note.kind=annotation ⇒ revision.bindings 存在 anchor 为 object 的项`；valid 必须成立，invalid 必须不成立；
   (d) 全部 `community_note_revision*.yaml`（含配对内的 revision）：所有 `bindings[*].anchor.selector.ranges[*]` 满足 `end > start`；对 `invalid_range_end_le_start.yaml` 必须不成立。
   四项全部满足 → `PASS community_structure`；任一不满足打印文件名并 `exit 1`。
5. 最后一行 `echo "PASS community_all"`。

`openspec/schemas/verify.sh` **不改**（D-NC002-11）；主 Agent 守卫 K01 依次运行 `verify.sh` 与 `verify_community.sh`。

## 3. fixture 校验器（act/05）

文件：`openspec/annotation-community/tools/validate_fixtures.py`、`test_validate_fixtures.py`。

CLI：`validate_fixtures.py <fixture_dir>`。退出 0：stdout 末行 `FIXTURES_OK <files> files <cases> cases`；退出 1：每个问题一行 `<文件名>#<case name 或 索引>: <问题>`，去重、按 `sorted()` 排序；退出 2：目录不存在或非目录、`state-machines.md` 不存在，stderr 一行。

规则（判据全部来自契约；`state-machines.md` 路径固定为 `<fixture_dir>/../../contracts/state-machines.md`）：

| 编号 | 规则 | 问题文案 |
|---|---|---|
| V1 | 每个 `*.json` 可解析且为 object | `invalid json` |
| V2 | `cases` 每项为 object 且含 `expected`；`content_hash_cases.json` 例外：`cases` 项含 `expected_hash`(hex64) 与 `expected_canonical_hex`(偶数长小写 hex)，`encoding_vectors` 项含 `expected_bytes_hex`，`invalid_snapshots` 项含 `reason`，`invalid_json_texts` 项含 `text`(string) 与 `reason` | `missing expected` / `missing expected_hash` / `missing expected_bytes_hex` / `missing reason` / `missing text` |
| V3 | 解析枚举总表（`## 枚举总表` 后第一张表，只取以 `|` 开头的连续行；`枚举` 列的反引号 token 并集 → ENUM_VALUES；须得到 11 行、恰 41 个值）；递归遍历每个 case，键名 ∈ STATE_KEYS = `{visibility, lifecycle, moderation_state, state, from, to, editor_state, delivery_state, pending_op, status, content_visibility, head_becomes}` 且值为字符串时，值 ∈ ENUM_VALUES ∪ `{"new"}`（`revision_cases.json` 的占位词）否则报 | `unknown state value '<值>' at <路径>` |
| V4 | 递归遍历，键名以 `_id`/`_ids` 结尾或 ∈ `{heads, heads_after}` 且值为字符串（或字符串数组）时：键名 ∉ NON_BUSINESS = `{user_id, account_id, actor_id, author_id, recipient_id, block_id, entity_id, device_id, attachment_id, command_id, event_id, object_id, reporter_id, target_id, target_ref, notifier_delivery_id, public_profile_id}` 才检查；值须匹配 `^(note|nrev|pub|cacc|cbnd|anc|ares|thr|cmt|crev|rct|bmk|shr|bkm|ntf|bev|psn)_[0-9a-f]{32}$`，或键名为 `artifact_revision_id` 时 `^rev_…`、`release_id` 时 `^rel_…`。`id_format_cases.json` 的 `value` 字段与 `command_id_cases.json` 的 `value/header/body` 字段跳过（它们故意非法）。不以上述后缀结尾的说明性键（如 `restore_source`、`both_parent`）**不检查**，这是有意为之 | `bad id '<值>' at <路径>` |
| V5 | `command_id` 键的字符串值须匹配 DESIGN §2.1.1 正则（同样跳过 command_id_cases 的 value/header/body） | `bad command_id at <路径>` |
| V6 | `content_hash_cases.json`：`equal_hash_to` 非 null 时目标 case 必须存在且 `expected_hash` 相等 | `equal_hash_to mismatch` / `equal_hash_to missing target` |
| V7 | 文件数必须为 9 且名称集合恰为规定的 9 个 | `unexpected fixture set` |

测试（`unittest`，通过 `subprocess.run([sys.executable, VALIDATOR, dir])`，夹具用 `tempfile` 复制真实 fixture 目录并同步复制契约到 `../../contracts/`）：

| 方法 | 断言 |
|---|---|
| test_real_fixtures_pass | 真实目录退出 0，末行 `FIXTURES_OK 9 files 198 cases` |
| test_missing_expected_red | 复制目录中删除 `limit_cases.json` 第 0 项的 `expected`：退出 1，stdout 含 `limit_cases.json#note_markdown_exactly_1MiB: missing expected` |
| test_unknown_state_red | `state_combinations.json` 第 0 项 lifecycle 改为 `Purged`（大小写不同，不在并集内）：退出 1，含 `unknown state value 'Purged'` |
| test_bad_id_red | `comment_reply_cases.json` 第 0 项 `request.thread_id` 改为 `thr_XYZ`：退出 1，含 `bad id 'thr_XYZ'` |
| test_equal_hash_to_red | `content_hash_cases.json` 的 `C02_object_keys_reordered.expected_hash` 末位改动：退出 1，含 `equal_hash_to mismatch` |
| test_missing_dir_exit2 | 不存在目录：退出 2，stdout 空，stderr 一行无 Traceback |
| test_enum_table_parsed | 直接 import 模块调用 `load_enum_table(path)`：返回 11 行；值集合大小 41，含 `purge_pending`、`ime_composing`、`retained`、`degraded`、`visible` |

## 4. SERVER nchash/v2（act/06）

模块 `xuan/community_hash.py`（独立实现，禁止 import 或复制 `nchash_reference.py`；禁止 `json.dumps`）。公开 API 与语义（DESIGN §7.2）：

| 名称 | 契约 |
|---|---|
| `DOMAIN: bytes = b"nchash/v2\n"` | — |
| `class CanonicalEncodingError(ValueError)`、`class SnapshotValidationError(ValueError)` | — |
| `load_snapshot_json(text: str) -> Any` | 解析层：`json.loads(text, parse_int=…, object_pairs_hook=…, parse_constant=…)`，遇原始 `-0`、重复键、`NaN`/`Infinity` 抛 `SnapshotValidationError` |
| `encode(value) -> bytes` | E 编码；非法输入抛 `CanonicalEncodingError` |
| `normalize_snapshot(snapshot: dict) -> dict` | 补默认值、字段全集校验、三数组规范排序、重复项拒绝（`SnapshotValidationError`） |
| `canonical_bytes(snapshot) -> bytes` | `encode(normalize_snapshot(snapshot))` |
| `content_hash(snapshot) -> str` | `sha256(DOMAIN + canonical_bytes).hexdigest()` |
| `project_revision(revision: dict) -> dict` | 只取六个语义字段；记录中其他键（同步、备份进度等）一律忽略不报错 |

测试 `tests/test_community_hash_parity.py`（`unittest.TestCase`；fixture 路径 `Path(__file__).parent / "fixtures" / "community_content_hash_cases.json"`；不 import `tests.conftest`、不 import firebase、不 import pytest）：

| 方法 | 断言 |
|---|---|
| test_domain_constant | `DOMAIN == b"nchash/v2\n"` |
| test_encoding_vectors | 16 个向量 subTest：`encode(value).hex() == expected_bytes_hex` |
| test_cases_canonical_and_hash | 18 个 case subTest：`snapshot` 非 null 时 `canonical_bytes(snapshot).hex() == expected_canonical_hex` 且 `content_hash(snapshot) == expected_hash`；`snapshot` 为 null 且有 `revision` 时先 `project_revision` |
| test_equal_hash_pairs | 所有 `equal_hash_to` 非 null 的 case：两者 `content_hash` 相等 |
| test_unequal_vs_base | C06/C07/C08/C09/C10/C11 六例 hash 各不等于 C01 |
| test_invalid_snapshots_raise | 7 个非法 snapshot subTest：`content_hash` 抛 `ValueError` |
| test_invalid_json_texts_raise | 3 个 `invalid_json_texts` subTest：`load_snapshot_json(text)` 抛 `ValueError`；并断言同一文本用裸 `json.loads` 不抛（证明必须在解析层拦截） |
| test_no_reference_import | 读取 `xuan/community_hash.py` 源码，断言不含 `nchash_reference` 与 `json.dumps` |

`tests/fixtures/community_content_hash_cases.json` 用 `cp` 从 SPEC 原件复制，不得手改；守卫用 `cmp` 核对。

## 5. Red→Green

- act/01～04：先写本步示例与脚本段落，本步 Schema 先只写 `{"$schema": …, "type": "object"}` 空壳，运行命令 1 取得 `FAIL: … should have failed`（反例被空壳放行）作为 Red；再写完整 Schema 至 Green。act/02 的结构块 Red：先放入配对与结构专属示例，此时脚本尚无 4(b)(c)(d) 检查，须先观察到 invalid 文件被放行，再补检查至 FAIL/PASS 正确。
- act/05：先写 7 个测试与只打印 `FIXTURES_OK 0 files 0 cases` 并退出 0 的空壳，运行命令 3 取得真实断言失败；再实现。
- act/06：先写 8 个测试与只定义 `DOMAIN` 的空壳模块，运行命令 5 取得 `AttributeError`/断言失败；再实现。
- 禁止：skip、永真断言、从被测输出生成期望、为通过而改 fixture/契约/示例期望、放宽 additionalProperties、先实现后补测试。
