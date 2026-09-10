# T-10 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示 T-10 失败，且全局 FAIL 合计为 4：
- `FAIL  T-10   异常页终态三值 (期望 >=3, 实得 0)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证异常页终态三值频次 (期望 >= 3)
test $(grep -c "manually_transcribed\|known_unrecognizable\|deferred" "$SPEC") -ge 3 || { echo "异常页三终态频次不足"; exit 1; }

# 2. 验证三个枚举各自出现
grep -q "manually_transcribed" "$SPEC" || { echo "缺失 manually_transcribed"; exit 1; }
grep -q "known_unrecognizable" "$SPEC" || { echo "缺失 known_unrecognizable"; exit 1; }
grep -q "deferred" "$SPEC" || { echo "缺失 deferred"; exit 1; }

# 3. 验证 M2 Gate 放行与阻断说明
grep -q "deferred.*阻断\|阻断.*deferred" "$SPEC" || { echo "缺失 deferred 阻断说明"; exit 1; }
grep -q "客观不可识别.*不是失败\|失败为零" "$SPEC" || { echo "缺失「客观不可识别不是失败」说明"; exit 1; }

# 4. 代码排版审查
git diff --check || exit 1

# 5. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-10` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 4 严格单调减少至 **3**；
3. `git diff --check` 无格式异常。
