# T-13 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示 T-13 失败，且全局 FAIL 合计为 1：
- `FAIL  T-13   章节状态标签 (期望 >=16, 实得 1)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证状态标签总数 (期望 >= 16)
count=$(grep -c "^状态：" "$SPEC")
test "$count" -ge 16 || { echo "章节状态标签数量不足: $count (期望 >= 16)"; exit 1; }

# 2. 验证严禁出现「最终规范」
grep -c "^状态：最终规范" "$SPEC" | grep -q "^0$" || { echo "存在被标为最终规范的章节"; exit 1; }

# 3. 代码排版审查
git diff --check || exit 1

# 4. 全局 T 机器判据验证（必须达到 0 FAIL！）
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-13` 由 FAIL 转为 PASS；
   - `T-13b` 保持 PASS；
   - **全局 FAIL 总数达到 0，verify-T.sh 以退出码 0 成功退出**；
3. `git diff --check` 无格式异常。
