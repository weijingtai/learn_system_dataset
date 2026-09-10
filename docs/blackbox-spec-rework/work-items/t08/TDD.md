# T-08 TDD／文档门禁（R2 返工版）

## 1. 判据设计

R1 门禁的缺陷是**只查字段名与 M5 缺席**：生产 Module 与归属子包完全不校验，接口只查「名字是否出现在 §1 与 §16.3」，因此把 `concept_id` 改成 `M2 / SourceAssetPack`、只改 Module、只改 Package、把接口改成错误供给包，门禁都仍返回 0。

R2 改为：

- 三接口：解析 §16.3.1 每个编号项的「供给子包」行，并与 §1 的「由 … 供给」片段一起做规范化精确相等；
- 五字段：解析 §16.3.2 表格，`生产Module|归属子包` 规范化后与期望逐字段精确相等，数据行必须恰好 5 行，生产列不得含 M5。

## 2. 门禁实现

```bash
# T-08 语义门禁：Tag 三接口供给包、五字段 owner/package、M5 生产者排除及 G4 命名空间。
# 生产 Module 与归属子包必须逐字段精确匹配：只校验字段唯一和 M5 缺席会漏掉错误归属。
sec163=$(sed -n '/^### 16\.3 /,/^## 17/p' "$SPEC")
sec1631=$(sed -n '/^#### 16\.3\.1 /,/^#### 16\.3\.2 /p' "$SPEC")
sec01=$(sed -n '/^## 1\.[[:space:]]/,/^## 2\.[[:space:]]/p' "$SPEC")

# 1. 三接口承接与“不含规则 DSL”
for tag_iface in '最小盘面概念字典' 'MarkContentBinding' 'EvidenceBundle'; do
  if printf '%s\n' "$sec163" | grep -Fq "$tag_iface" && printf '%s\n' "$sec01" | grep -Fq "$tag_iface"; then
    printf 'PASS  T-08s Tag interface present in §1 and §16.3: %s\n' "$tag_iface"
  else
    printf 'FAIL  T-08s Tag interface missing: %s\n' "$tag_iface"; FAILED=$((FAILED+1))
  fi
done

if printf '%s\n' "$sec163" | grep -Fq '不含规则 DSL' && printf '%s\n' "$sec01" | grep -Fq '不含规则 DSL'; then
  printf 'PASS  T-08s concept dictionary preserves rule DSL restriction\n'
else
  printf 'FAIL  T-08s concept dictionary missing rule DSL restriction\n'; FAILED=$((FAILED+1))
fi

# 2. 三接口供给子包精确校验：§16.3.1 的「供给子包」行与 §1 的「由 … 供给」片段必须同时正确
t08_supply_1631() {
  printf '%s\n' "$sec1631" | awk -v name="$1" '
    function nz(s){ gsub(/`/,"",s); gsub(/[*]/,"",s); gsub(/[-]/,"",s); gsub(/[[:space:]]/,"",s); gsub(/：/,"",s); gsub(/；/,"",s); return s }
    /^[0-9]+\.[[:space:]]+\*\*/ { inb = (index($0, name) > 0) }
    inb && nz($0) ~ /供给子包/ { print nz($0); exit }
  '
}
t08_supply_sec01() {
  printf '%s\n' "$sec01" | grep -F "$1" | head -1 \
    | sed -n 's/^[^由]*由[[:space:]]*\([^供]*\)供给.*$/\1/p' \
    | sed -e 's/`//g' -e 's/[[:space:]]//g'
}
for t08_iface_pair in '最小盘面概念字典:KnowledgeDataPack' 'MarkContentBinding:KnowledgeDataPack与RuleIndexPack' 'EvidenceBundle:EvidenceMapPack'; do
  t08_iface=${t08_iface_pair%%:*}; t08_pkg=${t08_iface_pair#*:}
  if [ "$(t08_supply_1631 "$t08_iface")" = "供给子包由${t08_pkg}供给" ] \
    && [ "$(t08_supply_sec01 "$t08_iface")" = "$t08_pkg" ]; then
    printf 'PASS  T-08s interface supply package: %s -> %s\n' "$t08_iface" "$t08_pkg"
  else
    printf 'FAIL  T-08s interface supply package mismatch: %s (期望 %s)\n' "$t08_iface" "$t08_pkg"; FAILED=$((FAILED+1))
  fi
done

# 3. Tag 侧 G4 命名空间消歧
if printf '%s\n' "$sec01" | grep -Eq 'TAG_SYSTEM_DESIGN\.md §12\.2.*G4' \
  && printf '%s\n' "$sec163" | grep -Eq 'TAG_SYSTEM_DESIGN\.md §12\.2.*G4' \
  && ! printf '%s\n' "$sec163" | grep -Eq '解除.*（G4）'; then
  printf 'PASS  T-08s Tag G4 namespaced to TAG_SYSTEM_DESIGN.md §12.2\n'
else
  printf 'FAIL  T-08s Tag G4 missing TAG_SYSTEM_DESIGN.md namespace\n'; FAILED=$((FAILED+1))
fi

# 4. §16.3.2 字段表格：五字段各恰好一次，生产 Module 与归属子包逐字段精确相等，生产列不得含 M5
t08_table_res=$(printf '%s\n' "$sec163" | awk -F'|' '
  function nz(s){ gsub(/`/,"",s); gsub(/[[:space:]]/,"",s); return s }
  BEGIN {
    want["omen_carrying"]="M4|KnowledgeDataPack"
    want["condition_affordance"]="M4|RuleIndexPack与KnowledgeDataPack"
    want["school_variance_display"]="M4/M6|KnowledgeDataPack"
    want["concept_id"]="M4|KnowledgeDataPack"
    want["是否改变当前判断"]="M4/M7/M6|KnowledgeDataPack（MarkContentBinding）"
  }
  /^\|/ && $0 !~ /^\|---/ && $0 !~ /字段名.*语义定义/ {
    name=nz($2); prod=nz($4); pack=nz($5)
    rows++
    if (name in want) {
      seen[name]++
      if ((prod "|" pack) != want[name]) err=err name "实际[" prod "|" pack "]，期望[" want[name] "]; "
      if (prod ~ /M5/) err=err name "生产列包含M5; "
    }
  }
  END {
    if (rows != 5) err=err "数据行=" rows "; "
    for (k in want) if (seen[k] != 1) err=err k "出现" seen[k] "次; "
    print (err == "" ? "OK" : err)
  }
')

if [ "$t08_table_res" = "OK" ]; then
  printf 'PASS  T-08s §16.3 table 5 fields with exact producer ownership and no M5 producer\n'
else
  printf 'FAIL  T-08s §16.3 table issue: %s\n' "$t08_table_res"; FAILED=$((FAILED+1))
fi
```

M5 的职责口径在三处保持一致：门禁在生产列拒绝 M5；§16.3.2 表格与 §16.3.2 说明均写明「M5 仅作为 Validator，不得作为生产者」；§13 明文「M5 仅作为验证工位，不负责生产」。

## 3. Red baseline（加固前，证明假绿）

```text
t08-1   exit=0   T-08 把 concept_id 改为 M2 / SourceAssetPack
t08-2   exit=0   T-08 只改错误 Module（omen_carrying M4→M2，Package 不变）
t08-3   exit=0   T-08 只改错误 Package（school_variance_display KnowledgeDataPack→RuleIndexPack，Module 不变）
t08-4   exit=0   T-08 将 EvidenceBundle 接口改为错误供给包
```

## 4. Green checks（加固后，正常规格）

```text
退出码: 0
PASS  T-08s Tag interface present in §1 and §16.3: 最小盘面概念字典
PASS  T-08s Tag interface present in §1 and §16.3: MarkContentBinding
PASS  T-08s Tag interface present in §1 and §16.3: EvidenceBundle
PASS  T-08s concept dictionary preserves rule DSL restriction
PASS  T-08s interface supply package: 最小盘面概念字典 -> KnowledgeDataPack
PASS  T-08s interface supply package: MarkContentBinding -> KnowledgeDataPack与RuleIndexPack
PASS  T-08s interface supply package: EvidenceBundle -> EvidenceMapPack
PASS  T-08s Tag G4 namespaced to TAG_SYSTEM_DESIGN.md §12.2
PASS  T-08s §16.3 table 5 fields with exact producer ownership and no M5 producer
FAIL 合计: 0
```

## 5. 负向变异（加固后）

每次变异从未修改的权威规格重新复制到 `/tmp/g3-r2-<case>.md`，只修改该副本，单独运行 `SPEC=/tmp/g3-r2-<case>.md bash docs/blackbox-spec-rework/verify-T.sh`。

| 变异 | 内容 | 加固前退出码 | 加固后退出码 | 触发的断言 |
|---|---|---|---|---|
| t08-1 | `concept_id` → `M2 / SourceAssetPack` | 0（假绿） | 1 | 实际 `M2/SourceAssetPack\|KnowledgeDataPack`，期望 `M4\|KnowledgeDataPack` |
| t08-2 | 只改 Module：`omen_carrying` M4→M2 | 0（假绿） | 1 | 实际 `M2\|KnowledgeDataPack`，期望 `M4\|KnowledgeDataPack` |
| t08-3 | 只改 Package：`school_variance_display` → `RuleIndexPack` | 0（假绿） | 1 | 实际 `M4/M6\|RuleIndexPack`，期望 `M4/M6\|KnowledgeDataPack` |
| t08-4 | `EvidenceBundle` 供给包改为 `SearchIndexPack`（§1 与 §16.3.1） | 0（假绿） | 1 | `interface supply package mismatch: EvidenceBundle (期望 EvidenceMapPack)` |

每次变异只触发 1 条 FAIL，无连带误报。

## 6. 恢复验证

恢复权威规格后重新运行门禁，退出码 0、`FAIL 合计: 0`；`git diff --check` 退出 0。
