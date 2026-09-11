# NC-003 独立验收

当前：NOT_EXECUTED。派发前置：NC-002 ACCEPTED；验证器已安装。

1. ACT 审查：未参与编写者做 wjt-react 四查；本文不自签 READY。
2. 范围：REST 仓库新增恰 4 个提交（在 `0f8bf52` 之后），`git show --name-only` 逐一核对只含各 ACT WRITE_NEW；`git diff 0f8bf52 HEAD --stat -- lib pubspec.yaml pubspec.lock` 为空；`test/openapi_validation_test.dart` 的 diff 只涉及 8 处断言与辅助函数（`test(` 计数仍 19）。
3. 重跑 TDD §1 全部命令并记录退出码：验证器对 `openapi/openapi.yaml` 0、对两个红文档非 0；`dart test +64`；`check_examples.py` 0；`nc003_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时文件，不入库）：① 用 Python 解析 yaml，独立复算：operation 级 `headers` 计数 0、社区路径恰 20、每个写操作 `IdempotencyKey` 必填、`If-Match` 集合恰为 W2～W6/W8～W11；② 对 `PublishRequest` 构造 `markdown` 恰 262144 字节与 262145 字节的示例，用 jsonschema 校验（注意 `maxLength` 按 code point，字节上限如用 `maxLength` 表达须说明取值），结果与契约一致或记录偏差；③ 把 `CommandResult.operation` 枚举与 DESIGN §2.1.1 列表逐字 diff；④ 检查 playground 既有 operation 的 `parameters` 中头参数名与迁移前 `headers` 键一一对应（35 对 35）；⑤ 随机抽 3 个错误响应，确认 `code` 值在契约 §4.1 目录内且 `type` 按 §4.2 映射。
5. 作弊扫描：测试无 `skip`、`expect(true`；`tool/validate_openapi` 确实调用 `openapi-spec-validator`（脚本内含该字符串且无自写校验逻辑）；`check_examples.py` 使用 `jsonschema` 库。
6. 流程核对：每个提交同时含测试与实现；报告给出真实 Red 原文（含改前文档的验证器失败原文）。
7. 通过后只验收 NC-003；服务端实现归 NC-009 起。

证据记录格式：commit；实际文件；每条 command/exit_code/原始摘要；Red 原文；盲测输出；跳过项与剩余阻塞。
