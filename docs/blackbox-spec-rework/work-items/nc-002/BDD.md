# NC-002 可观察行为

「校验」指 `.venv/bin/check-jsonschema --schemafile <schema> <example>`；「守卫」指 `bash openspec/schemas/verify_community.sh`；「fixture 校验器」指 `python3 openspec/annotation-community/tools/validate_fixtures.py openspec/annotation-community/fixtures/community/`。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 12 个 `community_*.schema.json` | `check-jsonschema --check-metaschema` | 全部通过；每个顶层与每个嵌套对象 `additionalProperties: false`，唯三豁免：`command_record.resource_ids`、`command_record.result_fields`、`behavior_event.attributes`（开放对象，`additionalProperties` 不为 false） |
| B02 | 每个 Schema 的 `*.valid.yaml` | 校验 | 通过 |
| B03 | 每个 Schema 的 `*.invalid_unknown_field.yaml` | 校验 | 失败 |
| B04 | `community_note.invalid_preferred_head_not_in_heads.yaml` | 守卫的结构检查（JSON Schema 无法表达，由 verify_community.sh 内 Python 块检查） | 守卫非零并打印该文件名 |
| B05 | `community_note_revision.invalid_quotes_without_anchor.yaml`；配对文件 `community_pair_annotation.invalid_no_anchor.yaml`（note.kind=annotation 而 revision 无带 anchor 的 binding） | 校验 / 守卫 | 前者由 Schema `if/then` 拒绝；后者由守卫结构块 4(c) 拒绝，且 `community_pair_annotation.valid.yaml` 通过 |
| B06 | `community_note_revision.invalid_mention_length_1.yaml`、`.invalid_selector_float.yaml`、`.invalid_attachment_id_prefix.yaml` | 校验 | 失败 |
| B07 | `community_comment.invalid_depth_2.yaml`、`.invalid_depth1_without_root.yaml` | 校验 | 失败（`if depth=1 then root_id/reply_to_id 为字符串`） |
| B08 | `community_content_access.invalid_combo_published_trashed.yaml`、`.invalid_combo_never_published_hidden.yaml` | 校验 | 失败（Schema `allOf/if/then` 表达 SM-C 白名单） |
| B09 | `community_command_record.invalid_operation.yaml`、`.invalid_outcome_running.yaml`、`.invalid_payload_hash_len.yaml` | 校验 | 失败 |
| B10 | ID 字段收到上游前缀（`rev_` 作 NoteRevision、`art_` 作 Note） | 校验 | 失败 |
| B11 | 9 个 fixture 文件原样 | fixture 校验器 | 退出 0，stdout 末行 `FIXTURES_OK 9 files 198 cases` |
| B12 | 任一 case 删除 `expected` | fixture 校验器 | 退出 1，stdout 含 `<文件>#<case name>: missing expected` |
| B13 | 任一状态字段值不在 state-machines.md 枚举总表 | fixture 校验器 | 退出 1，含 `unknown state value` 与该值 |
| B14 | 任一 `*_id` 字段前缀不符 §0.1 | fixture 校验器 | 退出 1，含 `bad id` 与字段路径 |
| B15 | `content_hash_cases.json` 中某 case 的 `equal_hash_to` 指向不存在的 case，或两者 `expected_hash` 不等 | fixture 校验器 | 退出 1 |
| B16 | SERVER `xuan/community_hash.py` 对 18 个 case 的 snapshot | 计算 `canonical_bytes` 与 `content_hash` | 与 fixture 字面量逐字节/逐字符相等（C17 先投影六字段） |
| B17 | 16 个编码向量 | `encode(value)` | 字节与 `expected_bytes_hex` 相等 |
| B18 | 7 个非法 snapshot | `content_hash` | 抛出 `ValueError`（或其子类），不返回哈希 |
| B19 | SERVER 测试文件 | 静态检查 | 不 import 参考编码器；期望值来自 `tests/fixtures/community_content_hash_cases.json` 字面量；该副本与 SPEC 原件字节相同 |
| B20 | `openspec/schemas/verify.sh` | 任一步骤后运行 | 退出 0 且相对派发基线零 diff（本任务不修改它；社区校验由 `verify_community.sh` 独立承担） |
| B21 | `content_hash_cases.json` 的 3 个 `invalid_json_texts`（`-0`、重复键、`NaN`） | SERVER `load_snapshot_json(text)` | 抛 `ValueError`；同一文本经 `json.loads` 默认解析会静默放行，因此必须在解析层拒绝 |
| B22 | `community_note_revision.invalid_range_end_le_start.yaml`（selector 某段 end ≤ start） | 守卫结构块 4(d) | 守卫非零并打印该文件名；Schema 层通过（JSON Schema 无法比较两个字段） |
| B23 | `community_command_record.valid_rejected.yaml`（outcome=rejected、applied_version null、result_code 非空、status 409）、`.valid_compacted.yaml`（result_compacted_at 非 null、result_fields `{}`）、`.invalid_rejected_with_version.yaml`、`.invalid_compacted_with_fields.yaml` | 校验 | 两正例通过，两反例失败 |
