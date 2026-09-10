# T-08 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示 T-08 与 T-08b 失败，且全局 FAIL 合计为 7：
- `FAIL  T-08   Tag 三接口已承接 (期望 >=3, 实得 0)`
- `FAIL  T-08b  Tag 五字段已写入 (期望 >=3, 实得 0)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证 Tag 三个接口名称出现频次 (期望 >= 3)
test $(grep -c "MarkContentBinding\|EvidenceBundle\|盘面概念字典" "$SPEC") -ge 3 || { echo "Tag 三接口频次不足"; exit 1; }

# 2. 验证 Tag 关键字段名称出现频次 (期望 >= 3)
test $(grep -c "omen_carrying\|condition_affordance\|school_variance_display" "$SPEC") -ge 3 || { echo "Tag 关键字段频次不足"; exit 1; }

# 3. 验证「不含规则 DSL」硬限制声明
grep -q "不含规则 DSL\|不含规则DSL" "$SPEC" || { echo "缺失「不含规则 DSL」限制声明"; exit 1; }

# 4. 验证「是否改变当前判断」与「UI 不得猜测」声明
grep -q "是否改变当前判断" "$SPEC" || { echo "缺失「是否改变当前判断」字段"; exit 1; }
grep -q "UI 不得猜测\|UI不得猜测" "$SPEC" || { echo "缺失「UI 不得猜测」声明"; exit 1; }

# 5. 代码排版审查
git diff --check || exit 1

# 6. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-08` 由 FAIL 转为 PASS；
   - `T-08b` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 7 严格单调减少至 **5**；
3. `git diff --check` 无格式异常。
