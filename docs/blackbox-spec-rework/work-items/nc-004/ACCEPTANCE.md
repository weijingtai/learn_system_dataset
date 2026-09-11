# NC-004 独立验收

当前：NOT_EXECUTED。

1. ACT 审查：由未参与编写的审查者做 wjt-react 四查；本文不自签 READY。
2. 范围：`git -C reading-notes log --oneline` 恰 5 个提交，`git show --name-only` 逐一核对只含各 ACT WRITE_NEW；learn_system 与 xuan-migration 其他目录零改动（`git status` 逐仓检查 xuan-storage、social、notification、repository-rest-adapter、xuan-shell）；父目录无 `.git`。
3. 重跑 TDD §1 全部 10 条命令并逐条记录退出码：`flutter analyze` 0；`flutter test` `+35: All tests passed!`；`pubspec.lock` 九个版本逐字等于契约 §1；fixture 副本 `cmp` 0；`nc004_guard.sh --require-impl` 0。
4. 主 Agent 交叉复算：用 learn_system 的 `tools/nchash_reference.py` 与 reading-notes 的 `nchash.dart`（写一个 `dart run` 一次性脚本，不入库）对至少 5 个 fixture 之外的盲测 snapshot 计算 hash：含 3 附件乱序、2 mention 同 offset 不同 user、binding 含两段 selector、title 含 emoji 与组合字符、change_summary 仅空白差异；两端逐字节相等。
5. 持久化盲测（不入库的临时测试或脚本）：保存 3 版后 `kill -9` 式中断不可模拟，改为：保存后直接用 `sqlite3` CLI 打开文件核对 `note_heads` 恰 1 行、`outbox_envelopes` 3 行且无任何标题/正文子串；再用 FailingInterceptor 在 `note_heads` 删除语句（而非 outbox）注入失败，验证同样回滚。
6. 作弊扫描：测试文件无 `skip`、`expect(true`、`isTrue)` 单独断言；`nchash.dart` 无 `jsonEncode`；仓储无 `catch (_) {}` 吞异常；`NativeDatabase.memory` 在 `test/` 与 `lib/` 中为 0 处。
7. 流程核对：每个提交同时含测试与实现；报告给出真实 Red 原文；自报「先实现后补测试」记录为流程偏差。
8. 通过后只验收 NC-004；不解锁需要 NC-015 密钥协议的同步/备份任务。

证据记录格式：commit；实际文件；每条 command/exit_code/原始摘要；Red 原文；盲测输出；跳过项与剩余阻塞。
