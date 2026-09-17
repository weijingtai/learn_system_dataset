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

## 当前状态（2026-09-16 暂停）

W8：《乾元秘旨》电子文本真书走到 M8（第 100–108 条；计划 `G7-PLAN.md` §6）。

**已完成并验收**：M1/M2（J3e/J3f/J4b，M2 与独立金标 12 类一致，宿主已入库）；M3→M4 衔接（8.1）；M4 offset 支持 + 两路抽取 + **用户 24 条裁决已导入，M4 封存**（8.2）；M5 offset 档 + PUA 对账（8.3，真书 INTERNAL_DEMO 通过）；M8 登记 ACT 08 与 K1（ACT 09 GraphProjectionPack、ACT 10 reference_and_hash_only/offset 七段链）。

**真书持久 Ledger**：`var/ledgers/qianyuan_w8/`（不入库；备份 `qianyuan_w8.bak_before_m4_rulings`）——M1→M2→M3→M4（succeeded）→M5（succeeded）已在其上跑完。

**半成品 / 回来先做（按顺序）**：
1. **8.4 M6**：R84 `4e16022`、R84b `cb96b94` 已提交**未验收**，且 review 套件有既有用例红（夹具 `pipeline/review/testing/data/m4_candidates.yaml` 中 `as_qizheng_000002` 偏移应为 9–11，第 108 条）。派单 `~/tmux-agents/runs/prompts/agy-84b.txt`（未执行）；回报 `agy-84.report.md`。agy 续接对话 `1d32b970-8f83-47d6-8571-7476d4b65903`。
2. 验收 8.4 后：在 `var/ledgers/qianyuan_w8/` 跑 M6 到 awaiting_human → 主 Agent 生成 M6 审核表给用户（须告知：26 条 assertion 无 `concept_refs`，要编出 Concept 词条需用户 `modify` 补显式引用；2 条 a 路 assertion 被 G4 拒收）。
3. **8.6 M8 K2**（ACT 11 知识链+`ent_` 发号表、ACT 12 Gate）：派单 `agy-86d.txt`（agy 读完代码后撞额度，未动手）；续接对话 `af9e74e2-766b-4ca2-9bd1-6b1c4f4f2fc7`。
4. 8.5 M7 Snapshot 补 `evidence_level`/`corpus_spans_revision_id`（第 106 条 D4，未派）→ M8 ACT 13 改读 Snapshot → ACT 14 验收脚本与 run_all 转判（8.7）。

**执行器现状**：cmd（DeepSeek V4.1 Flash）周限额，周六 9-19 12:13 重置；agy（Gemini 3.8 Flash Medium）个人额度约 2 小时重置；opencode Union Alpha 不可靠。换执行器前先问用户。

验证基线：`check_interfaces` `pass=44 fail=0`；`run_all.sh` `SUMMARY pass=2 fail=1 blocked=8`；干净树 orchestrator/contract_registry 因页图不入库各有 5/1 条失败，属环境。

## 用户待办

- [ ] **M6 审核表**（W8 8.4 之后由主 Agent 生成）：用户逐条 接受/修改/驳回；不得由 Agent 代填（P7）。
- [ ] **签发决定表**：真实 `expert_verified` 由用户本人签发（第 80 条），不阻断 W8 的 `INTERNAL_DEMO`，阻断 `PUBLIC_RELEASE` 与 M6 `upstream_real` 判定。
- [x] 验收宿主原文：《乾元秘旨》全文已入库（J4b `1406048`）。
- [x] M4 分歧裁决：24 组已由用户填写并导入（2026-09-16）。

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
