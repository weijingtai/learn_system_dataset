# NC-017 独立验收

当前：未验收。派发前置：NC-004、NC-015 ACCEPTED；NC-011 CLIENT 线 act/06 已提交；wjt-react 四查 READY。

1. ACT 审查：未参与编写者做 wjt-react 四查（`reviews/NC-017-REVIEW-R1.md`，派 agy）。
2. 范围（`git diff-tree -r --name-only`）：reading-notes 在 NC-011-F 提交之后恰 2 个提交，只含契约 §2 白名单文件；`pubspec.yaml` 相对基线只多 `  cryptography: 2.9.0` 一行；`pubspec.lock` 只多 cryptography 一段。
3. 重跑 TDD §1 全部命令（经 tmux 执行器只运行，主 Agent 读原始输出判定）；`nc017_guard.sh --require-impl` 为 0。
4. 主 Agent 盲测（临时副本，不入库，结束后 `git status --short` 为空）：
   - ① 用 Python `cryptography` AESGCM 与 OpenSSL Argon2id 独立解开写入器导出的一个 2 笔记含附件的文件（按契约 §3～§4 手写解析），记录与仓库一致。
   - ② 把文件中第 1 块的 `chunk_len` 改大 1 → `ExportUndecryptable`（不是崩溃或 RangeError）。
   - ③ 头部 `scope` 改为其他值并重算 digest → `ExportFormatError`。
   - ④ 附件字节恰为 1 MiB 与 1 MiB+1 时，写入与解码往返一致。
   - ⑤ `ExportUndecryptable` 在五种失败下 `runtimeType` 与 `toString()` 都相同，异常对象不含块号字段。
   - ⑥ 导出后仓库中笔记的 `pending_op`、`updated_at` 与修订数量不变（写入器只读）。
5. 作弊扫描：测试无 `skip`、永真断言；K、D、文件摘要为字面量；E10/E11 确为经 `debugHook` 注入并检查磁盘上的 `.partial`；无真实网络。
6. 通过后：NC-017 `ACCEPTED`；解锁 NC-018（须同时等 NC-016）。

---

## 验收记录 R1（主 Agent，2026-09-12）：ACCEPTED

- **执行**：tmux + `cmd --yolo`（`deepseek/deepseek-v4.1-flash`），会话 nc017；四查由 agy 完成（`reviews/NC-017-REVIEW-R1.md`，READY、返工 0 项，参考值由审查者经 OpenSSL 与 Python 独立复算吻合）。
- **提交与范围**（`git diff-tree -r --name-only`）：reading-notes 在 NC-011-F `463835e` 之后恰 2 个提交——`e913b14`（NC-017-A）为 `lib/reading_notes.dart`、`lib/src/export/export_bundle_format.dart`、`pubspec.lock`、`pubspec.yaml`、`test/export/export_bundle_test.dart`；`4a0d70a`（NC-017-B）为 `lib/reading_notes.dart`、`lib/src/export/export_writer.dart`、`test/export/export_bundle_test.dart`。全部在契约 §2 白名单内。`pubspec.yaml` 只增 `  cryptography: 2.9.0` 一行；`pubspec.lock` 只增 cryptography 一段（8 行，`version: "2.9.0"`）。
- **守卫**：执行方运行 `nc017_guard.sh --require-impl` 时 K05 因守卫自身锁文件正则行数写错（`{5}` 应为 6 行）而误判，执行方按停手协议上报并附独立复算；主 Agent 确认为守卫缺陷，改为按块解析（`d848c56`），复跑 K01～K05 全 PASS、失败条数 0（含 `flutter analyze` 0、`flutter test +253`）。
- **交付报告**：act/01、act/02 均有 Red 原文段与 VERIFICATION 输出（`export_bundle_test.dart +14`、全量 `+253`）。执行方在 act/02 Red 之后改过一处测试自身写法：E09 原用 `List<Map>.contains(map)`（Dart `Map` 未覆写 `==`，恒为 false），改为 `parent_ids`/`change_summary`/`restored_from` 显式字段断言——判据更严，不属放宽，接受。
- **盲测**（主 Agent 编写，cmd 只运行；原始输出 `~/tmux-agents/runs/nc017v/`；盲测文件复制进 `test/export/` 执行后已删除，`git status --short` 为空）：
  - ① Python 独立解码（`nc017_blind_decode.py`：OpenSSL 3.6.3 Argon2id 派生 + pyca AESGCM 按契约 §3～§4 手写解析）写入器导出的 2 笔记 / 3 修订 / 3 附件（含 1 MiB 与 1 MiB+1 字节）文件：28 项全 PASS——清单 digest 复算、规范 JSON 头、不含 scopeUid、KDF 参数、分块帧覆盖文件、3 块且非末块明文恰 1048576 字节、附件 byte_length 与 content_digest、记录顺序与键集合（笔记 8 键、修订 13 键）、修订内容与仓库一致、结束记录与计数 2/3/3、文件 SHA-256、原始字节不含三处明文。
  - ② 第 1 块 `chunk_len` 加 1 → `ExportUndecryptable`（非崩溃）：PASS。
  - ③ 头部 `scope` 改为 `other_scope` 并重算 digest → `ExportFormatError`：PASS。
  - ④ 1 MiB 与 1 MiB+1 附件经写入器导出后 `decodeExportFile` 往返逐字节相等：PASS。
  - ⑤ 错口令、末字节翻转、截断 1 字节、chunk_len 篡改四种失败的 `runtimeType` 相同、`toString()` 均为 `ExportUndecryptable`：PASS。
  - ⑥ 导出前后两条笔记的 `pending_op`、`updated_at`、`lifecycle` 与修订数不变：PASS。
- **作弊扫描**：测试无 `skip`、永真断言；K、D、文件摘要等为字面量（守卫 K05 `ref_literals=True`）；E10 在 `after_chunk:0` 注入并断言 `.partial` 存在，E11 在 `before_verify` 翻转 `.partial` 并断言其被删除；无真实网络。
- **判定**：`ACCEPTED`。NC-018 仍需等待 NC-016。
