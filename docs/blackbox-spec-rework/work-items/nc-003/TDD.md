# NC-003 验证计划

所有命令在 `export PATH=/Users/jingtaiwei/flutter/bin:$PATH` 下运行；仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter`；验证器路径与 Python 见 README。

## 1. 命令

| # | 命令 | 期望 |
|---|---|---|
| 1 | `dart analyze` | 0 issues |
| 2 | `tool/validate_openapi openapi/openapi.yaml` | act/01 后退出 0（改前非零） |
| 3 | `tool/validate_openapi test/fixtures/openapi/red_operation_headers.yaml`；`… red_invalid_31.yaml` | 均非零 |
| 4 | `dart test test/openapi_validation_test.dart` | `+19` |
| 5 | `dart test test/community_openapi_contract_test.dart` | act/01 后 `+2`；act/02 后 `+5`；act/03 后 `+8`；act/04 后 `+13`；act/05 后 `+15`；act/06 后 `+19` |
| 6 | `dart test` | act/01 `+52`；act/02 `+55`；act/03 `+58`；act/04 `+63`；act/05 `+65`；act/06 `+69: All tests passed!` |
| 7 | `python tool/check_examples.py`（act/05） | 退出 0 |
| 8 | `git diff 0f8bf52 HEAD --stat -- lib pubspec.yaml pubspec.lock` | 空 |
| 9 | `grep -c 'headers:' openapi/openapi.yaml` 仅作参考；判据用测试 B05 | — |
| 10 | `bash docs/blackbox-spec-rework/reviews/nc003_guard.sh --require-impl`（learn_system 内） | 0 |

## 2. act/01：验证器接入与既有结构迁移

文件：`tool/validate_openapi`（bash，可执行位）、`test/fixtures/openapi/red_operation_headers.yaml`、`test/fixtures/openapi/red_invalid_31.yaml`、`openapi/openapi.yaml`（新增 `components/parameters` 下 `IdempotencyKey`、`IfMatch`、`IfNoneMatch`、`Traceparent` 四个 `in: header` 参数；22 个 operation 的 `headers:` 逐一改为 `parameters` 中的 `$ref`；`components/headers` 只保留响应头 `ETag`）、`test/openapi_validation_test.dart`（14 行断言所在的 10 个测试块 + 一个 `hasHeaderParam(doc, op, name)` 辅助函数，解析 `$ref`；第 50 行 `components['headers']` 不改）、`test/community_openapi_contract_test.dart`（先建文件，含 2 个测试）。

2 个测试（名称逐字）：`no operation level headers anywhere`（B05，用 PyYAML 等价的 Dart 遍历 `paths.*.<method>`）、`validator accepts openapi and rejects red documents`（B01/B02/B03：`Process.run('tool/validate_openapi', …)` 三次，期望 0/非 0/非 0）。

Red：先写 2 个测试、迁移后的 14 行断言、两个红文档与工具；对改前文档运行命令 2（非零）、命令 4（10 个块红）、命令 5（B05 红）取得原文；再迁移 yaml。

## 3. act/02：社区参数、Schema、错误组件与 CommandResult

文件：`openapi/openapi.yaml`（`components/parameters`：`Cursor` 补 pattern、新增 `Limit`、`ContentId`、`CommentId`、`TargetType`、`TargetId`、`ShareId`、`CommandId`；`components/schemas`：契约 §5 全部 Schema、`CommandResult`；`components/responses`：`NotFoundContent`、各错误变体、`RateLimited`（含 `Retry-After` 头）、`GoneCommandResult`），`test/community_openapi_contract_test.dart` 追加 3 个测试。

3 个测试：`problem details requires code and error responses use it`（B11，此步只断言 `ProblemDetails` 与 responses 组件）、`command result operation enum is the closed set of 17`（B12）、`rate limited response carries retry after`（B16）。

Red：先写 3 个测试，运行命令 5 取得失败原文。

## 4. act/03：内容端点 W1～W6、R1、R6

文件：`openapi/openapi.yaml`（paths：W1～W6、R1、R6），`test/community_openapi_contract_test.dart` 追加 3 个测试。

3 个测试：`limit and cursor parameters bounds`（B13）、`community schema property names are snake case`（B14）、`publish request requires content hash and snapshot`（B15）。

Red：先写 3 个测试，运行命令 5 取得失败原文。

## 5. act/04：评论、互动、分享、举报与命令端点

文件：`openapi/openapi.yaml`（paths：W7～W14、R2～R5），`test/community_openapi_contract_test.dart` 追加 5 个测试。

5 个测试：`community paths and methods match the catalog`（B06）、`write operations require idempotency key header parameter`（B07）、`if match required on versioned writes and absent elsewhere`（B08）、`reads declare etag if none match and not modified`（B09）、`acl read entries share the not found content response and command endpoints follow ledger rules`（B10/B26/B27）。

Red：先写 5 个测试，运行命令 5 取得失败原文。

## 5b. act/05：示例校验工具、fixture 与版本号

文件：`tool/check_examples.py`、`test/fixtures/openapi/examples/manifest.json` 与 8 个 JSON 示例（契约 §8 表）、`openapi/openapi.yaml`（`info.version: 1.1.0`），`test/community_openapi_contract_test.dart` 追加 2 个测试：`examples manifest validates via check examples tool`（B17～B20、B24：`Process.run` 期望 0；再以临时 manifest 翻转一项期望 1）、`replay example keeps original applied version distinct from current state`（B25）。

Red：先写测试与 manifest（工具尚不存在）取得原文；实现工具；命令 6 达 `+65`。

## 5c. act/06：验收返工（NC-003-F；契约 §10）

文件：`openapi/openapi.yaml`、`tool/check_examples.py`（删 `nullable` 改写）、`test/fixtures/openapi/examples/`（新增 2 个示例并入 manifest，共 10 项）、`test/community_openapi_contract_test.dart`（新增 4 个测试；修改既有 `if match required on versioned writes and absent elsewhere` 与 `problem details requires code and error responses use it` 两个测试的断言对象，测试名不变）。

4 个新测试（名称逐字）：`community schemas express null with type arrays not nullable`（B28，含 check_examples 源码不含 `nullable`：B32）、`legacy problem details and responses equal baseline`（B29：用 `git show 0f8bf52:openapi/openapi.yaml` 取基线，YAML 解析后比较）、`publish declares optional if match for republish`（B30）、`markdown declares utf8 byte limit and detail declares state corrupted`（B31）。

Red：先改/写 6 个测试与 2 个示例，对 `89cc68d` 运行命令 5 与命令 7 取得失败原文（B28 应红：null 示例 invalid；B29 应红：ProblemDetails 与基线不等）。

## 6. Red→Green 与禁止

- 每步先测试后实现；报告贴 Red 原文。
- 禁止：`skip`、永真断言、改 `lib/`、改 `pubspec.*`、新增依赖、再写 yaml 字段检查器代替验证器、改 playground 字段语义、把 backup.* 路径写进文档。
- 命令 6 最终 `+69`（act/05 阶段 `+65`）。
