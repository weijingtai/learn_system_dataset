# NC-016a 独立验收

当前：未验收。派发前置：NC-004、NC-007、NC-015、NC-017 ACCEPTED；wjt-react 四查 READY。

1. ACT 审查：未参与编写者做 wjt-react 四查（`reviews/NC-016a-REVIEW-R1.md`）。
2. 范围（`git diff-tree -r --name-only`）：STORAGE 分支 `fix/nc016-guard-aad` 在 `8ddb877` 之后恰 1 个提交、只含契约 §2.1 文件，`main` 仍为 `8ddb877`；CLIENT 在 `4a0d70a` 之后恰 2 个提交、只含 §2.2 文件，`note_repository.dart` 删除行数为 0；12 个样例副本与 learn_system 原件 SHA-256 相同。
3. 重跑 TDD §1 全部命令（经 tmux 执行器只运行，主 Agent 读原始输出判定）；`nc016a_guard.sh --require-impl all` 为 0。
4. 主 Agent 盲测（临时文件执行后删除，工作树恢复干净）：
   - ① 用 pyca 独立解开 Dart `seal` 产出的一个**多块**（明文 > 1 MiB，经 relay 以外的测试入口构造，不走内联上限）信封：按契约 §6.2 复算 wrap_key、解包 DEK、逐块解密与签名验证。
   - ② 交换信封 payload 中两块的顺序、删除末块，均 `reject:aad_mismatch`。
   - ③ `SealedEnvelope.toJson` → `fromJson` 往返后 `receive` 仍 `accept`。
   - ④ 旧会话代数的仓储调用 `applyRemoteRevision` → `StaleSessionError`，零写入。
   - ⑤ STORAGE worktree 内 `core`、`drift`、`p2p` 三包 `flutter analyze` 的问题数与改动前相同。
   - ⑥ `decideAuthorization` 与 STORAGE guard 对 8 个样例之外随机 200 组参数（固定随机种子）判定结果完全一致。
5. 作弊扫描：测试无 `skip`、永真断言；§9 参考值为字面量；S09～S17 使用真实 Ed25519/X25519 密钥（非替身签名）；S14 断言未调用验签；无真实网络。
6. 通过后：NC-016a `ACCEPTED`；NC-016b 仍 `BLOCKED`；NC-018 解锁条件之一（NC-016）按 16a 交付裁定。
