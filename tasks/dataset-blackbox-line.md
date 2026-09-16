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

## 当前状态

刚完成：impl-09 全部 `ACCEPTED`（M1 电子文本入库 + M2 清洗，含追踪链两端闭合）；
impl-10 的 L1/L2/L3 `ACCEPTED`，语义层落地。

半成品位置：无。工作区干净，`git status --short -- pipeline openspec` 为空。

下一步：**impl-10 L4** —— `act/07`：`openspec/acceptance/m3-coverage.sh` 支持电子文本宿主，
写范围 `pipeline/corpus_compiler/acceptance.py`、`tests/test_acceptance.py`、`m3-coverage.sh`，
corpus 套阈值 **≥148**（139 + 12，见 `impl-10-corpus-semantic/TDD.md` §2.1）。

微观意图：L4 派发时顺手把 `m3-coverage.sh` 的宿主缺失分支按裁定 94 D2/D3 的口径写死
（默认宿主**不得**回落 `mini_ed01`；`rc != 0` 或解析行数为 0 一律不得 `exit 0`）——
impl-09 的两份脚本已是这个写法，直接照抄即可，别让 M3 这份又退回老毛病。
L4 之后是 7.4（签发决定表模板，我出模板→用户填）与 7.5（impl-04 M8 知识链 + GraphProjectionPack）。

验证方法：
```bash
cd /Users/jingtaiwei/Git/Public/learn_system && export LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/intake/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"        # Ran 35 OK
.venv/bin/python -m unittest discover -s pipeline/digitization/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"  # Ran 67 OK
.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"          # Ran 139 OK
.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/semantic/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)" # Ran 54 OK
bash openspec/acceptance/run_all.sh | tail -1        # SUMMARY pass=2 fail=1 blocked=8（基线，恒不变）
bash openspec/acceptance/m1-intake.sh; echo exit=$?  # exit=2（宿主未落地）
```

---

## 用户待办（不由机时决定，回来先看这两条）

- [ ] **签发决定表**：真实 `expert_verified` 由用户本人签发，主 Agent 出模板（裁定 80）。
      不填则 M6 `upstream_real`、M4 真实签发等判定**永远 BLOCKED**，规格写死，任何 Agent 不得代填（P7）。
- [ ] **验收宿主原文**：需《乾元秘旨》一段真实电子文本入仓做验收样本（`pipeline/corpus/_fixture/qianyuan_ed01_text`）。
      属独占 fixture ACT（P4）。取不取、取多少、权利状态怎么标，等用户发话。
      在此之前 `m1-intake.sh`/`m2-sanitization.sh`/`m3-coverage.sh` 如实 exit 2 是**设计意图**，不是缺陷。

---

## 计划区（W7）

- [x] 7.0 M6→M7 真实上游接线（impl-07 g0-06 `0ef4105`、impl-06 act/12 `dc83cf9`；裁定 83/84/87）
- [x] 7.1 impl-00 act/14 电子文本闭集登记（`ec8c3a8`，36 PASS）
- [x] 7.2 impl-09 M1+M2 电子文本（阶段 A + J1–J4 + J1a/J1b/J3a/J3b/J3c，全部 `ACCEPTED`）
- [ ] 7.3 impl-10 M3 偏移锚点 + 语义层
  - [x] 阶段 A 起草（`fcf9458`→`3359e4b`）
  - [x] L1 偏移锚点与切分（`0d50d29`、`1eab4be`）
  - [x] L2 输入解析/事务 + Gate/组装（`e5b07ed`、`6ec07c5`）
  - [x] L3 语义层（`13ddfd1`、`e42c482`、`2d7b613`、`61070ad`）
  - [ ] **L4 `m3-coverage.sh` 电子文本宿主支持（act/07，阈值 ≥148）**
- [ ] 7.4 签发决定表模板 → 用户填写 → M4/M6 真实签发导入
- [ ] 7.5 impl-04 跟进：M8 知识链前三段 + GraphProjectionPack

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
