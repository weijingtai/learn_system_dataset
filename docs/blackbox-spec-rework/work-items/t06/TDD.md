# T-06 TDD／文档门禁

## Red baseline

R1 必须验证新语义门禁确实能识别旧规格，而不是把旧的全局计数当作 Red：

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

```bash
tmp_spec=$(mktemp)
cp openspec/learn-system-blackbox-architecture.md "$tmp_spec"
sed -i.bak 's/  1\. `KnowledgeEntry`;/  1. `EvidenceLink`;/; s/  3\. `EvidenceLink`;/  3. `KnowledgeEntry`;/' \
  openspec/learn-system-blackbox-architecture.md
if bash docs/blackbox-spec-rework/verify-T.sh; then
  echo "T-06 Red 未触发"; exit 1
fi
cp "$tmp_spec" openspec/learn-system-blackbox-architecture.md
rm -f "$tmp_spec" "$tmp_spec.bak" openspec/learn-system-blackbox-architecture.md.bak
```

该变异交换 Assertion/EvidenceLink 相邻项，必须使 `T-06s` 为 FAIL。

## Green checks

R1 语义门禁：`verify-T.sh` 的 `T-06s` 只在 §16 EvidenceMapPack 专属区间
找到恰好 7 个编号条目，并按
`KnowledgeEntry → Assertion → EvidenceLink → SourceSpan → SourceAnchor → OcrPage/字框坐标 → SourceAsset 页标识`
逐项精确匹配时通过；删除首项、末项、交换任意相邻项，或只在散文中保留词语时必须非零退出。

执行 Agent 完成修改后，必须运行以下精确命令组合验证 Green 状态：

```bash
SPEC=openspec/learn-system-blackbox-architecture.md

# 1. 验证 EvidenceMapPack 出现频次 (期望 >= 2)
test $(grep -c "EvidenceMapPack" "$SPEC") -ge 2 || { echo "EvidenceMapPack 频次不足"; exit 1; }

# 2. 验证 §16 M8 包含「字框」说明
sed -n '/## 16/,/## 17/p' "$SPEC" | grep -q "字框" || { echo "§16 缺失字框说明"; exit 1; }

# 3. 验证专属顺序门禁与坐标约束
bash docs/blackbox-spec-rework/verify-T.sh | grep -q '^PASS  T-06s' || { echo "T-06s 未通过"; exit 1; }
sed -n '/## 16/,/## 17/p' "$SPEC" | grep -q "同源可换算" || { echo "§16 缺失坐标同源可换算约束"; exit 1; }

# 4. 代码排版审查
git diff --check || exit 1

# 5. 全局 T 机器判据验证
bash docs/blackbox-spec-rework/verify-T.sh
```

## 判定合格标准

1. Green checks 全部以退出码 0 通过；
2. `verify-T.sh` 中：
   - `T-06s` 由 Red 变为 PASS；
   - `T-06` 由 FAIL 转为 PASS；
   - 全局 FAIL 总数保持既有基线，仅减少 T-06 对应失败，不得引入新增失败；
3. `git diff --check` 无格式异常。
