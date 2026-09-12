# NC-010 独立验收

当前：`REWORK_ACT06`（2026-09-11 主 Agent 验收 R1，见文末）。派发前置：NC-003 ACCEPTED（已满足）。

1. ACT 审查：未参与编写者做 wjt-react 四查。
2. 范围：reading-notes 恰 5 个提交（`9b35e97` 之后），只含各 ACT WRITE_NEW；TDD 命令 7 diff 为空；`pubspec.yaml` 相对基线只多 `http: 1.6.0` 一行；`pubspec.lock` 中既有九个版本不变；`note_database.g.dart` 未改。
3. 重跑 TDD §1 全部命令：`flutter test +212`；`nc010_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时测试，不入库）：① payload_hash：Dart 实现对另外 3 组输入（含中文 body、`if_match: null`、嵌套对象）与 Python `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)` 的 SHA-256 逐字相等；②③ 已下沉为正式测试 B31/B32，验收时核对其断言确为真实文件库关闭重开与并发调用（非同一连接内的模拟）；④ 作者文案：`trashed_at` 恰 30 天前 / 29 天 23 小时前 的 N 值；⑤ 他人视角页面源码不引用 `NoteRepository`（公开视图只经 R1）；⑥ `CommunityApi` 对 `If-Match` 值带双引号、对 `ifNoneMatchVersion` 同样。
5. 作弊扫描：测试无 `skip`、永真断言；payload_hash 期望值为字面量；`lib/src/community` 无 Firebase 导入；`lib/src/editor`、`lib/src/persistence` 不导入 `lib/src/community`（editor.md 不变式）；无真实网络（`HttpClient`、`http.Client()` 直接构造不出现在测试中）。
6. 通过后：NC-010 `ACCEPTED`；NC-011（评论）与 NC-012（互动）可复用命令队列。

---

## 验收记录 R1（主 Agent，2026-09-11）：act/01～05 REWORK，追加 act/06

- 提交：reading-notes `bd894b4`（A）、`3e25710`（B）、`2c59d08`（C）、`266aff0`（D）、`46a5ebf`（E），逐提交 `git diff-tree` 均在对应 WRITE_NEW 内；`pubspec.yaml` 只加 `http: 1.6.0`，`pubspec.lock` 只多 http 一段；受保护目录（domain/persistence/editor/history 及对应测试目录）自 `9b35e97` 零改动；工作树干净。
- 命令经 tmux + agy 执行（只运行、存原始输出于 `~/tmux-agents/runs/nc010v/`，主 Agent 读原始输出判定）：`flutter analyze` No issues；`flutter test` `+212: All tests passed!`；`nc010_guard.sh --require-impl` 失败条数 0；作弊扫描（skip/永真断言、真实 HttpClient、Firebase、editor/persistence 导入 community）均无命中；参考哈希在 `command_queue_test.dart:77` 为字面量。
- 交付报告 `work-items/nc-010/DELIVERY_REPORT.md`：act/01～05 均有 Red 原文段与 Green 输出。
- 源码审阅：`CommunityApi` 写操作 `if-match` 与 `getContent` 的 `if-none-match` 均为带双引号的版本号（清单 ⑥ 通过）；他人视角 `content_detail_page.dart` 不引用 `NoteRepository`（⑤ 通过）；B31 测试用 `Directory.systemTemp` 真实文件库 `openScoped` → `close()` → 重开，B32 用 `Future.wait` 同时调用两个 `drain()`（②③ 通过）。
- 盲测（主 Agent 编写，临时文件已删除）：
  - 通过：作者文案 N 值——恰 30 天前「剩余 0 天」、29 天 23 小时前与 29 天前「剩余 1 天」、当下「剩余 30 天」；31 天前显示「剩余 0 天」（记 D-NC010-12）。payload_hash §8 样例一与「嵌套对象、布尔、浮点、大整数、负数」样例与 Python 逐字相等。
  - **缺陷 1**：`computePayloadHash` 用 `'if_match': ?ifMatch`，`ifMatch` 为 null 时省略该键；服务端与契约公式保留 `"if_match": null`。首次发布样例 Dart `1385a6c2…` ≠ Python `d9216833…`；把 Python 侧改为省略该键即得 Dart 值，确认为唯一成因。
  - **缺陷 2**：`_canonicalJson` 用 `List<String>.sort()`（UTF-16 码元序），契约 §4 表写明「键按码点排序」。键含 U+1F600 与 U+FF41 时 Dart `d70a36d7…` ≠ Python `7a9dbfff…`；Python 侧改按 UTF-16 排序即得 Dart 值。
  - 影响：`payload_hash` 目前只落本地命令行，未参与服务端比对，功能暂未出错；但违反「跨端逐字节一致」，NC-011/NC-012 复用队列前必须修正。
- 判定：**REWORK**（小）；契约 §10（D-NC010-10～12）+ act/06；通过后复跑两组盲测哈希与全量计数，关闭 NC-010。
