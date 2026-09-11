# NC-003 可观察行为

「测试」指 REST 仓库 `dart test <文件>`；「验证器」指 `tool/validate_openapi`（透传 `openapi-spec-validator 0.9.0` 退出码）；「示例校验」指 `tool/check_examples.py`。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 改前 `openapi/openapi.yaml`（35 处 operation 级 `headers:`） | 验证器 | 非零退出，输出含 `'headers' was unexpected`；迁移后同一命令退出 0 |
| B02 | `test/fixtures/openapi/red_operation_headers.yaml`（含一处 operation 级 `headers:`） | 验证器 | 非零退出 |
| B03 | `test/fixtures/openapi/red_invalid_31.yaml`（`info` 缺 `version`） | 验证器 | 非零退出 |
| B04 | 既有 `test/openapi_validation_test.dart` | 8 处断言改为检查 `parameters` 中存在 `in: header` 且 `name` 相符（经 `$ref` 解析） | 文件仍 19 个测试且全过；其余 11 个测试未改 |
| B05 | 迁移后文档 | 遍历全部 path/operation | 0 处 operation 级 `headers` 键 |
| B06 | 社区部分 | 检查 `/v1/community` 路径 | 契约 §2 的 20 个路径与方法逐字存在，无多余社区路径 |
| B07 | W1～W14 | 检查 `parameters` | 每个含 `$ref` 到 `IdempotencyKey` 且解析后 `required: true`、pattern 为 command_id 正则 |
| B08 | W2～W6、W8～W11 | 检查 `parameters` | 含 `IfMatch` 且 `required: true`；W1、W7、W12～W14、R1～R6 不含 `IfMatch` |
| B09 | R1～R3 | 检查 | `parameters` 含 `IfNoneMatch`；200 响应 `headers.ETag` 存在；存在 304 响应 |
| B10 | R1～R4 | 检查 404 | 四者 404 均 `$ref: '#/components/responses/NotFoundContent'` |
| B11 | `components/schemas/ProblemDetails` | 检查 | `required` 含 `type`、`title`、`status`、`code`；全部 4xx/5xx 响应 content 为 `application/problem+json` 且 schema 为 `ProblemDetails` 或其 `allOf` 派生 |
| B12 | `CommandResult.operation` | 检查 enum | 恰 17 个，逐字等于契约 §2 闭集 |
| B13 | `components/parameters/Limit` 与 `Cursor` | 检查 | `Limit`：integer、minimum 1、maximum 100、default 20；`Cursor`：pattern `^[A-Za-z0-9_-]{1,512}$` |
| B14 | 社区 Schema（契约 §5 全部名称） | 遍历 properties | 属性名全部匹配 `^[a-z][a-z0-9_]*$` |
| B15 | `PublishRequest` | 检查 | `required` 恰为 `content_id, revision_id, content_hash, snapshot`；`content_hash` pattern `^[0-9a-f]{64}$` |
| B16 | 429 响应组件 | 检查 | `headers.Retry-After` 存在；schema 派生自 `ProblemDetails` 且 `retry_after_seconds` integer 1～60 必填 |
| B17 | `examples/publish_missing_required.json`（缺 `content_hash`） | 示例校验 | manifest 标 `invalid`，工具判定不符合 `PublishRequest` |
| B18 | `examples/comment_illegal_status.json`（`status: archived`） | 示例校验 | `invalid`，不符合 `Comment` |
| B19 | `examples/idempotency_conflict_409.json`、`version_conflict_412.json`、`publish_valid.json` | 示例校验 | 三者 `valid`；前两者分别含 `original_request_hash`（64 hex）与 `current_version` |
| B20 | 示例 manifest 全体 | 运行 `tool/check_examples.py` | 退出 0；把任一 `expect` 翻转后退出 1（Red 证据） |
| B21 | 四个提交 | `git diff 0f8bf52 HEAD --stat -- lib pubspec.yaml pubspec.lock` | 空 |
| B22 | 全量 | `dart test` | `+64: All tests passed!`；`tool/validate_openapi openapi/openapi.yaml` 退出 0 |
| B23 | `info.version` | 检查 | `1.1.0` |
