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

刚完成：8.4b（用户 26 条 M6 决定导入、M6 `close` 封存 `succeeded`）与 8.6-K2（ACT 11 `496fbb1`、ACT 12 `162250c`）已验收。**投产评估实测**（2026-09-19）：10 个包测试全绿（ledger 84 / intake 38 / digitization 86 / corpus 163 / semantic 57 / knowledge 149 / validation 108 / review 166 / assembly 96 / dataset 162），`check_interfaces.py` `pass=44 fail=0`，`run_all.sh` `pass=2 fail=1 blocked=8`。**结论：不可投产**——阻断项见下。

进行中：**P1 = 8.5** 已派发（ACT `impl-07-assembly/act/11.yaml`，执行器 `agy --model pro`，tmux 会话 `w8-85`，派单 `~/tmux-agents/runs/prompts/agy-85.txt`，回报落点 `~/tmux-agents/runs/agy-85.report.md`）。

下一步：① 验收 P1（8.5）；② P2 = 8.6-K3（ACT 13 改读 M7 Snapshot、ACT 14 电子文本路线）；③ P3 = 8.7（orchestrator 登记 m4/m6、验收脚本电子文本路线、`run_all.sh` 按真实判定输出）。

**投产阻断（三条硬的）**：① M7 完整增量汇编未实现，只做了创世一次 → 加不了第二本书、也做不了第二次修订；② M8 未接 M7 真实 Snapshot（卡在 8.5）；③ 编排层未登记 m4/m6，`run_all.sh` 判定过时（仍报「M4 未实现」），无一键验证手段。
**投产前必改（质量项，均已查实）**：④ M4 brief 每批 20 条上限两路都顶格截断，改自适应 `上限 = 1.2 × 该批片段数`；⑤ 补回被上限截掉的 5 个 concept 词条（正财/偏财/偏印/正印/劫财，b 路 notes 已逐个点名，不必重跑 M4）；⑥ M5 Gate 增一条扫描 `adapter_notes`，命中「控总数/上限/略去/未逐一登记」即置待处理（该字段目前是无下游消费者的死数据）；⑦ 41 片段清单 `spans_tianguan_qisha.yaml` 全盘无此文件（README 只记 sha256），须从提交件重建入库并标注「与原记录 sha256 未能核对」；⑧ `pipeline/corpus_compiler/tests/test_gate_offset.py::test_gate_offset_does_not_import_compiler_modules` 随发现范围变红（自检用的 `GATE_SOURCE_ENV` 泄漏到真实用例），是测试设施缺陷非产品缺陷。

**规模现状**：真书只跑了原文 `[8663, 9397)` 共 734 字 = 全书 17,735 字的 **4.1%**（首纵切设计如此）。现可交付下游的是该切片上 26 条带偏移证据的断言，`INTERNAL_DEMO` 级——**是样品不是产品**。全书外推需 470–729 条候选（估算，单样本外推）。

微观意图：M6 审核表要显式写两条——26 条 assertion 无 `concept_refs`（不推断，裁定 107 Q-M8-01），要出 Concept 词条须用户 `modify` 补显式引用；2 条 a 路 assertion 已被 M4 G4 拒收。8.5 派发时顺手把 `genesis_package.json` 里「标 offset_level 却用页码形态 ID」的自相矛盾一并修掉（裁定 106 D4）。8.7 时才动 `run_all.sh`（P4 独占）。

真书 Ledger：`var/ledgers/qianyuan_w8/`（不入库；备份 `qianyuan_w8.bak_before_m4_rulings`）。

**执行器 2026-09-19 已恢复**：`agy`（`~/.local/bin/agy`，189MB 真实二进制，09-18 换过）与 `cmd`（1.58.0，周限额 12:13 已过）均可用；`opencode`/`freebuff`/`mimo` 的 CLI 也在。注意 `agy --model pro` 实际跑的是 **Claude Sonnet 4.6**，不是 Gemini Pro。
**坑：`~/tmux-agents/bin/tmux-watch.sh` 对新版 agy 失效**——它靠匹配界面文字判忙/闲（`ready_re` 找 `? for shortcuts`），新版界面改成 `Tip: Press shift+tab…`，一挂就误判空闲并立即退出（exit 0），等于没有监控。替代做法：用 `until [ -f <回报文件> ]; do sleep 20; done` 后台等回报文件出现。另：`tmux-agent.sh send` 的消息会**排队到当前回合结束**才被消费，期间执行器可能已按旧理解动手改代码——急事要先 `pause`。

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
- [x] 8.4 M6：R84 `4e16022`、R84b `cb96b94`、R84c `e5c960a`（夹具更正，裁定 108）已验收；`open_review` 已跑至 `awaiting_human`（srun_3009b37a…）并生成审核表模板 `var/ledgers/qianyuan_w8_review/m6_review_decisions_template.yaml`（26 项）
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

---

**2026-09-19 用户决定：Jev 不接入本链（实测后否决）**
实测报告在 `~/Documents/jev-router/eval/learnsystem/`（另一会话产出，136 次请求、$0.0042）。四项结论：
1. **省 token 不成立**：闭集字段只占 LLM 输出 13.4%，全书双路约省 $0.25。**以后不得再以成本为由提接入。**
2. **M4 漏抽体检不过线**：L1 查实的 5 个真实漏抽词条，Jev 召回 **0/5**，概率全在 0.08–0.10（自信地答错）。原因是结构性的——
   Noul 的题面承载不了「该抽的都抽了吗」：那是**拿候选与原文比对找缺口**的比对任务，不是判断题。**别人再提这条，先看这一行。**
3. **分词不过线**：与 M3 结构层一致率 97.4% **是陷阱数**——一个永远答「不该断」的常数函数能拿 100%。真实问题是 267 个候选只有 **2 个**越过 0.8 置信度，阈值分流工程上等于没有。**禁止拿「一致率 97%」立项。**
4. **唯一过线项**：片段可断言性（套语/标题/设问筛子）——可断言 35 条 p=0.79–0.95、不可断言 6 条 p=0.05–0.44，两组不重叠，错分 0/41。但不可断言样本仅 6 条且同书同两节，**未复跑，不足以接入**。
硬约束（将来若重启接入仍适用）：不进 Gate 判定、不产 offset、响应须录成冻结输入、选项顺序固定并进请求指纹。
另有一条通路事实：**verifier（M6 审核排序）被权限分类器判定为跨信任边界的硬阻断，用户授权也解除不了**——因 state 带 M6 派生的命题文本。T5 只发公有领域原文故放行。不得改造数据形态去绕。

**2026-09-19 口径（派活纪律，因本轮踩到而立）**
ACT 文字与代码既有约定冲突时，**以主 Agent 裁定为准，执行方不得反过来改既有约定去凑 ACT 字面**。
起因：ACT 把「缺字段」的错误码误写成 SCH_002，执行器为满足字面把 `evidence_level` 移出 `_CANDIDATE_SET_REQUIRED` 必填集，
削弱了统一的必填校验。已令其撤销。教训对主 Agent 同样成立：ACT 里写错误码前先核实既有约定。

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

