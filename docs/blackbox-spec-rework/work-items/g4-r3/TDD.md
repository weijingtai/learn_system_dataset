# TDD：G4 第三批（先红后绿）

`export LC_ALL=en_US.UTF-8`；`S=openspec/learn-system-blackbox-architecture.md`；`BASE=$(git rev-parse HEAD)`（开工前记下）。

## 0. 开工基线

```bash
git status --short PLAN.md pipeline/TODO.md pattern_knowledge_workbench/TODO.md LEARN_SYSTEM_TARGET.md $S   # 空
grep -c '^- \[ \]' PLAN.md                                                     # 63
grep -Fxc '## G6 注解社区线（C/S 会话；与 Dataset 会话的 G3 线并行、互不暂存）' PLAN.md   # 1
grep -c 'KnowledgeReleaseCompiler' pipeline/TODO.md pattern_knowledge_workbench/TODO.md LEARN_SYSTEM_TARGET.md   # 各 1
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                           # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1     # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo "schemas exit=$?"             # 0
```

## 1. r3-01 Red → Green

| 判据 | Red | Green |
|---|---|---|
| `grep -c '^## 黑箱差距 → PLAN 条目 → owner 映射' PLAN.md` | 0 | 1 |
| `git diff $BASE -- PLAN.md \| grep -E '^-[^-]' \| wc -l` | 0 | 0（零删行） |
| `git diff $BASE --numstat -- PLAN.md \| cut -f2` | — | 0 |
| `grep -c '^- \[ \]' PLAN.md` | 63 | 66 |
| `bash docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py`（见下） | 不存在 | `D16 OK`，exit 0 |
| `grep -c '唯一登记处' pipeline/TODO.md pattern_knowledge_workbench/TODO.md LEARN_SYSTEM_TARGET.md` | 0 0 0 | 1 1 1 |
| `grep -c '^- \[ \]' pipeline/TODO.md pattern_knowledge_workbench/TODO.md` | 15 23 | 15 23 |
| 新节位置：`awk '/^## G4 黑箱 D 类规格/{a=NR} /^## 黑箱差距 → PLAN/{b=NR} /^## G6 注解社区线/{c=NR} END{print (a<b && b<c)?"ORDER_OK":"ORDER_BAD"}' PLAN.md` | ORDER_BAD | ORDER_OK |

`check_d16.py`（执行 Agent 按 ACT `checker` 原样写入 `docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py`，属于交付物）做四件事：① 从 `$S` §19 主表提取 19 个首列名，逐一在 PLAN 新节表 A 第一列找到恰 1 次，且第四列 owner 路径存在；② 从表 B 每行取「」内开头文字，`- [ ] <开头>` 在 PLAN.md 恰匹配 1 行，标注列 ∈ 三值；③ PLAN.md 所有未被 ② 匹配的 `- [ ]` 行，要么是新节内的 3 条新增，要么位于 G6/注解社区各节（节名闭集见 ACT）；④ 表 B 行数 = 43。任一失败打印 `D16 FAIL <原因>` exit 1。

## 2. r3-02 Red → Green

| 判据 | Red | Green |
|---|---|---|
| `grep -c 'pat_<technique>_<6位数字>' $S` | 0 | 1 |
| `grep -c 'ent_<32hex>' $S` | 0 | 1 |
| `sed -n '/^#### 3b\. /,/^#### 4\. /p' $S \| grep -c '^|'` | 5 | 7 |
| `sed -n '/^#### 3b\. /,/^#### 4\. /p' $S \| grep -c '用户 2026-09-11 确认'` | 0 | 1 |
| `grep -Fc '\| ConflictGroup（冲突组） \| \`cg_<32hex>\` \|' $S` | 1 | 1（原三行不变） |

## 3. 回归（每个 ACT 后）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                              # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1        # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo "schemas exit=$?"                # 0
git diff --check
git status --short | grep -v '^??' | grep -vE 'PLAN.md|pipeline/TODO.md|pattern_knowledge_workbench/TODO.md|LEARN_SYSTEM_TARGET.md|learn-system-blackbox-architecture.md|work-items/g4-r3/check_d16.py'   # 空
```
