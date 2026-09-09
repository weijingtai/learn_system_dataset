# D-03 TDD／机器与人工判据

本任务是文档追溯验收：机器检查先证明结构齐全，人工检查再证明语义没有假绿。

## 自动判据

在仓库根目录运行：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md
for v in running awaiting_human suspended succeeded failed superseded; do rg -q "(^|[^a-z_])${v}([^a-z_]|$)" "$SPEC" || exit 1; done
for v in draft sealed quarantined invalidated superseded; do rg -q "(^|[^a-z_])${v}([^a-z_]|$)" "$SPEC" || exit 1; done
for k in resume_token status_version record_human_event supersedes_step_run_id; do rg -q "$k" "$SPEC" || exit 1; done
rg -q '不是登录、会话或鉴权 token' "$SPEC"
rg -q '默认不设置自动超时' "$SPEC"
rg -q '不读取工作目录中的“最新文件”' "$SPEC"
test "$(git show --name-only --format= b0022d4 | sed '/^$/d' | sort | tr '\n' ' ')" = "HANDOFF.md PLAN.md openspec/learn-system-blackbox-architecture.md "
git diff --check
```

`verify-T.sh` 是全局未完成任务计数，不以零退出为本项通过条件；只保存输出，确认 D-03 提示中的 `awaiting_human` 与 `resume_token` 均非零。

## 人工语义判据

- §7.1 明确一个阶段人工队列只使用一个 StepRun，而不是每个决定新建 StepRun。
- 人工事件登记不消费 token；恢复操作原子消费 token。
- 合法迁移表覆盖等待、恢复、可恢复暂停、失败、成功、取代。
- `succeeded`、`failed`、`superseded` 为不可变终态。
- Artifact 生命周期与内容成熟度分别列出。
- §17 不在 Ledger 写入失败时制造虚假持久状态。

任一人工判据无唯一解释，即为失败，不能由标题或关键词命中抵消。
