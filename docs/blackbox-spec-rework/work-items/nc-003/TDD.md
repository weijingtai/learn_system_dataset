# NC-003 验证计划

所有命令在 `export PATH=/Users/jingtaiwei/flutter/bin:$PATH` 下运行；仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter`；验证器路径与 Python 见 README。

## 1. 命令

| # | 命令 | 期望 |
|---|---|---|
| 1 | `dart analyze` | 0 issues |
| 2 | `tool/validate_openapi openapi/openapi.yaml` | act/01 后退出 0（改前非零） |
| 3 | `tool/validate_openapi test/fixtures/openapi/red_operation_headers.yaml`；`… red_invalid_31.yaml` | 均非零 |
| 4 | `dart test test/openapi_validation_test.dart` | `+19` |
| 5 | `dart test test/community_openapi_contract_test.dart` | act/01 后 `+2`；act/02 后 `+8`；act/03 后 `+13`；act/04 后 `+14` |
| 6 | `dart test` | act/01 `+52`；act/02 `+58`；act/03 `+63`；act/04 `+64: All tests passed!` |
| 7 | `python tool/check_examples.py`（act/04） | 退出 0 |
| 8 | `git diff 0f8bf52 HEAD --stat -- lib pubspec.yaml pubspec.lock` | 空 |
| 9 | `grep -c 'headers:' openapi/openapi.yaml` 仅作参考；判据用测试 B05 | — |
| 10 | `bash docs/blackbox-spec-rework/reviews/nc003_guard.sh --require-impl`（learn_system 内） | 0 |

## 2. act/01：验证器接入与既有结构迁移

文件：`tool/validate_openapi`（bash，可执行位）、`test/fixtures/openapi/red_operation_headers.yaml`、`test/fixtures/openapi/red_invalid_31.yaml`、`openapi/openapi.yaml`（新增 `components/parameters` 下 `IdempotencyKey`、`IfMatch`、`IfNoneMatch`、`Traceparent` 四个 `in: header` 参数；35 处 operation 级 `headers:` 逐一改为 `parameters` 中的 `$ref`；既有 `components/headers` 中对应请求头定义删除或仅保留响应头 `ETag`）、`test/openapi_validation_test.dart`（8 处断言 + 一个 `hasHeaderParam(op, name)` 辅助函数，解析 `$ref`）、`test/community_openapi_contract_test.dart`（先建文件，含 2 个测试）。

2 个测试（名称逐字）：`no operation level headers anywhere`（B05）、`validator accepts openapi and rejects red documents`（B01/B02/B03：`Process.run('tool/validate_openapi', …)` 三次，期望 0/非 0/非 0；验证器缺失时测试失败并打印退出码 2 的信息）。

Red：先写 2 个测试与 8 处迁移后的断言、两个红文档、工具脚本；运行命令 2（改前非零）、命令 4（迁移断言后对改前文档 8 处红）、命令 5（B05 红）取得原文；再迁移 yaml。

## 3. act/02：社区组件与内容端点

文件：`openapi/openapi.yaml`（`components/parameters`：`Cursor` 补 pattern、新增 `Limit`、`ContentId`、`CommentId`、`TargetType`、`TargetId`、`ShareId`、`CommandId`；`components/schemas`：契约 §5 全部 Schema、`CommandResult`；`components/responses`：`NotFoundContent`、`ProblemDetails` 各错误变体、`RateLimited`（含 `Retry-After` 头）；paths：W1～W6、R1、R6），`test/community_openapi_contract_test.dart` 追加 6 个测试。

6 个测试：`problem details requires code and error responses use it`（B11）、`command result operation enum is the closed set of 17`（B12）、`limit and cursor parameters bounds`（B13）、`community schema property names are snake case`（B14）、`publish request requires content hash and snapshot`（B15）、`rate limited response carries retry after`（B16）。

Red：先写 6 个测试，运行命令 5 取得失败原文。

## 4. act/03：评论、互动、分享、举报与命令端点

文件：`openapi/openapi.yaml`（paths：W7～W14、R2～R5），`test/community_openapi_contract_test.dart` 追加 5 个测试。

5 个测试：`community paths and methods match the catalog`（B06）、`write operations require idempotency key header parameter`（B07）、`if match required on versioned writes and absent elsewhere`（B08）、`reads declare etag if none match and not modified`（B09）、`acl read entries share the not found content response`（B10）。

Red：先写 5 个测试，运行命令 5 取得失败原文。

## 5. act/04：示例校验工具、fixture 与版本号

文件：`tool/check_examples.py`、`test/fixtures/openapi/examples/manifest.json` 与 5 个 JSON 示例（契约 §8 表）、`openapi/openapi.yaml`（`info.version: 1.1.0`），`test/community_openapi_contract_test.dart` 追加 1 个测试：`examples manifest validates via check examples tool`（B17～B20：`Process.run` 期望 0；再以临时 manifest 翻转一项期望 1）。

Red：先写测试与 manifest（工具尚不存在）取得原文；实现工具；命令 6 达 `+64`。

## 6. Red→Green 与禁止

- 每步先测试后实现；报告贴 Red 原文。
- 禁止：`skip`、永真断言、改 `lib/`、改 `pubspec.*`、新增依赖、再写 yaml 字段检查器代替验证器、改 playground 字段语义、把 backup.* 路径写进文档。
- 命令 6 最终 `+64`。
