# NC-002 验证计划

工作目录：learn_system 步骤在 `/Users/jingtaiwei/Git/Public/learn_system`；act/05 在 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`。只用 Python 标准库与仓库已有的 `.venv/bin/check-jsonschema`（0.38.0）。判据来自 `contracts/community-models.md`、`contracts/state-machines.md` 与 `fixtures/community/*.json`。

## 1. 命令

| # | 命令 | 期望 | 自哪一步起 |
|---|---|---|---|
| 1 | `bash openspec/schemas/verify_community.sh` | 退出 0；每个正例一行 `PASS community_<schema>_valid`，每个反例一行 `PASS community_<schema>_<reason>`，结构块一行 `PASS community_structure` | act/01 |
| 2 | `bash openspec/schemas/verify.sh` | 退出 0；既有 PASS 行全部保留，末尾追加命令 1 的全部输出 | act/01 |
| 3 | `python3 -m unittest discover -s openspec/annotation-community/tools -p 'test_validate_fixtures.py' -v` | 退出 0，`Ran 7 tests` | act/04 |
| 4 | `python3 openspec/annotation-community/tools/validate_fixtures.py openspec/annotation-community/fixtures/community/` | 退出 0，stdout 末行 `FIXTURES_OK 9 files 196 cases` | act/04 |
| 5 | `cd /Users/jingtaiwei/Git/Public/xuan-server/functions-py && python3 -m unittest tests.test_community_hash_parity -v` | 退出 0，`Ran 7 tests` | act/05 |
| 6 | `cmp openspec/annotation-community/fixtures/community/content_hash_cases.json /Users/jingtaiwei/Git/Public/xuan-server/functions-py/tests/fixtures/community_content_hash_cases.json` | 退出 0 | act/05 |
| 7 | `LC_ALL=C bash openspec/annotation-community/review_v1_5_guard.sh`；`bash openspec/annotation-community/verify.sh`；`git diff --check` | 均 0；失败时按 README 外部失败规则处理 | 每步 |
| 8 | `bash docs/blackbox-spec-rework/reviews/nc002_guard.sh --require-impl` | 退出 0 | act/05 之后 |

命令 4 的 196 = content_hash 41（cases 18 + encoding_vectors 16 + invalid_snapshots 7）+ id_format 33 + command_id 10 + limit 17 + mention 13 + state_combinations 24 + lifecycle_transition 35 + comment_reply 12 + revision 11；校验器把三段都计入 cases 数。

## 2. Schema 与示例（act/01～03）

全部放 `openspec/schemas/`，示例放 `openspec/schemas/examples/`。所有 `$ref` 写成 `community_common.schema.json#/$defs/<名>`；`verify_community.sh` 用 `"$CJ" --base-uri "file://$REPO_ROOT/openspec/schemas/"` 解析。每个 Schema：`$schema` 为 draft 2020-12，顶层与全部嵌套对象 `additionalProperties: false`，`required` 列出该对象**全部**字段（契约中「默认」只影响 hash 规范化，存储记录必须显式携带）。

### 2.1 `community_common.schema.json`（只含 `$defs`）

| $def | 定义 |
|---|---|
| noteId … pseudonym（17 个，名称为 `<对象>Id`，pseudonym 名为 `actorPseudonym`） | `type: string, pattern: ^<前缀>[0-9a-f]{32}$`（前缀见 community-models §0.1） |
| upstreamRevisionId / upstreamReleaseId | `^rev_[0-9a-f]{32}$` / `^rel_[0-9a-f]{32}$` |
| commandId | DESIGN §2.1.1 正则 |
| accountId | `type: string, minLength: 1, maxLength: 128, pattern: ^[^/]+$` |
| attachmentId | `^[A-Za-z0-9_-]{1,128}$` |
| hex64 | `^[0-9a-f]{64}$` |
| timestamp | `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$` |
| version | `type: integer, minimum: 0` |
| operationName | enum：17 个操作（community-models §3.2） |
| targetKind | enum `knowledge_entry` `assertion` `source_span` `source_anchor` |
| relation | enum `about` `quotes` |

### 2.2 各 Schema 与示例文件

| Schema 文件 | 关键约束（其余字段按契约表） | 示例文件（`community_<schema>.` 前缀省略） |
|---|---|---|
| `community_note` | required 9；`kind` enum；`head_revision_ids` minItems 1 uniqueItems；`lifecycle` enum SM-3；`pending_op` enum SM-5；`trashed_at` timestamp 或 null | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_upstream_art_prefix.yaml`（id=art_…）；`invalid_empty_heads.yaml`；`invalid_pending_op_value.yaml`（pending_op=purge_pending） |
| `community_note_revision` | required 13；`$defs` attachmentRef(5 字段, alt maxLength 200, caption 500)、mentionRef(4 字段, start_offset ≥0, length ≥2, display_name minLength 1 maxLength 64)、bindingRef(4 字段；`if relation=quotes then anchor type object`)、anchorRef(7 字段)、selector(`schema const selector/v0-provisional`, ranges minItems 1, 每段 end > start 无法表达→由 validate 层保证，Schema 只要求 integer ≥0)；`title` maxLength 200；`change_summary` maxLength 500；`attachment_refs` maxItems 20；`mentions` maxItems 50；三数组 `uniqueItems: true`；`content_hash` hex64；`restored_from` nrev 或 null | `valid.yaml`（含 quotes+anchor 与 about+null）；`invalid_unknown_field.yaml`；`invalid_rev_as_note_revision.yaml`（id=rev_…）；`invalid_quotes_without_anchor.yaml`；`invalid_mention_length_1.yaml`；`invalid_selector_float.yaml`（start: 1.5）；`invalid_attachment_id_prefix.yaml`（attachment_id 含 `/`）；`invalid_21_attachments.yaml`；`invalid_duplicate_mention.yaml` |
| `community_publication` | required 7；`state` enum SM-2b；`if state=draft then published_at null else timestamp` | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_draft_with_published_at.yaml`；`invalid_live_without_published_at.yaml` |
| `community_content_access` | required 8；三枚举；`allOf`: `if visibility=never_published then moderation_state const allowed`；`if visibility=published then lifecycle const active`；`current_publication_id` pub 或 null | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_combo_published_trashed.yaml`；`invalid_combo_never_published_hidden.yaml`；`invalid_version_negative.yaml` |
| `community_comment` | required 11；`depth` enum [0,1]；`status` enum；`if depth=1 then root_id,reply_to_id type string`；`if depth=0 then root_id,reply_to_id type null` | `valid.yaml`（depth 0）；`valid_reply.yaml`（depth 1）；`invalid_unknown_field.yaml`；`invalid_depth_2.yaml`；`invalid_depth1_without_root.yaml`；`invalid_thread_id_cmt_prefix.yaml` |
| `community_comment_revision` | required 6；`body` maxLength 4000；`mentions` maxItems 50 uniqueItems | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_body_4001.yaml` |
| `community_reaction` | required 8；`target_type` enum content/comment；`value` enum like/dislike/null | `valid.yaml`；`valid_cancelled.yaml`（value null, version 2）；`invalid_unknown_field.yaml`；`invalid_value.yaml`（value: love） |
| `community_command_record` | required 13（DESIGN §2.1.1）；`operation` $ref operationName；`outcome` enum committed/rejected；`applied_version` version 或 null；`result_http_status` integer 100–599；`payload_hash` hex64；`resource_ids` object additionalProperties string；`result_fields` object | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_operation.yaml`；`invalid_outcome_running.yaml`；`invalid_payload_hash_len.yaml` |
| `community_notification_record` | required 8；`notification_id` ntf；`target` object {kind enum content/comment, id string, thread_id thr 可选} additionalProperties false；`delivery_state` enum SM-7 | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_delivery_state.yaml` |
| `community_notifier_delivery_binding` | required 8；`write_source` enum；`notifier_delivery_id`、`source_ref` minLength 1 | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_write_source_client.yaml` |
| `community_behavior_event` | required 12（DESIGN §11.2 外层）；`event_id` bev；`actor_pseudonym` psn；`schema_version` integer ≥1；`note_ref` hex64 或 null；`attributes` object（本期不收紧） | `valid.yaml`；`invalid_unknown_field.yaml`；`invalid_pseudonym_prefix.yaml`（psn 写成 account id） |
| 配对示例（结构块用） | `community_pair_annotation.valid.yaml`：`{note: <kind=annotation>, revision: <含 quotes+anchor binding>}`；`community_pair_annotation.invalid_no_anchor.yaml`：note kind=annotation 但 revision 的 bindings 全为 anchor null；`community_note.invalid_preferred_head_not_in_heads.yaml`：Schema 通过但 preferred_head_id ∉ head_revision_ids | 见 §2.3 |

示例中的 ID 一律用 `0123456789abcdef0123456789abcdef` 及其变体；时间戳用 `2026-09-10T12:00:00Z`。

### 2.3 `verify_community.sh`

`set -euo pipefail`；定位 `REPO_ROOT`、`CJ="$REPO_ROOT/.venv/bin/check-jsonschema"`；不可执行则 `echo ERROR >&2; exit 1`。

1. `"$CJ" --check-metaschema openspec/schemas/community_*.schema.json` → `PASS community_metaschema`。
2. 对每个 `examples/community_*.valid.yaml`（含 `valid_*.yaml`）：以文件名推断 schema（`community_<schema>.…`），校验必须通过 → `PASS community_<schema>_valid[_<变体>]`。
3. 对每个 `examples/community_*.invalid_*.yaml`：校验必须失败（失败即通过）→ `PASS community_<schema>_<reason>`；若意外通过则 `FAIL: <文件> should have failed` 并 `exit 1`。配对文件与 `invalid_preferred_head_not_in_heads` 不走第 3 步（它们 Schema 层是合法的），由第 4 步处理。
4. Python 结构块（`"$REPO_ROOT/.venv/bin/python" - <<'PY'`）：(a) 递归遍历 12 个 Schema，所有 `type: object` 节点（含 `$defs`、`items`、`then`）必须 `additionalProperties: false`；(b) 读取全部 `community_note*.yaml` 正例：`preferred_head_id ∈ head_revision_ids` 必须成立，对 `invalid_preferred_head_not_in_heads.yaml` 必须不成立；(c) 配对文件：用 jsonschema 库分别校验 note/revision 后，`note.kind=annotation ⇒ revision.bindings 存在 anchor 为 object 的项`；valid 必须成立，invalid 必须不成立 → `PASS community_structure`。
5. 最后一行 `echo "PASS community_all"`。

`openspec/schemas/verify.sh` 末尾追加且仅追加一行：`bash "$REPO_ROOT/openspec/schemas/verify_community.sh"`。

## 3. fixture 校验器（act/04）

文件：`openspec/annotation-community/tools/validate_fixtures.py`、`test_validate_fixtures.py`。

CLI：`validate_fixtures.py <fixture_dir>`。退出 0：stdout 末行 `FIXTURES_OK <files> files <cases> cases`；退出 1：每个问题一行 `<文件名>#<case name 或 索引>: <问题>`，去重、按 `sorted()` 排序；退出 2：目录不存在或非目录、`state-machines.md` 不存在，stderr 一行。

规则（判据全部来自契约；`state-machines.md` 路径固定为 `<fixture_dir>/../../contracts/state-machines.md`）：

| 编号 | 规则 | 问题文案 |
|---|---|---|
| V1 | 每个 `*.json` 可解析且为 object | `invalid json` |
| V2 | `cases` 每项为 object 且含 `expected`；`content_hash_cases.json` 例外：`cases` 项含 `expected_hash`(hex64) 与 `expected_canonical_hex`(偶数长小写 hex)，`encoding_vectors` 项含 `expected_bytes_hex`，`invalid_snapshots` 项含 `reason` | `missing expected` / `missing expected_hash` / `missing expected_bytes_hex` / `missing reason` |
| V3 | 解析枚举总表（`## 枚举总表` 后第一张表，`枚举` 列的反引号 token 并集 → ENUM_VALUES；须得到 11 行、≥ 40 个值）；递归遍历每个 case，键名 ∈ STATE_KEYS = `{visibility, lifecycle, moderation_state, state, from, to, editor_state, delivery_state, pending_op, status, content_visibility, head_becomes}` 且值为字符串时，值 ∈ ENUM_VALUES ∪ `{"new","user_choice"}`（后两者是 revision_cases 的占位词）否则报 | `unknown state value '<值>' at <路径>` |
| V4 | 递归遍历，键名以 `_id`/`_ids` 结尾或 ∈ `{heads, heads_after}` 且值为字符串（或字符串数组）时：键名 ∉ NON_BUSINESS = `{user_id, account_id, actor_id, author_id, recipient_id, block_id, entity_id, device_id, attachment_id, command_id, event_id, object_id, reporter_id, target_id, target_ref, notifier_delivery_id, public_profile_id}` 才检查；值须匹配 `^(note|nrev|pub|cacc|cbnd|anc|ares|thr|cmt|crev|rct|bmk|shr|bkm|ntf|bev|psn)_[0-9a-f]{32}$`，或键名 ∈ `{artifact_revision_id}` 时 `^rev_…`、`{release_id}` 时 `^rel_…`。`id_format_cases.json` 的 `value` 字段与 `command_id_cases.json` 的 `value/header/body` 字段跳过（它们故意非法） | `bad id '<值>' at <路径>` |
| V5 | `command_id` 键的字符串值须匹配 DESIGN §2.1.1 正则（同样跳过 command_id_cases 的 value/header/body） | `bad command_id at <路径>` |
| V6 | `content_hash_cases.json`：`equal_hash_to` 非 null 时目标 case 必须存在且 `expected_hash` 相等 | `equal_hash_to mismatch` / `equal_hash_to missing target` |
| V7 | 文件数必须为 9 且名称集合恰为规定的 9 个 | `unexpected fixture set` |

测试（`unittest`，通过 `subprocess.run([sys.executable, VALIDATOR, dir])`，夹具用 `tempfile` 复制真实 fixture 目录并同步复制契约到 `../../contracts/`）：

| 方法 | 断言 |
|---|---|
| test_real_fixtures_pass | 真实目录退出 0，末行 `FIXTURES_OK 9 files 196 cases` |
| test_missing_expected_red | 复制目录中删除 `limit_cases.json` 第 0 项的 `expected`：退出 1，stdout 含 `limit_cases.json#note_markdown_exactly_1MiB: missing expected` |
| test_unknown_state_red | `state_combinations.json` 第 0 项 lifecycle 改为 `deleted`：退出 1，含 `unknown state value 'deleted'` |
| test_bad_id_red | `comment_reply_cases.json` 第 0 项 `request.thread_id` 改为 `thr_XYZ`：退出 1，含 `bad id 'thr_XYZ'` |
| test_equal_hash_to_red | `content_hash_cases.json` 的 `C02_object_keys_reordered.expected_hash` 末位改动：退出 1，含 `equal_hash_to mismatch` |
| test_missing_dir_exit2 | 不存在目录：退出 2，stdout 空，stderr 一行无 Traceback |
| test_enum_table_parsed | 直接 import 模块调用 `load_enum_table(path)`：返回 11 行；值集合含 `purge_pending`、`ime_composing`、`retained`、`degraded`、`visible` |

## 4. SERVER nchash/v2（act/05）

模块 `xuan/community_hash.py`（独立实现，禁止 import 或复制 `nchash_reference.py`）。公开 API 与语义（DESIGN §7.2）：

| 名称 | 契约 |
|---|---|
| `DOMAIN: bytes = b"nchash/v2\n"` | — |
| `encode(value) -> bytes` | E 编码；非法输入抛 `ValueError` 子类 `CanonicalEncodingError` |
| `normalize_snapshot(snapshot: dict) -> dict` | 补默认值、字段全集校验、三数组规范排序、重复项拒绝（`ValueError` 子类 `SnapshotValidationError`） |
| `canonical_bytes(snapshot) -> bytes` | `encode(normalize_snapshot(snapshot))` |
| `content_hash(snapshot) -> str` | `sha256(DOMAIN + canonical_bytes).hexdigest()` |
| `project_revision(revision: dict) -> dict` | 从完整 NoteRevision 记录取六个语义字段 |

测试 `tests/test_community_hash_parity.py`（`unittest.TestCase`；fixture 路径 `Path(__file__).parent / "fixtures" / "community_content_hash_cases.json"`；不 import `tests.conftest`、不 import firebase）：

| 方法 | 断言 |
|---|---|
| test_domain_constant | `DOMAIN == b"nchash/v2\n"` |
| test_encoding_vectors | 16 个向量 subTest：`encode(value).hex() == expected_bytes_hex` |
| test_cases_canonical_and_hash | 18 个 case subTest：`snapshot` 非 null 时 `canonical_bytes(snapshot).hex() == expected_canonical_hex` 且 `content_hash(snapshot) == expected_hash`；`snapshot` 为 null 且有 `revision` 时先 `project_revision` |
| test_equal_hash_pairs | 所有 `equal_hash_to` 非 null 的 case：两者 `content_hash` 相等 |
| test_unequal_vs_base | C06/C07/C08/C09/C10/C11 六例 hash 各不等于 C01 |
| test_invalid_snapshots_raise | 7 个非法 snapshot subTest：`content_hash` 抛 `ValueError` |
| test_no_reference_import | 读取 `xuan/community_hash.py` 源码，断言不含字符串 `nchash_reference` |

`tests/fixtures/community_content_hash_cases.json` 用 `cp` 从 SPEC 原件复制，不得手改；守卫用 `cmp` 核对。

## 5. Red→Green

- act/01～03：先写示例 YAML 与 `verify_community.sh`，Schema 文件先只写 `{"$schema": …, "type": "object"}` 空壳，运行命令 1 取得 `FAIL: … should have failed`（反例被空壳放行）作为 Red；再写完整 Schema 至 Green。
- act/04：先写 7 个测试与只打印 `FIXTURES_OK 0 files 0 cases` 并退出 0 的空壳，运行命令 3 取得真实断言失败；再实现。
- act/05：先写 7 个测试与只定义 `DOMAIN` 的空壳模块，运行命令 5 取得 `AttributeError`/断言失败；再实现。
- 禁止：skip、永真断言、从被测输出生成期望、为通过而改 fixture/契约/示例期望、放宽 additionalProperties。
