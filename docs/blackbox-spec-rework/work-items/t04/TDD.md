# T-04 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示以下 3 项失败，且全局 FAIL 合计为 13：
- `FAIL  T-04   G1-G7 已接线(缺失数) (期望 0, 实得 6)`
- `FAIL  T-04b  三级消费级别已写入 (期望 >=3, 实得 0)`
- `FAIL  T-04c  fail-closed 已声明 (期望 >=1, 实得 0)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证 G1 至 G7 全部出现（缺失数为 0）
gmiss=0
for g in G1 G2 G3 G4 G5 G6 G7; do
  grep -q "$g" "$SPEC" || { echo "缺失门禁代号: $g"; gmiss=$((gmiss+1)); }
done
test "$gmiss" -eq 0 || exit 1

# 2. 验证三级消费级别出现频次 (期望 >= 3)
test $(grep -c "INTERNAL_DEMO\|DEV_SEARCH\|PUBLIC_RELEASE" "$SPEC") -ge 3 || { echo "三级消费级别出现频次不足"; exit 1; }

# 3. 验证 fail-closed 声明出现 (期望 >= 1)
test $(grep -c "fail-closed" "$SPEC") -ge 1 || { echo "缺失 fail-closed 声明"; exit 1; }

# 4. 验证 §13 M5 包含 G1–G6 对应表及执行工位标注
sed -n '/## 13/,/## 14/p' "$SPEC" | grep -q "G1" || { echo "§13 缺失 G1 接线"; exit 1; }
sed -n '/## 13/,/## 14/p' "$SPEC" | grep -q "G6" || { echo "§13 缺失 G6 接线"; exit 1; }

# 5. 验证 §16 M8 包含显式输入参数与三级门槛表（引用 G7）
sed -n '/## 16/,/## 17/p' "$SPEC" | grep -q "INTERNAL_DEMO" || { echo "§16 缺失 INTERNAL_DEMO"; exit 1; }
sed -n '/## 16/,/## 17/p' "$SPEC" | grep -q "G7" || { echo "§16 缺失 G7 引用"; exit 1; }

# 6. 代码排版审查
git diff --check || exit 1

# 7. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-04` 由 FAIL 转为 PASS；
   - `T-04b` 由 FAIL 转为 PASS；
   - `T-04c` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 13 严格单调减少至 **10**；
3. `git diff --check` 无格式异常。
