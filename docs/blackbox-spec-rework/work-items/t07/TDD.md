# T-07 TDD／文档门禁（R2 返工版）

## 1. 判据设计

R1 门禁的缺陷是**只做子串匹配**：`query-contract` 只要含 `QueryContractPack` 即通过（追加 `EvidenceMapPack` 仍通过），`optional-vector-index` 只要匹配「本期不产出.*§21」即通过（追加归属仍通过），取代声明只要同一节出现「取代…KnowledgePack」即通过（改成「不得取代」仍通过）。

R2 改为规范化（去反引号与空白）后**精确相等**，并对否定语义做显式拒绝。

## 2. 门禁实现

```bash
# T-07 语义门禁：§16.2 KnowledgePack 双向映射表精确解析。
# 右列必须是唯一落点：既不能缺少正确归属，也不能在正确归属之后追加第二个子包，
# 因此改为规范化后精确相等，而不是子串匹配。
sec162=$(sed -n '/^### 16\.2 /,/^### 16\.3 /p' "$SPEC")
t07_errs=$(printf '%s\n' "$sec162" | awk -F'|' '
  function nz(s) { gsub(/`/, "", s); gsub(/[[:space:]]/, "", s); return s }
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
    c1=nz($2)
    c2=nz($3)
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
    if (target["query-contract"] != "QueryContractPack（查询契约与接口定义）") err=err "query-contract归属[" target["query-contract"] "]，期望[QueryContractPack（查询契约与接口定义）]; "
    if (target["optional-vector-index"] != "本期不产出（依据§21非目标）") err=err "optional-vector-index归属[" target["optional-vector-index"] "]，期望[本期不产出（依据§21非目标）]; "
    if (err == "") print "OK"
    else print err
  }
')

if [ "$t07_errs" = "OK" ]; then
  printf 'PASS  T-07s §16.2 映射表15项唯一且query-contract正确归属QueryContractPack\n'
else
  printf 'FAIL  T-07s §16.2 映射表不合规: %s\n' "$t07_errs"; FAILED=$((FAILED+1))
fi

# 取代声明必须是同一句肯定语义：同一行内同时出现 PublicationPackage、KnowledgeDataPack、
# 正式取代、KnowledgePack；「不得取代」等否定句一律判失败。
t07_decl=0
if printf '%s\n' "$sec162" | grep -F '正式取代' | grep -F 'PublicationPackage' \
  | grep -F 'KnowledgeDataPack' | grep -Fq 'KnowledgePack'; then
  t07_decl=1
fi
if printf '%s\n' "$sec162" | grep -Eq '不得取代|不予取代|禁止取代|未予取代|不取代'; then
  t07_decl=0
fi
if [ "$t07_decl" = "1" ]; then
  printf 'PASS  T-07s §16.2 affirmative replacement statement with PublicationPackage and KnowledgeDataPack\n'
else
  printf 'FAIL  T-07s §16.2 replacement statement missing or negated\n'; FAILED=$((FAILED+1))
fi
```

## 3. Red baseline（加固前，证明假绿）

加固前，三个变异全部返回 0：

```text
t07-1   exit=0   T-07 给 query-contract 追加 EvidenceMapPack
t07-2   exit=0   T-07 给 optional-vector-index 追加「同时归入 SearchIndexPack」
t07-3   exit=0   T-07 把「正式取代」改成「不得取代」
```

## 4. Green checks（加固后，正常规格）

```text
退出码: 0
PASS  T-07s §16.2 映射表15项唯一且query-contract正确归属QueryContractPack
PASS  T-07s §16.2 affirmative replacement statement with PublicationPackage and KnowledgeDataPack
FAIL 合计: 0
```

## 5. 负向变异（加固后）

每次变异从未修改的权威规格重新复制到 `/tmp/g3-r2-<case>.md`，只修改该副本，单独运行 `SPEC=/tmp/g3-r2-<case>.md bash docs/blackbox-spec-rework/verify-T.sh`。

| 变异 | 内容 | 加固前退出码 | 加固后退出码 | 触发的断言 |
|---|---|---|---|---|
| t07-1 | `query-contract` 追加 `EvidenceMapPack` | 0（假绿） | 1 | 映射表精确归属：实际 `QueryContractPack（查询契约与接口定义）EvidenceMapPack`，期望 `QueryContractPack（查询契约与接口定义）` |
| t07-2 | `optional-vector-index` 追加「同时归入 SearchIndexPack」 | 0（假绿） | 1 | 映射表精确归属：实际 `本期不产出（依据§21非目标）同时归入SearchIndexPack`，期望 `本期不产出（依据§21非目标）` |
| t07-3 | 「正式取代」→「不得取代」 | 0（假绿） | 1 | `replacement statement missing or negated` |

每次变异只触发 1 条 FAIL，无连带误报。

## 6. 恢复验证

恢复权威规格后重新运行门禁，退出码为 0、`FAIL 合计: 0`；`git diff --check` 退出 0。
