# T-07 TDD／文档门禁

## Red baseline

在执行修改前，运行全局 T 类机器判据并记录基线：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

当前基线应明确显示 T-07 失败，且全局 FAIL 合计为 8：
- `FAIL  T-07   KnowledgePack 映射表(缺失) (期望 0, 实得 8)`

## Green checks

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证全部 10 个核心目录关键字均在规格中出现
dmiss=0
for d in concepts entries assertions applicability-rules school-views evidence-links source-spans source-anchors query-contract; do
  grep -q "$d" "$SPEC" || { echo "映射表缺失条目: $d"; dmiss=$((dmiss+1)); }
done
test "$dmiss" -eq 0 || exit 1

# 2. 验证其余目录与非目标标注在 §16 中出现
sed -n '/## 16/,/## 17/p' "$SPEC" | grep -q "optional-vector-index" || { echo "§16 缺失 optional-vector-index"; exit 1; }
sed -n '/## 16/,/## 17/p' "$SPEC" | grep -q "本期不产出" || { echo "§16 缺失本期不产出标注"; exit 1; }

# 3. 验证取代声明在 §16 中出现
sed -n '/## 16/,/## 17/p' "$SPEC" | grep -q "取代.*KnowledgePack" || { echo "§16 缺失 KnowledgePack 取代声明"; exit 1; }

# 4. 代码排版审查
git diff --check || exit 1

# 5. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-07` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数由 8 严格单调减少至 **7**；
3. `git diff --check` 无格式异常。
