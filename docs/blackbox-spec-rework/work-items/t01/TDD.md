# T-01 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示 T-01 失败，且全局 FAIL 合计为 14：
- `FAIL  T-01   三层术语已写入 (期望 >=3, 实得 1)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证术语核心标识与路径出现频次 (期望 >= 3)
test $(grep -c "co_shared_\|homograph_id\|schemas/shared/canon" "$SPEC") -ge 3 || { echo "术语标识与路径频次不足"; exit 1; }

# 2. 验证 §12 M4 章节包含「确定性」免模型说明
sed -n '/## 12/,/## 13/p' "$SPEC" | grep -q "确定性" || { echo "§12 缺失确定性免模型说明"; exit 1; }

# 3. 验证 L1/L2/L3 关键字段与规则
grep -q "co_shared_<domain>_NN" "$SPEC" || { echo "缺失 co_shared ID 规范"; exit 1; }
grep -q "hg_<4位数字>\|hg_NNNN" "$SPEC" || { echo "缺失 hg ID 规范"; exit 1; }
grep -q "schemas/shared/canon" "$SPEC" || { echo "缺失 canon 存放路径"; exit 1; }
grep -q "schemas/shared/homographs" "$SPEC" || { echo "缺失 homographs 存放路径"; exit 1; }
grep -q "禁止裸绑字面" "$SPEC" || { echo "缺失 L2 禁止裸绑字面约束"; exit 1; }

# 4. 验证 §5 Contract Registry 追加了冻结输入声明
sed -n '/## 5/,/## 6/p' "$SPEC" | grep -q "schemas/shared/canon" || { echo "§5 Contract Registry 未声明冻结输入"; exit 1; }

# 5. 代码排版与格式审查
git diff --check || exit 1

# 6. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-01` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 14 严格单调减少至 **13**；
3. `git diff --check` 无格式异常。
