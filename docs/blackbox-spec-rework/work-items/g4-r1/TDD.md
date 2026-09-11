# TDD：G4 第一批（先红后绿）

全部命令在 worktree 根目录执行，先 `export LC_ALL=en_US.UTF-8`。`S=openspec/learn-system-blackbox-architecture.md`。

## 0. 开工基线（每组都要跑，任一不符即停手）

```bash
git merge-base --is-ancestor e64f2a4 HEAD && echo ANCESTOR_OK
git status --short                                                    # 期望空
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                  # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1   # MUTATIONS: 109/109 rejected
bash openspec/schemas/verify.sh >/dev/null; echo "schemas exit=$?"    # 0
```

## 1. 每个 ACT 的 Red（改动前必须为下列值）与 Green（改动后必须为下列值）

| ACT | 判据命令 | Red（改动前） | Green（改动后） |
|---|---|---|---|
| d13 | `sed -n '/^### 6\.2 /,/^## 7\./p' $S \| grep -c 'Review Console（M7 模式）\|M7 回流'` | 0 | 3（块内 2 行 + 块后归属段首句） |
| d13 | `sed -n '/^### 6\.2 /,/^## 7\./p' $S \| grep -c '不改变任何已封存'` | 0 | 1 |
| d10 | `grep -c '^### 14\.1 精确失效传播' $S` | 0 | 1 |
| d10 | `grep -c 'carried_forward\|ReworkImpactReport' $S` | 0 | ≥ 4 |
| d10 | `grep -c '之后只让血缘可达的派生物失效' $S` | 1 | 0 |
| d10 | `grep -c 'M3 至 M6 全部失效' $S` | 0 | 0 |
| d11 | `grep -c '^### 17\.1 StageCheckpoint' $S` | 0 | 1 |
| d11 | `grep -c 'StageCheckpoint' $S` | 1 | ≥ 6 |
| d06 | `grep -c '^├── AnchorContractPack$' $S` | 0 | 1 |
| d06 | `grep -c 'AnchorContractPack\|IdentityMigrationMap' $S` | 1 | ≥ 8 |
| d06 | `sed -n '/^## 20\./,/^## 21\./p' $S \| grep -c '^11\. '` | 0 | 1 |
| d06 | `grep -c '锚点迁移关系' $S` | 0 | ≥ 2 |
| d08 | `grep -c '^- Interpretation、SchoolView、Alias；$' $S` | 0 | 1 |
| d08 | `grep -c 'SchoolView\|changes_current_judgment' $S` | 2 | ≥ 5（新增：列表行、定义段、SchoolViewPack 段、§18 行） |
| d08 | `grep -c 'SchoolViewPack' $S` | 0 | ≥ 1 |
| d08 | `grep -c '^├── SchoolViewPack$' $S` | 0 | 0（不新增顶层子包） |
| d08 | `grep -c '待用户确认' $S` | 记录 | 比 Red 多 1 |
| d14 | `awk '/^## 19\./,/^### 19\.0 /' $S \| grep -c '^| .* | .* | .* | .* | \(首纵切内\|首纵切后\|本阶段暂缓\) |$'` | 0 | 19 |
| d14 | `awk '/^## 19\./,/^### 19\.0 /' $S \| grep -c '| 首纵切内 |$'` | 0 | 4 |
| d14 | `grep -c '^## 22\. 实施分期与首个纵切$' $S` | 0 | 1 |
| d14 | `awk '/^## 22\./{f=1;next} f && NF {print; exit}' $S` | （空） | `状态：讨论候选` |
| d14 | `grep -c '§22' LEARN_SYSTEM_TARGET.md` | 0 | 1 |

## 2. 回归（每个 ACT 完成后、提交前）

```bash
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                              # FAIL 合计: 0
bash docs/blackbox-spec-rework/verify-T.sh | grep -c '^PASS  G3-'                  # 12
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1        # MUTATIONS: 109/109 rejected
bash openspec/schemas/verify.sh >/dev/null; echo "schemas exit=$?"                # 0
git diff --check                                                                    # 无输出
```

T-13 结构门禁提醒：§3–§18 每节标题后的第一个非空行必须仍是原 `状态：` 行；新增 `###` 小节放在该节 `状态：` 行之后的任意位置均可，但不得插在标题与 `状态：` 之间。

## 3. 主 Agent 语义验收（机器判据只是必要条件）

对每条新增文本逐句核对 `act/<id>.yaml` 的 `text` 字段是否逐字落实；核对未改动 ACT 范围外任何行（`git diff` 只含 ACT 指定的插入/替换）。
