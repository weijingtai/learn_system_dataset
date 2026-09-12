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
