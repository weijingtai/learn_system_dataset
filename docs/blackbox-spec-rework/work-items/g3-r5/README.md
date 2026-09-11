# G3 R5：封闭三类区域边界假绿

状态：`READY`（主 Agent 2026-09-10 完成六件套与 ACT 自审）
task_id：`blackbox-g3-r5-region-boundaries`
权威需求来源：根 `PROJECT_COLD_START_HANDOFF.md` §5–§7、`HANDOFF.md` 顶部「项目冷启动总交接」
基线提交：`ffe19df`（两个授权脚本自该提交后未再改动；`git diff ffe19df HEAD -- <两脚本>` 为空）
分支：`codex/docs/knowledge-compilation`

## Goal

在不改规格正文、不扩展否定词黑名单的前提下，让 `verify-T.sh` 对以下三类结构性绕过一律非零退出并命中指定 FAIL ID；同时把这三类绕过固化为 `mutations.sh` 的永久变异用例。

| 编号 | 绕过方式（当前 exit 0） | 必须命中的 FAIL ID |
|---|---|---|
| R5-1 | D-07 三个封闭块之后、下一 START（或 `### 16.2`）之前，隔空行追加冲突 bullet 或冲突段落 | `G3-D07-TP` / `G3-D07-QC` / `G3-D07-RI`（按所在区域） |
| R5-2 | §16.2 映射表正确数据行行尾追加第三列 ` 冲突附加值 \|` | `G3-T07-MAP` |
| R5-3 | §16.3.1 内在 B3 正确块之后、`#### 16.3.2` 之前再插入同名 B3 标题；或在 B1 块后重复 B1 标题；或在块外追加正文 | `G3-T08-BLOCK` |

## 主 Agent 已复现的 Red 基线（HEAD = c9b3d6e，脚本等同 ffe19df）

`LC_ALL=en_US.UTF-8` 下，对四个独立临时副本运行门禁：

```text
r5-1a（TP 块后空行 + 冲突 bullet）      exit=0  无 FAIL 行
r5-1b（TP 块后空行 + 冲突段落）         exit=0  无 FAIL 行
r5-2 （release-manifest 行尾追加第三列） exit=0  无 FAIL 行
r5-3 （B3 块后重复 B3 标题）            exit=0  无 FAIL 行
```

正常规格：`FAIL 合计: 0`；selftest `37/37`；固定矩阵 `98/98 rejected`。

## Scope

- 允许写：`docs/blackbox-spec-rework/verify-T.sh`、`docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh`
- 允许读：`AGENTS.md`、本目录六件套、`openspec/learn-system-blackbox-architecture.md`（只读，作为待测对象）。expected 常量只来自两个脚本内已提交的 `C_*` 与 `TDD.md` §1.1；g3-r3 目录下未提交草稿不是常量来源
- 其余一切路径禁止写入；`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、本目录文档由主 Agent 在验收后更新

## Forbidden

1. 修改规格正文、其他工作包、验收文档、协调文档。
2. 增加任何自然语言否定词/关键词黑名单；只允许「区域封闭 + 完整行逐字规范化相等」。
3. 从 `$SPEC`（待测副本）推导 expected；expected 只能是脚本内硬编码常量。
4. 用 `sort -u` 抹掉重复；用 `[[:space:]]` 做冻结规范化（规范化只删 5 种字节：反引号、星号、空格、Tab、CR）。
5. 放宽既有断言、缩减既有 98 例、固定返回码、跳过变异未生效的用例。
6. `git add -A`、`git add .`、任何批量暂存；只允许显式 `git add` 两个授权脚本。
7. `reset`、`clean`、`stash`、切分支、rebase、push、合并。
8. 自行宣布 G3 通过或启动 G4。

## Inputs

- 规格 §16 当前结构（行号以 HEAD 为准）：TP START 行 686、QC START 行 693、RI START 行 701、`### 16.2` 行 706、表格 712–728、`#### 16.3.1` 行 734、B1/B2/B3 标题 736/740/743、`#### 16.3.2` 行 747。
- 权威常量：`verify-T.sh` 与 `mutations.sh` 现有 `C_*` 常量；§16.2 的 15 行 `C_T07_M01..M15` 目前只在 `mutations.sh` 中，本任务须原样复制进 `verify-T.sh`。

## Dependencies

- 无外部依赖；bash + POSIX 工具（awk/sed/grep/tr/mktemp）。
- 本机 `locale` 默认 `LC_CTYPE=C`，会让与本任务无关的 `T-06s` 误报；所有验证命令前 `export LC_ALL=en_US.UTF-8`。

## Stop Conditions

- 两个授权脚本在开工时相对 `ffe19df` 有任何差异；
- 任一 Anchor 命中次数不为 1；
- 修复后任一既有 98 例变为 not-rejected；
- 正常规格出现 `G3-*` FAIL；
- 需要修改允许范围之外的文件才能通过。

遇到以上任一情况：停止，不扩大范围，按 ACT `on_fail` 报告。

## 执行顺序

`act/01.yaml`（先红：新增 11 例 + 2 个原语 + selftest，提交）→ `act/02.yaml`（后绿：封闭三类区域，提交）。

## 决定记录

**2026-09-10 转译审查 R1：返工 4 项**（审查者 = 原规划者，实跑核对）

- ACT01: 草案 t08-45（B3 承接说明后追加正文）与 t08-47（B2 后空行 + 正文）在 HEAD 已被 `G3-T08-BLOCK` 拒绝，不是 Red，「not-rejected 恰 5」断言必然失败 ｜ 修正标准：改为 t08-45 = §16.3.1 标题后插正文、t08-47 = B2 块尾重复 B2 标题；两例实跑 exit 0。
- ACT02: TDD §2.1 FAIL 文案「…或直接打印区域行数」存在二选一 ｜ 修正标准：唯一写法，数字由 `g3_nlines` 实算。
- ACT02: 「删除或停用旧逻辑」存在二选一 ｜ 修正标准：明确删除 `g3_d07_items`。
- ACT.yaml: scope.read 引用未提交的 `g3-r3/CANONICAL.md` 作常量来源，与「不得派发过时草稿」冲突 ｜ 修正标准：常量来源改为两脚本已提交 `C_*` 与 TDD §1.1。

**2026-09-10 转译审查 R2：READY，2 个 ACT 可开工**。四查：忠实性（两 ACT 分别对应冷启动交接 §6 第 1–2 项与第 3–5 项，验收标准区未改动）；覆盖性（BDD 2.1–2.4、3.1–3.2、4.1–4.3 各有一例，失败路径由 `MUTATION_NOT_APPLIED`、selftest 与 98 例回归覆盖）；可执行性（路径 `ls` 核对存在，命令仅 bash/grep/git，无第三方依赖，模糊词扫描为零，两 ACT 各 45/60 分钟）；独立性（act/02 声明 `depends_on` act/01，两 ACT 写不同文件）。
