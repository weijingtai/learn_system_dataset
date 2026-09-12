# NC-010 独立验收

当前：NOT_EXECUTED。派发前置：NC-003 ACCEPTED（已满足）。

1. ACT 审查：未参与编写者做 wjt-react 四查。
2. 范围：reading-notes 恰 5 个提交（`9b35e97` 之后），只含各 ACT WRITE_NEW；TDD 命令 7 diff 为空；`pubspec.yaml` 相对基线只多 `http: 1.6.0` 一行；`pubspec.lock` 中既有九个版本不变；`note_database.g.dart` 未改。
3. 重跑 TDD §1 全部命令：`flutter test +211`；`nc010_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时测试，不入库）：① payload_hash：Dart 实现对另外 3 组输入（含中文 body、`if_match: null`、嵌套对象）与 Python `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)` 的 SHA-256 逐字相等；②③ 已下沉为正式测试 B31/B32，验收时核对其断言确为真实文件库关闭重开与并发调用（非同一连接内的模拟）；④ 作者文案：`trashed_at` 恰 30 天前 / 29 天 23 小时前 的 N 值；⑤ 他人视角页面源码不引用 `NoteRepository`（公开视图只经 R1）；⑥ `CommunityApi` 对 `If-Match` 值带双引号、对 `ifNoneMatchVersion` 同样。
5. 作弊扫描：测试无 `skip`、永真断言；payload_hash 期望值为字面量；`lib/src/community` 无 Firebase 导入；无真实网络（`HttpClient`、`http.Client()` 直接构造不出现在测试中）。
6. 通过后：NC-010 `ACCEPTED`；NC-011（评论）与 NC-012（互动）可复用命令队列。
