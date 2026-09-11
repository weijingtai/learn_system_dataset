# NC-015 验证计划

所有命令在 `/Users/jingtaiwei/Git/Public/learn_system` 下运行；`PY=/Users/jingtaiwei/Git/Public/learn_system/.venv/bin/python`。

## 1. 命令

| # | 命令 | 期望 |
|---|---|---|
| 1 | `$PY openspec/annotation-community/tools/check_private_sync_protocol.py` | 退出 0，末行 `samples=18` |
| 2 | `$PY -m unittest openspec/annotation-community/tools/test_check_private_sync_protocol.py` | `Ran N tests`，N ≥ 15，`OK` |
| 3 | `ls openspec/annotation-community/fixtures/private_sync | wc -l` | 18 |
| 4 | `bash openspec/annotation-community/verify.sh` | 0 |
| 5 | `bash docs/blackbox-spec-rework/reviews/nc015_guard.sh --require-impl` | 0 |

## 2. act/01：18 个样例

文件：`fixtures/private_sync/` 下 18 个 JSON，文件名逐字按契约 §7；字段按 BDD B02/B05/B09/B10；`expected` 逐字按契约 §7。`content_hash` 用脚本从 `fixtures/community/content_hash_cases.json` 读取第一个 case 的 `expected_hash` 粘贴（报告附该值）。`signature` 与密文引用为格式级（D-NC015-07）：`signature` 128 hex，`wrapped_dek` 96 hex（48 字节），`eph_pub` 64 hex，`nonce_w` 32 hex，`nonce_seed` 32 hex，`session_pub` 64 hex，`session_pub_sig` 128 hex；`envelope_valid.json` 另含 `signed_fields` 数组（契约 §4.4 十个字段名，顺序一致）。

Red：本步无检查器；以 act/02 的自测为 Red 来源（先写自测再写检查器）。本步提交前用 `$PY -c "import json,glob;[json.load(open(f)) for f in glob.glob('openspec/annotation-community/fixtures/private_sync/*.json')]"` 确认可解析。

## 3. act/02：检查器与自测

文件：`tools/check_private_sync_protocol.py`（标准库；读契约 markdown 与样例目录；红条件按契约 §8；成功打印 `samples=18` 退出 0；支持 `--contract <path> --fixtures <dir>` 供自测注入临时副本）、`tools/test_check_private_sync_protocol.py`（unittest，≥ 15 个测试，名称逐字）：
`green_on_real_contract_and_fixtures`（B01）、`auth_samples_have_required_fields`（B02）、`expired_sample_now_after_expiry`（B03）、`mismatch_samples_differ_in_exactly_one_field`（B04）、`valid_envelope_hash_matches_nc002_fixture`（B05）、`hash_mismatch_has_probe_and_same_signature`（B06）、`bad_signature_differs_in_signed_field`（B07）、`replay_shares_note_and_revision`（B08）、`oversize_inline_is_262145`（B09）、`relay_ttl_and_deletion_layers`（B10）、`missing_section_or_decision_or_tbd_fails`（B11，三个子断言）、`bad_expected_or_missing_file_or_wrong_ttl_fails`（B12，四个子断言）、`aad_mismatch_differs_only_in_recipient`（B14）、`session_pub_bad_signature_fields`（B15）、`pairing_anonymous_refused`（B16）。

Red：先写自测（检查器模块尚不存在 → ImportError 原文），再写检查器。

## 4. 禁止

`skip`、永真断言；读契约以外文档；新增依赖；改契约或其他文件。
