# T-09 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示 T-09 失败，且全局 FAIL 合计为 5：
- `FAIL  T-09   Orchestrator 六项查询(缺失) (期望 0, 实得 6)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证六项查询契约全部存在（缺失数必须为 0）
for q in RunStatus StageProgress PendingQueue BlockingReasons ReworkImpact ThroughputEstimate; do
  grep -q "$q" "$SPEC" || { echo "缺失查询契约: $q"; exit 1; }
done

# 2. 验证五个 PendingQueue 显式列出
grep -q "M2 异常页与低置信字" "$SPEC" || { echo "缺失 M2 异常页队列"; exit 1; }
grep -q "M3 边界分歧" "$SPEC" || { echo "缺失 M3 边界分歧队列"; exit 1; }
grep -q "M4 类别分歧" "$SPEC" || { echo "缺失 M4 类别分歧队列"; exit 1; }
grep -q "M6 待签发" "$SPEC" || { echo "缺失 M6 待签发队列"; exit 1; }
grep -q "M7 待裁决" "$SPEC" || { echo "缺失 M7 待裁决队列"; exit 1; }

# 3. 验证 §7 进度事件上报约束
grep -q "进度事件" "$SPEC" || { echo "缺失「进度事件」约束"; exit 1; }

# 4. 代码排版审查
git diff --check || exit 1

# 5. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-09` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 5 严格单调减少至 **4**；
3. `git diff --check` 无格式异常。
