# T-12 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示 T-12 失败，且全局 FAIL 合计为 2：
- `FAIL  T-12   §19 施工顺序说明 (期望 >=1, 实得 0)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证施工顺序说明出现
grep -q "非施工顺序\|前置层" "$SPEC" || { echo "缺失「非施工顺序/前置层」说明"; exit 1; }

# 2. 验证依赖拓扑展示
grep -q "L1 Artifact Ledger.*LineageGraph" "$SPEC" || { echo "缺失依赖拓扑图"; exit 1; }

# 3. 验证表格包含「层级」列
grep -q "|.*层级.*|" "$SPEC" || { echo "§19 表格缺失层级列"; exit 1; }

# 4. 代码排版审查
git diff --check || exit 1

# 5. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-12` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 2 严格单调减少至 **1**；
3. `git diff --check` 无格式异常。
