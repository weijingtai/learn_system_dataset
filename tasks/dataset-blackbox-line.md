# 任务纪要 — Dataset 黑箱线（codex/docs/knowledge-compilation）

> 同分支另有一条工作线 `ocr/ 单字切分识别质量修复`，纪要在 `tasks/codex-docs-knowledge-compilation.md`，**两条互不覆盖**。
> 本线范围：`docs/blackbox-spec-rework/**`、`pipeline/**`、`openspec/**`
> 更新时间：2026-09-16

---

## 目标

按 W7「文本源优先」路线打通 M1→M8：以电子文本（TXT/MD）替代图像 OCR 作为第一版来源，
证据级别 `offset_level`，发布级别只做 `INTERNAL_DEMO`/`DEV_SEARCH`（裁定 76）。

计划见 `docs/blackbox-spec-rework/G7-PLAN.md` §4/§5；裁决见 `G7-RULINGS.md`；
逐包清单见 `SUBAGENT_TODO.md` §G7。

---

## 当前状态（2026-09-17）

刚完成：用户 24 条 M4 分歧裁决已导入持久 Ledger（24 human_event + 24 Checkpoint），M4 `srun_bafd7499…` 封存 `succeeded`（26 assertion / 2 pattern / 10 新概念候选 / 2 条 a 路被 G4 拒收，状态全 `disputed`）；同 Ledger M5 `INTERNAL_DEMO` 通过（warnings 39、failures 0）。M8 ACT 08/09/10 已验收。

半成品：M6 R84 `4e16022`+R84b `cb96b94` **已提交未验收**，review 套件现有既有用例红——需按裁定 108 改 `pipeline/review/testing/data/m4_candidates.yaml` 中 `as_qizheng_000002` 偏移 13→9、15→11（`quote`/`quote_sha256` 不变），派单已写好：`~/tmux-agents/runs/prompts/agy-84b.txt`。M8 K2 派单 `agy-86d.txt` 未开工。

下一步：① 派 agy 执行 R84c → 主 Agent 验收 8.4；② 在 `var/ledgers/qianyuan_w8/` 跑 M6 到 `awaiting_human`，生成 M6 审核表交用户；③ 并行派 M8 K2（ACT 11 知识链+`ent_` 发号表、ACT 12 Gate）。

微观意图：M6 审核表要显式写两条——26 条 assertion 无 `concept_refs`（不推断，裁定 107 Q-M8-01），要出 Concept 词条须用户 `modify` 补显式引用；2 条 a 路 assertion 已被 M4 G4 拒收。8.5 派发时顺手把 `genesis_package.json` 里「标 offset_level 却用页码形态 ID」的自相矛盾一并修掉（裁定 106 D4）。8.7 时才动 `run_all.sh`（P4 独占）。

真书 Ledger：`var/ledgers/qianyuan_w8/`（不入库；备份 `qianyuan_w8.bak_before_m4_rulings`）。**执行器 2026-09-17 全部不可用**：`agy` CLI 已失效（`~/.local/bin/agy` → `/Volumes/256/.../Antigravity.app/Contents/Resources/app/bin/antigravity` 不存在，盘上只剩 `Antigravity IDE.app`，是 IDE 启动器不是 agent CLI）；`cmd` 周限额至 2026-09-19 12:13；`opencode/union-alpha` 常卡死（见墓地）。本机尚有 `mimo` v0.1.1（`~/.mimocode/bin/mimo`，未实测写代码）。

验证方法：
```bash
cd /Users/jingtaiwei/Git/Public/learn_system && export LC_ALL=en_US.UTF-8
for p in ledger intake digitization corpus_compiler corpus_compiler/semantic knowledge_extraction validation review assembly dataset_compiler; do \
  printf "%-26s " $p; .venv/bin/python -m unittest discover -s pipeline/$p/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)" | tr '\n' ' '; echo; done
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py | tail -1   # pass=44 fail=0
bash openspec/acceptance/run_all.sh | tail -1                                                  # pass=2 fail=1 blocked=8
```
注：干净树（`git archive`）跑 orchestrator/contract_registry 会各有 5/1 条红，因页图不入库，属环境非回归。

## 交接须知（给接手 Agent，2026-09-17）

读取顺序：本纪要 → `docs/blackbox-spec-rework/G7-RULINGS.md` 表格第 **95–108** 行（W8 全部裁决）→ `G7-PLAN.md` §6（W8 分波表）→ 对应工作包 `README/TDD/ACCEPTANCE`。**不要先读源码**。

角色纪律（沿用 P1–P9 与裁定 93/97）：主 Agent 写计划/工作包/裁决、做独立验收（`git archive <hash>` 干净树 + 自设篡改），**不写实现代码**；执行器遇未知或需删改已验收判据必须写「## 待裁决」停手；回报未亲自跑过的一律写「未跑」；人工决定（M4 分歧裁决、M6 审核、`expert_verified` 签发）**只能由用户填**，Agent 不得代填（P7）。

现成资产（都在盘上，别重做）：
- 未执行派单：`~/tmux-agents/runs/prompts/agy-84b.txt`（M6 夹具更正 R84c）、`agy-86d.txt`（M8 K2 = ACT 11 知识链+`ent_` 发号表、ACT 12 Gate）。把里面的执行器与回报路径换成新执行器即可，内容不必重写。
- 历史回报：`~/tmux-agents/runs/{agy-84,agy-86a,agy-86b,agy-86c,cmd-81,cmd-82,cmd-83,cmd-j4b,cmd-fx,oc-w8}.report.md`；M4 分歧原始导出 `cmd-82-disputes.yaml`。
- 用户已填并已导入的裁决表：`var/ledgers/qianyuan_w8_review/m4_rulings_filled.yaml`。
- 独立金标与仲裁材料已入库：`pipeline/corpus/_fixture/qianyuan_ed01_text/expected/`（**任何情况下不得修改**，第 95/101 条）。

未验收/未完成边界（接手第一件事是确认这三条）：
1. M6 的 `4e16022`、`cb96b94` **已提交但未验收**，且 `pipeline/review/tests` 有既有用例红——先做第 108 条夹具更正再验收，别在红基线上继续加功能。
2. `pipeline/corpus/_fixture/qianyuan_ed01_text/m4/` 已入库，但 M6 之后若改动上游契约，需回看该宿主是否仍成立。
3. `var/` 永不入库；持久 Ledger 的写操作前先整目录备份。

## 用户待办

- [ ] **M6 审核表**（W8 8.4 之后由主 Agent 生成）：用户逐条 接受/修改/驳回；不得由 Agent 代填（P7）。
- [ ] **签发决定表**：真实 `expert_verified` 由用户本人签发（第 80 条），不阻断 W8 的 `INTERNAL_DEMO`，阻断 `PUBLIC_RELEASE` 与 M6 `upstream_real` 判定。
- [x] 验收宿主原文：《乾元秘旨》全文已入库（J4b `1406048`）。
- [x] M4 分歧裁决：24 组已由用户填写并导入（2026-09-16）。

## 计划区（W7）

- [x] 7.0 M6→M7 真实上游接线（impl-07 g0-06 `0ef4105`、impl-06 act/12 `dc83cf9`；裁定 83/84/87）
- [x] 7.1 impl-00 act/14 电子文本闭集登记（`ec8c3a8`，36 PASS）
- [x] 7.2 impl-09 M1+M2 电子文本（阶段 A + J1–J4 + J1a/J1b/J3a/J3b/J3c，全部 `ACCEPTED`）
- [x] 7.3 impl-10 M3 偏移锚点 + 语义层
  - [x] 阶段 A 起草（`fcf9458`→`3359e4b`）
  - [x] L1 偏移锚点与切分（`0d50d29`、`1eab4be`）
  - [x] L2 输入解析/事务 + Gate/组装（`e5b07ed`、`6ec07c5`）
  - [x] L3 语义层（`13ddfd1`、`e42c482`、`2d7b613`、`61070ad`）
  - [x] **L4 `m3-coverage.sh` 电子文本宿主支持（act/07，阈值 ≥148）**
- [ ] 7.4 签发决定表模板 → 用户填写 → M4/M6 真实签发导入
- [ ] 7.5 impl-04 跟进：M8 知识链前三段 + GraphProjectionPack（并入 W8 8.6）

## 计划区（W8：真书走到 M8；细表见 `G7-PLAN.md` §6，裁决 100–108）

- [x] 8.0 J3f（`87ce16c`）+ J4b（`1406048`）：M1/M2 验收改为对原文实跑比对，宿主入库
- [x] 8.1 `ids.py` 偏移形态（`7bdaa9c`）+ 电子文本 M3 补阶段产物（`08e3bba`）
- [x] 8.2 M4 offset 支持（`71c913f`）+ 真书宿主与两路提交件（`7838d59`）+ 用户 24 条裁决导入、M4 封存
- [x] 8.3 M5 offset 档 G1/G2/G3（`2537b75`）+ PUA 对账（`82f7148`）+ 登记表更正（`2db0fcc`）
- [ ] 8.4 M6：R84 `4e16022`、R84b `cb96b94` 已提交未验收；缺 R84c 夹具更正（裁定 108）→ 跑 M6 出审核表
- [ ] 8.5 M7 Snapshot 补 `evidence_level`/`corpus_spans_revision_id`（裁定 106 D4）
- [ ] 8.6 M8：ACT 08 `ff21388`、ACT 09 `fc31716`、ACT 10 `ce3ddab` 已验收；K2（ACT 11/12）未开工；ACT 13/14 待 8.5
- [ ] 8.7 验收脚本电子文本路线 + orchestrator 登记 m4/m6 + `run_all.sh` 按判定输出

---

## 决定记录

**2026-09-15 裁定 85/86（impl-09 形态唯一权威）**
同一契约的形态说明只允许有一处权威出处，其余位置一律引用而非复述。
起因：`source_manifest` 形态在包内有三处互相矛盾的写法。权威出处 = `impl-09 README §3`。

**2026-09-15 裁定 87（判定可见优先于数字好看）**
act/12 的 `pass=12` 是我起草时的算术疏漏。执行方提出「把 `first_review_counts` 折进别的检查以保住 12」，
不采纳——为迁就写死的数字而把真实判定藏起来，与裁定 84 否掉的 C 案是同一种失败模式。
改为 `pass=13`。据裁定 54，不变量是 `fail=0` 而非固定 pass 总数。

**2026-09-15 裁定 88（护栏须对所有等价写法成立）**
`test_dump_does_not_touch_global_safedumper` 在运行期取全局注册表前后快照，
而污染发生在 **import 期**，因而恒绿。护栏必须能检出 import 期副作用。

**2026-09-16 裁定 90/91/92（清单类交付物的验收口径，代价最大的一组）**
1. 工作包 `tests` 清单必须覆盖其 contract 声明的**每一项**可判定行为，差集须为空或显式标 `DEFERRED`。
2. 清单/闭集类护栏**不得自带「为触发而造」的样例表充数**；每项须 (正例, 反例) 成对，正例贴近真实输入；
   **执行方自带样例全绿不构成达标证据**，主 Agent 一律另建独立样例集复核。
3. 数据表类交付物**不得只给数量下限**——纯数量阈值直接制造凑数动机（裁定 91 的「≥20 对」
   导致执行方塞入 `戊戌→戊戌` 自映射、`已己→已经` 不成词等假条目）。数量必须与内容自洽判据同时给出。

**2026-09-16 裁定 93（未然语气 = 未验证）**
回报中任何以「将／应当／会」陈述的验证结果一律视为未验证；结论只接受「命令 + 真实输出」成对。
起因：执行方写「注入后某测试**将**转红，证实护栏有效」，主 Agent 照做实测 `Ran 136 OK`——**结论与事实相反**。
配套：凡执行方声称「已验证」的每一项，主 Agent 独立复跑一次，不接受转述。

**2026-09-16 裁定 94 D4（追踪链必须闭合到下载物）**
`source_assets[]` 同时记 `sha256`（磁盘原始文件字节）与 `normalized_sha256`（归一化后即 RawText 的字节）
加 `original_encoding`，两端各自闭合。原先只记归一化哈希，带 BOM／GB18030 的来源回不到「我当初下载的就是这个文件」。

**2026-09-16 取舍：注入式验证一律落在临时副本**
不再允许「改真实源文件 → 验证 → `finally` 还原」的写法：`finally` 挡不住进程被强杀，
本会话已因此毁掉一个实现文件。改用 `tempfile.TemporaryDirectory()`（`61070ad`）。

---

**2026-09-16 裁定 104（M4 分歧必须人工裁决，撤回第 100 条 D4）**
规格 §12:572「未解决语义分歧进入人工队列，不能通过 M4 Gate」——我原先写的「分歧以 `disputed` 进 M6」违规。
同时定抽取协议 v2：证据以整片段为单位（只写 `source_span_id`/`support_type`），否则两路引文边界随意、证据键对不齐。
实测：v1 分歧 35 组 → v2 24 组。

**2026-09-16 裁定 107（M8 设计）**
`ent_` 用 UUIDv4 + 发号表作冻结输入（否决 UUIDv5/哈希派生，规格 §8.1 明文）；边不发 ID，身份为 `(source, relation, target)`（【I-10】不新增前缀）；
证据链保持规格的固定七段，第 6/7 段按证据级别分派；KnowledgeEntry 主体双轨且**不推断**，无主体 assertion 计入 `known_defects`。

**2026-09-17 操作决定（真书链在持久 Ledger 上跑）**
用户裁决导入与 M4/M5 运行由主 Agent 直接执行（只调既有接口、不写实现代码），导入前先整目录备份 Ledger。
M6 不在验收前跑，避免用户依据未验收实现作出审核决定。

## 踩坑墓地

**2026-09-15 别再用：OpenCode Zen 免费档（MiMo / MUSE Spark 1.2）**
两者共用一个免费池，耗尽后显示 `Free usage exceeded ... retrying in ~18h`，会话**不报错只排队**，
**已投递的 prompt 会在额度恢复后自动开跑**。换执行器前必须 `tmux kill-session` 掉旧会话，
否则一天后重复执行同一批指令。（同一坑在 Gemini 侧也踩过一次。）

**2026-09-16 别再用：Nemotron 3.5 Lightning 免费档写代码**
能应答、能读文件，但长任务会崩：单回合跑 21 分钟后输出退化为多语言乱码
（`The testrial, its tâche: publish thenumber--mounted-credridor`、`평생- allies`、`époux 1 (организация`），
且**把正在编辑的文件覆盖成注入的那一行、从不还原**——`gate_offset.py` 原实现因此丢失（未提交，仓库无损）。
结论：不可用于写代码；免费档里目前只有它可用时，宁可等额度也不要派实现类任务。

**2026-09-16 别再信：执行方回报里的「已验证」**
同一晚三个执行器分别出现：① 声称四条 `assemble_*` 用例「OK」而该四条**根本不存在**；
② 声称护栏「将转红」而实测不转红；③ 把完工后计数当「开工基线」、把测试文件内容当「Red 原文」。
结论：主 Agent 必须对每一项声称独立复跑（已立为裁定 93 配套制度）。

**2026-09-16 别再写：`-p 'test_x.py'` 过滤 + 断言累计用例数**
impl-10 起草稿的 verify 命令只跑单个测试文件却断言整套累计（跑 18 条要求 ≥52），
**命令永不可能达标**。且累计从 0 起算、忽略了 `corpus_compiler/tests` 已有的 68 条基线，
还把两个互不包含的测试目录串成一条累计链。
结论（裁定 89）：阈值 = 基线 + 本包新增；每套目录独立累计；verify 必须跑整套、不加 `-p`。

**2026-09-16 别再用：ERR 正则里放中文「额度／限流」**
`oc-watch.sh` 的错误正则含这两个词，而**我自己的派发文里就写着这两个词**并显示在执行器屏幕上，
于是每次派发都立刻误报「撞额度」。已改为只认执行器真实横幅
（`Free usage exceeded`、`Individual quota reached`、`HTTP 429` 等）。

**2026-09-16 已知非缺陷：三份验收脚本 exit 2**
`m1-intake.sh`/`m2-sanitization.sh`（及后续 `m3-coverage.sh`）在电子文本宿主未落地前如实 exit 2（BLOCKED），
是设计意图（P4 独占 fixture ACT 尚未安排）。**不要为了让它变绿而改默认宿主或加兜底分支**——
裁定 94 D2/D3 正是为此而立。

**2026-09-16 别再用：opencode `opencode/union-alpha`（Union Alpha Free）写代码**
供应端反复 `Error from provider (Console): Upstream request failed: Endpoint is unavailable`，会话不退出只原地重试：
两次各卡 1.5–2 小时零产出（一次 Write 工具循环不落盘，一次 8.1 全程零改动、回报只有 `placeholder`）。
小任务（J3f）能完成。判定卡死：token 数 + `git diff --stat` 20 分钟不变 → kill 改派。半成品必须让接手方先审再用。

**2026-09-16 别再让执行方「带红提交」**
8.4 执行方按裁定 106 改严偏移解释后，既有用例因夹具数据错误转红，它**先提交实现再停手请示**，
导致仓库停在红色基线（裁定 108 记违规一次）。结论：待裁决事项导致既有用例红时，保持工作树未提交、只写「## 待裁决」。

**2026-09-16 监控脚本误报两次（`oc-watch.sh`）**
① 完成标题用 `grep -qE "$KEY|## 待裁决"` 匹配全文，回报正文里提到「写「## 待裁决」」即误判完成 → 改为行首 `^` 匹配；
② 限额关键词 `quota|limit` 命中屏幕上的代码文本 → 改为只认 `Error from provider` 横幅。
结论：监控的完成/异常判据必须锚定 agent 自身输出的固定形态，不能是会出现在任务内容里的词。

