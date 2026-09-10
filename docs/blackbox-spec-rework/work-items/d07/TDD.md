# D-07 TDD 机器与语义判据

## 1. 自动判据设计

在 `docs/blackbox-spec-rework/verify-T.sh` 中新增 D-07 语义门禁：

```bash
# D-07 语义门禁
d07_sec16=$(sed -n '/^## 16[. ]/,/^## 17[. ]/p' "$SPEC")
d07_sec13=$(sed -n '/^## 13[. ]/,/^## 14[. ]/p' "$SPEC")

# 1. 两个子包在 §16 出现
if printf '%s\n' "$d07_sec16" | grep -Fq 'TechniqueProfilePack' \
  && printf '%s\n' "$d07_sec16" | grep -Fq 'QueryContractPack'; then
  printf 'PASS  D-07s PublicationPackage contains TechniqueProfilePack and QueryContractPack\n'
else
  printf 'FAIL  D-07s PublicationPackage missing TechniqueProfilePack or QueryContractPack\n'; FAILED=$((FAILED+1))
fi

# 2. 四查询接口齐备
for query_iface in 'getEntry' 'getSourceSpan' 'searchKnowledge' 'matchFacts'; do
  if printf '%s\n' "$d07_sec16" | grep -Fq "$query_iface"; then
    printf 'PASS  D-07s QueryContractPack interface: %s\n' "$query_iface"
  else
    printf 'FAIL  D-07s QueryContractPack missing interface: %s\n' "$query_iface"; FAILED=$((FAILED+1))
  fi
done

# 3. TechniqueProfilePack 核心要素齐备
for tp_elem in 'FactSet Profile' 'operator 集合' 'AST schema 版本' 'Profile 版本'; do
  if printf '%s\n' "$d07_sec16" | grep -Fq "$tp_elem"; then
    printf 'PASS  D-07s TechniqueProfile element: %s\n' "$tp_elem"
  else
    printf 'FAIL  D-07s TechniqueProfile missing element: %s\n' "$tp_elem"; FAILED=$((FAILED+1))
  fi
done

# 4. 规则纯声明式 AST，禁止可执行 Python 规则
if printf '%s\n' "$SPEC" | grep -Eq '禁止.*(可执行|模型生成).*Python' \
  && printf '%s\n' "$SPEC" | grep -Fq '结构化 AST/YAML/JSON'; then
  printf 'PASS  D-07s rules require declarative AST and forbid executable Python\n'
else
  printf 'FAIL  D-07s rules declarative AST or Python ban missing\n'; FAILED=$((FAILED+1))
fi

# 5. §13 M5 针对 FactSet 可执行性校验（引 G6）
if printf '%s\n' "$d07_sec13" | grep -Fq 'FactSet' \
  && printf '%s\n' "$d07_sec13" | grep -Fq '可执行性' \
  && printf '%s\n' "$d07_sec13" | grep -Fq 'G6'; then
  printf 'PASS  D-07s M5 verifies FactSet rule executability under G6\n'
else
  printf 'FAIL  D-07s M5 missing FactSet rule executability under G6\n'; FAILED=$((FAILED+1))
fi
```

## 2. 先红后绿执行流程

1. **Red 阶段**：
   - 将上述判据写入 `docs/blackbox-spec-rework/verify-T.sh`；
   - 运行 `bash docs/blackbox-spec-rework/verify-T.sh`；
   - 预期输出：D-07 门禁报 FAIL，FAILED 计数增加（至少 5+ 处 FAIL），证明新门禁对旧规格有效拦截。

2. **Green 阶段**：
   - 修改 `openspec/learn-system-blackbox-architecture.md`：
     - §13 强化 M5 G6 校验及规则 AST/禁止 Python 规则说明；
     - §16 目录树新增 `TechniqueProfilePack` 与 `QueryContractPack`；
     - §16 新增详细段落阐述两子包规范、四接口、AST schema 版本、Profile 版本与兼容性；
   - 运行 `bash docs/blackbox-spec-rework/verify-T.sh`；
   - 预期输出：全部 PASS，FAILED 计数为 0。

3. **负向变异阶段（Mutation Testing）**：
   - 变异 A：删除 `matchFacts`，重新运行门禁，必须 FAIL；
   - 变异 B：删除 `TechniqueProfilePack`，重新运行门禁，必须 FAIL；
   - 变异 C：删除 `Profile 版本`，重新运行门禁，必须 FAIL；
   - 变异 D：删除 `AST schema 版本`，重新运行门禁，必须 FAIL；
   - 恢复所有变异，重新验证 0 FAIL。
