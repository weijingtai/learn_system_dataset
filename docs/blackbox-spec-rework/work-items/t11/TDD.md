# T-11 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示 T-11 失败，且全局 FAIL 合计为 3：
- `FAIL  T-11   §19 实测数字已写入 (期望 >=2, 实得 0)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证实测数字出现频次 (期望 >= 2)
test $(grep -c "496\|148" "$SPEC") -ge 2 || { echo "实测数字 496/148 频次不足"; exit 1; }

# 2. 验证 18 键碰撞说明
grep -q "18 键\|18键" "$SPEC" || { echo "缺失 18 键碰撞说明"; exit 1; }

# 3. 验证 §19 表格行数扩展 (期望 >= 21)
rows=$(grep -c "^|" <(sed -n '/## 19/,/## 20/p' "$SPEC"))
test "$rows" -ge 21 || { echo "§19 表格行数不足: $rows (期望 >= 21)"; exit 1; }

# 4. 代码排版审查
git diff --check || exit 1

# 5. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-11` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 3 严格单调减少至 **2**；
3. `git diff --check` 无格式异常。
