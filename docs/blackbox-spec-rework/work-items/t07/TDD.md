# T-07 TDD／文档门禁

## 1. 语义门禁设计

在 `docs/blackbox-spec-rework/verify-T.sh` 中对 §16.2 实施精确表格解析：
1. 限定解析范围为 `### 16.2` 至 `### 16.3`；
2. 校验 15 个早期目录条目各且仅出现一次，总数据行数严格等于 15；
3. `query-contract` 必须且仅能归属 `QueryContractPack`，严禁归入 `RuleIndexPack` 或 `SearchIndexPack`；
4. `optional-vector-index` 必须保留非目标声明；
5. 表前必须包含 `PublicationPackage` 取代旧 `KnowledgePack` 的声明。

```bash
sec162=$(sed -n '/^### 16\.2 /,/^### 16\.3 /p' "$SPEC")
t07_errs=$(printf '%s\n' "$sec162" | awk -F'|' '
  BEGIN {
    wanted["release-manifest"]=1
    wanted["schema"]=1
    wanted["concepts"]=1
    wanted["entries"]=1
    wanted["assertions"]=1
    wanted["applicability-rules"]=1
    wanted["school-views"]=1
    wanted["evidence-links"]=1
    wanted["source-spans"]=1
    wanted["source-anchors"]=1
    wanted["scan-assets-or-references"]=1
    wanted["exact-search-index"]=1
    wanted["fulltext-index"]=1
    wanted["optional-vector-index"]=1
    wanted["query-contract"]=1
  }
  /^\|/ && $0 !~ /^\|---/ && $0 !~ /早期.*目录/ {
    c1=$2
    c2=$3
    gsub(/[`[:space:]]/, "", c1)
    if (c1 in wanted) {
      seen[c1]++
      target[c1]=c2
    }
    total++
  }
  END {
    err=""
    if (total != 15) err=err "行数!=15(" total "); "
    for (k in wanted) {
      if (seen[k] != 1) err=err k "=" seen[k] "; "
    }
    if (target["query-contract"] !~ /QueryContractPack/) err=err "query-contract未归属QueryContractPack; "
    if (target["query-contract"] ~ /RuleIndexPack|SearchIndexPack/) err=err "query-contract错归IndexPack; "
    if (target["optional-vector-index"] !~ /本期不产出.*§21/) err=err "optional-vector-index缺非目标; "
    if (err == "") print "OK"
    else print err
  }
')
```

## 2. Red baseline

门禁加固后、规格修改前：
- `FAIL  T-07s §16.2 映射表不合规: query-contract未归属QueryContractPack; query-contract错归IndexPack;`
- `verify-T.sh` 退出码为 1。

## 3. Green checks

修改 §16.2 将 `query-contract` 映射修正为 `QueryContractPack（查询契约与接口定义）` 后：
- `PASS  T-07s §16.2 映射表15项唯一且query-contract正确归属QueryContractPack`
- `PASS  T-07s §16.2 包含KnowledgePack取代声明`
- `bash docs/blackbox-spec-rework/verify-T.sh` 退出码为 0，FAIL 合计为 0。

## 4. 负向变异测试

1. 变异 1：将 `query-contract` 改回 `RuleIndexPack`，门禁必须以退出码 1 失败；
2. 变异 2：删除任一行（如 `schema`），门禁因行数不足或缺项以退出码 1 失败；
3. 变异 3：删除取代声明，门禁因缺失声明以退出码 1 失败。
4. 恢复规格后，重新验证退出码为 0。
