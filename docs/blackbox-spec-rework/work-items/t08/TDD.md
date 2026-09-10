# T-08 TDD／文档门禁

## 1. 语义门禁设计

在 `docs/blackbox-spec-rework/verify-T.sh` 中对 §1 与 §16.3 实施结构与语义校验：
1. 校验 Tag 三个核心接口（`最小盘面概念字典`、`MarkContentBinding`、`EvidenceBundle`）必须同时在 §1 与 §16.3 中明确承接；
2. 校验概念字典必须严格声明「不含规则 DSL」；
3. 校验 Tag 侧 G4 必须显式命名空间化为 `TAG_SYSTEM_DESIGN.md §12.2 的 G4`，严禁与规格正文 G4 内容分层门禁混同；
4. 解析 §16.3.2 字段表格，确保五个关键字段（`omen_carrying`、`condition_affordance`、`school_variance_display`、`concept_id`、`是否改变当前判断`）均出现，且生产 Module 列**绝对不得包含 M5**（M5 仅作为 Validator，不得作为生产者）。

```bash
# T-08 语义门禁：Tag 三接口、五字段、M5 生产者排除及 G4 命名空间
sec163=$(sed -n '/^### 16\.3 /,/^## 17/p' "$SPEC")
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

# 2. Tag 侧 G4 命名空间消歧
if printf '%s\n' "$sec01" | grep -Eq 'TAG_SYSTEM_DESIGN\.md §12\.2.*G4' \
  && printf '%s\n' "$sec163" | grep -Eq 'TAG_SYSTEM_DESIGN\.md §12\.2.*G4' \
  && ! printf '%s\n' "$sec163" | grep -Eq '解除.*（G4）'; then
  printf 'PASS  T-08s Tag G4 namespaced to TAG_SYSTEM_DESIGN.md §12.2\n'
else
  printf 'FAIL  T-08s Tag G4 missing TAG_SYSTEM_DESIGN.md namespace\n'; FAILED=$((FAILED+1))
fi

# 3. §16.3.2 字段表格解析与 M5 生产者排除
t08_table_res=$(printf '%s\n' "$sec163" | awk -F'|' '
  BEGIN {
    f["omen_carrying"]=1
    f["condition_affordance"]=1
    f["school_variance_display"]=1
    f["concept_id"]=1
    f["是否改变当前判断"]=1
  }
  /^\|/ && $0 !~ /^\|---/ && $0 !~ /字段名.*语义定义/ {
    name=$2
    prod=$4
    pack=$5
    gsub(/[`[:space:]]/, "", name)
    if (name in f) {
      seen[name]++
      if (prod ~ /M5/) m5_producer[name]=prod
    }
  }
  END {
    err=""
    for (k in f) {
      if (seen[k] != 1) err=err k "出现" seen[k] "次; "
      if (k in m5_producer) err=err k "生产列包含M5(" m5_producer[k] "); "
    }
    if (err == "") print "OK"
    else print err
  }
')
```

## 2. Red baseline

门禁加固后、规格修改前：
- `FAIL  T-08s Tag G4 missing TAG_SYSTEM_DESIGN.md namespace`
- `FAIL  T-08s §16.3 table issue: condition_affordance生产列包含M5( M4 / M5 ); omen_carrying生产列包含M5( M4 / M5 );`
- `FAIL 合计: 2`，退出码为 2。

## 3. Green checks

修改 §1 与 §16.3 消歧 G4 并剔除 M5 生产者身份后：
- `PASS  T-08s Tag interface present in §1 and §16.3: 最小盘面概念字典`
- `PASS  T-08s Tag interface present in §1 and §16.3: MarkContentBinding`
- `PASS  T-08s Tag interface present in §1 and §16.3: EvidenceBundle`
- `PASS  T-08s concept dictionary preserves rule DSL restriction`
- `PASS  T-08s Tag G4 namespaced to TAG_SYSTEM_DESIGN.md §12.2`
- `PASS  T-08s §16.3 table 5 fields present and M5 excluded from producers`
- `bash docs/blackbox-spec-rework/verify-T.sh` 退出码为 0，FAIL 合计为 0。

## 4. 负向变异测试

1. 变异 1：在 `omen_carrying` 生产 Module 列加入 M5，门禁必须报 FAIL（退出码 1）；
2. 变异 2：删除 G4 的 `TAG_SYSTEM_DESIGN.md §12.2` 命名空间前缀，门禁必须报 FAIL（退出码 1）；
3. 变异 3：删除「不含规则 DSL」硬限制，门禁必须报 FAIL（退出码 1）；
4. 变异 4：删除 `EvidenceBundle` 接口，门禁必须报 FAIL（退出码 1）；
5. 恢复规格后，退出码重归 0。
