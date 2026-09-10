# T-05 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示 T-05 失败，且全局 FAIL 合计为 10：
- `FAIL  T-05   evidence_level 两档 (期望 >=2, 实得 0)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证 offset_level 与 glyphbox_level 出现频次 (期望 >= 2)
test $(grep -c "offset_level\|glyphbox_level" "$SPEC") -ge 2 || { echo "evidence_level 两档出现频次不足"; exit 1; }

# 2. 验证 §11 M3 包含 evidence_level 子节与两档定义
sed -n '/## 11/,/## 12/p' "$SPEC" | grep -q "offset_level" || { echo "§11 缺失 offset_level"; exit 1; }
sed -n '/## 11/,/## 12/p' "$SPEC" | grep -q "glyphbox_level" || { echo "§11 缺失 glyphbox_level"; exit 1; }

# 3. 验证 §11 M3 包含 PUBLIC_RELEASE 强约束说明
sed -n '/## 11/,/## 12/p' "$SPEC" | grep -q "PUBLIC_RELEASE" || { echo "§11 缺失 PUBLIC_RELEASE 约束"; exit 1; }

# 4. 验证 §13 M5 G3 门禁包含 evidence_level 校验说明
sed -n '/## 13/,/## 14/p' "$SPEC" | grep -q "evidence_level" || { echo "§13 缺失 evidence_level 校验"; exit 1; }

# 5. 代码排版审查
git diff --check || exit 1

# 6. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-05` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 10 严格单调减少至 **9**；
3. `git diff --check` 无格式异常。
