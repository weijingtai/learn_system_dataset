# D-07 TDD 机器判据（R2 返工版）

## 1. 判据设计

R1 门禁的缺陷是**跨块代偿**：`TechniqueProfilePack` 与 `QueryContractPack` 的要素用整节 `grep` 校验，`RuleIndexPack` 的版本声明完全没有独立校验，因此 §16 其他段落（尤其 `ReleaseManifest` 的「Schema/Profile 版本」）可以代替被删内容让门禁变绿。

R2 改为按专属段切片后逐块断言：

- 锚点：三份契约各自的导语行，在全文中必须**恰好出现一次**；
- 切片：从导语行起，到下一个专属段导语或下一个 Markdown 标题为止；
- 任一块缺失或锚点歧义 → FAIL（fail-closed，不允许静默跳过）。

```bash
# D-07 语义门禁：TechniqueProfilePack / QueryContractPack / RuleIndexPack 三份契约
# 必须各自在专属段内闭合。§16 其余文字（如 ReleaseManifest 的「Schema/Profile 版本」）
# 不得跨块代偿，因此先按专属段导语切片，再逐块断言，而不是对整节做关键词 grep。
sec13=$(sed -n '/^## 13[. ]/,/^## 14[. ]/p' "$SPEC")

tp_anchor='承载各术数领域确定性事实结构与规则语法标准'
qc_anchor='规范发布包对外暴露的确定性只读查询契约'
ri_anchor='承载确定性适用规则索引'

d07_blocks=$(awk -v tp="$tp_anchor" -v qc="$qc_anchor" -v ri="$ri_anchor" '
  /^#/ { cur = "" }
  index($0, tp) > 0 { cur = "TP" }
  index($0, qc) > 0 { cur = "QC" }
  index($0, ri) > 0 { cur = "RI" }
  cur != "" { print cur "\t" $0 }
' "$SPEC")

d07_block() { printf '%s\n' "$d07_blocks" | awk -F'\t' -v k="$1" '$1 == k { sub(/^[^\t]*\t/, ""); print }'; }
d07_f() { printf '%s\n' "$1" | grep -Fq "$2"; }
d07_e() { printf '%s\n' "$1" | grep -Eq "$2"; }

for d07_pair in "TP:$tp_anchor" "QC:$qc_anchor" "RI:$ri_anchor"; do
  d07_key=${d07_pair%%:*}; d07_anchor=${d07_pair#*:}
  if [ -n "$(d07_block "$d07_key" | grep -v '^$')" ] && [ "$(grep -Fc "$d07_anchor" "$SPEC")" = "1" ]; then
    printf 'PASS  D-07s %s dedicated block located\n' "$d07_key"
  else
    printf 'FAIL  D-07s %s dedicated block missing or ambiguous\n' "$d07_key"; FAILED=$((FAILED+1))
  fi
done

d07_tp=$(d07_block TP); d07_qc=$(d07_block QC); d07_ri=$(d07_block RI)

for tp_elem in 'FactSet Profile' 'operator 集合' 'AST schema 版本'; do
  if d07_f "$d07_tp" "$tp_elem"; then
    printf 'PASS  D-07s TechniqueProfilePack element: %s\n' "$tp_elem"
  else
    printf 'FAIL  D-07s TechniqueProfilePack missing element: %s\n' "$tp_elem"; FAILED=$((FAILED+1))
  fi
done

if d07_f "$d07_tp" '事实字段与枚举' && d07_f "$d07_tp" '闭集枚举' \
  && ! d07_e "$d07_tp" '客户端自由猜测|不列.*事实字段|由客户端.*猜|无需列出.*枚举'; then
  printf 'PASS  D-07s TechniqueProfilePack mandates fact fields and closed enum values\n'
else
  printf 'FAIL  D-07s TechniqueProfilePack fact fields / closed enums missing or negated\n'; FAILED=$((FAILED+1))
fi

if d07_e "$d07_tp" '禁止.*(可执行|模型生成).*Python'; then
  printf 'PASS  D-07s TechniqueProfilePack forbids executable or model-generated Python\n'
else
  printf 'FAIL  D-07s TechniqueProfilePack Python ban missing\n'; FAILED=$((FAILED+1))
fi

for query_iface in 'getEntry' 'getSourceSpan' 'searchKnowledge' 'matchFacts'; do
  if d07_f "$d07_qc" "$query_iface"; then
    printf 'PASS  D-07s QueryContractPack interface: %s\n' "$query_iface"
  else
    printf 'FAIL  D-07s QueryContractPack missing interface: %s\n' "$query_iface"; FAILED=$((FAILED+1))
  fi
done

if d07_f "$d07_qc" '向后兼容'; then
  printf 'PASS  D-07s QueryContractPack declares backward compatibility\n'
else
  printf 'FAIL  D-07s QueryContractPack missing backward compatibility\n'; FAILED=$((FAILED+1))
fi

if d07_f "$d07_ri" '每条规则' && d07_f "$d07_ri" '显式声明' \
  && d07_f "$d07_ri" 'profile_version' && d07_f "$d07_ri" 'AST schema 版本'; then
  printf 'PASS  D-07s RuleIndexPack binds every rule to profile_version and AST schema version\n'
else
  printf 'FAIL  D-07s RuleIndexPack per-rule profile_version / AST schema version missing\n'; FAILED=$((FAILED+1))
fi

if d07_f "$d07_ri" '结构化 AST/YAML/JSON'; then
  printf 'PASS  D-07s RuleIndexPack keeps rules declarative AST/YAML/JSON\n'
else
  printf 'FAIL  D-07s RuleIndexPack rules not declarative AST/YAML/JSON\n'; FAILED=$((FAILED+1))
fi

if printf '%s\n' "$sec13" | grep -Fq 'FactSet' \
  && printf '%s\n' "$sec13" | grep -Fq '可执行性' \
  && printf '%s\n' "$sec13" | grep -Fq 'G6' \
  && printf '%s\n' "$sec13" | grep -Fq '不负责生产'; then
  printf 'PASS  D-07s M5 verifies FactSet executability under G6 and produces no contract\n'
else
  printf 'FAIL  D-07s M5 FactSet executability or non-producer boundary missing\n'; FAILED=$((FAILED+1))
fi

sec16=$(sed -n '/^## 16[. ]/,/^## 17[. ]/p' "$SPEC")
if printf '%s\n' "$sec16" | grep -Fq 'TechniqueProfilePack' \
  && printf '%s\n' "$sec16" | grep -Fq 'QueryContractPack'; then
  printf 'PASS  D-07s PublicationPackage lists TechniqueProfilePack and QueryContractPack\n'
else
  printf 'FAIL  D-07s PublicationPackage missing TechniqueProfilePack or QueryContractPack\n'; FAILED=$((FAILED+1))
fi
```

## 2. Red baseline（加固前，证明假绿）

加固前，三个变异全部返回 0（说明门禁无法识别缺陷）：

```text
d07-1   exit=0   D-07 删除 TechniqueProfilePack 的「事实字段与枚举」整条
d07-2   exit=0   D-07 将「事实字段与枚举」改成否定语义（客户端自由猜测）
d07-3   exit=0   D-07 删除 RuleIndexPack 的「每条规则显式声明 Profile 版本及 AST schema 版本」整条
```

## 3. Green checks（加固后，正常规格）

```text
PASS  D-07s TP dedicated block located
PASS  D-07s QC dedicated block located
PASS  D-07s RI dedicated block located
PASS  D-07s TechniqueProfilePack element: FactSet Profile
PASS  D-07s TechniqueProfilePack element: operator 集合
PASS  D-07s TechniqueProfilePack element: AST schema 版本
PASS  D-07s TechniqueProfilePack mandates fact fields and closed enum values
PASS  D-07s TechniqueProfilePack forbids executable or model-generated Python
PASS  D-07s QueryContractPack interface: getEntry
PASS  D-07s QueryContractPack interface: getSourceSpan
PASS  D-07s QueryContractPack interface: searchKnowledge
PASS  D-07s QueryContractPack interface: matchFacts
PASS  D-07s QueryContractPack declares backward compatibility
PASS  D-07s RuleIndexPack binds every rule to profile_version and AST schema version
PASS  D-07s RuleIndexPack keeps rules declarative AST/YAML/JSON
PASS  D-07s M5 verifies FactSet executability under G6 and produces no contract
PASS  D-07s PublicationPackage lists TechniqueProfilePack and QueryContractPack
FAIL 合计: 0
```

## 4. 负向变异（加固后）

每次变异从未修改的权威规格重新复制到 `/tmp/g3-r2-<case>.md`，只修改该副本，单独运行 `SPEC=/tmp/g3-r2-<case>.md bash docs/blackbox-spec-rework/verify-T.sh`。

| 变异 | 内容 | 加固前退出码 | 加固后退出码 | 触发的断言 |
|---|---|---|---|---|
| d07-1 | 删除「事实字段与枚举」整条 | 0（假绿） | 1 | `TechniqueProfilePack fact fields / closed enums missing or negated` |
| d07-2 | 改成「包中不列任何事实字段与枚举；字段由客户端自由猜测」 | 0（假绿） | 1 | 同上（否定语义被拒） |
| d07-3 | 删除 RuleIndexPack 的逐规则版本声明整条 | 0（假绿） | 1 | `RuleIndexPack per-rule profile_version / AST schema version missing` |

每次变异只触发 1 条 FAIL，无连带误报。`d07-3` 同时证明跨块代偿已被阻断：`ReleaseManifest` 中「Schema/Profile 版本」文字保留不动，门禁仍非零退出。

## 5. 恢复验证

恢复权威规格后重新运行门禁，退出码为 0、`FAIL 合计: 0`；`git diff --check` 退出 0。
