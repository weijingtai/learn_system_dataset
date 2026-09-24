# 云端接手说明（2026-09-23，本地主 Agent 移交）

> 写给：在 GitHub 上接手本仓库的 Claude Code 云端会话（以及 Jules 等云端执行者）。
> 写的人：本地主 Agent（Claude）。用户已要求本地**停止**继续处理，后续全部在云端完成。
> **先读完本文件，再读仓库根 `TODO.md`。** 本文件讲前因后果和现场；`TODO.md` 是唯一的待办入口。

---

## 一、一句话现状

目标是 **M1→M8 由调度器连成一条线**，并且各阶段只经 `LedgerPort` 读写账本（不走后门）。
当前卡在两件事上，**必须按顺序做**：

1. **T03c**：5 个模块包还有 111 处走后门（直接读账本内部）。任务书已写好：`docs/jules/T03c.md`。
2. **T04**：M1→M8 连成一条线。做了一半、已暂停，半成品在两个 `wip/` 分支上；它被 T03c 挡着。

---

## 二、前因后果

### 1. 为什么有 `TODO.md`

用户 4 天前就要求「把所有问题清掉」，结果一直有遗留。根因是**没有任务追踪**：事情散在对话、`PLAN.md`、`HANDOFF.md`、各 CHARTER 里，边做边掉。
所以 09-23 建了仓库根 `TODO.md` 作为唯一的待办入口，规则写在它开头。**请严格照它的规则做：一次一条，做完改状态并附证据，新发现的问题先入表再动手。**

### 2. 已完成的（09-23）

| 条目 | 提交 | 内容 |
|---|---|---|
| M7 增量汇编（I 波收口） | `64c091e` 等 | 多版次对勘四类关系全部可达，`run_all.sh 20.5` 首次 PASS。细节见 `docs/blackbox-spec-rework/work-items/impl-07-assembly/CHARTER-INCREMENTAL.md` §25–§32 |
| **T02** | `57e2a44` | `run_all.sh` 里 7 处写死的 BLOCKED 改为读 M8 实际产出再判。改完后露出 M8 的真实状况：三个构建函数只有测试在调、`run_m8` 从没调过（→ T05f）；M8 的输入不接 M7（→ T04） |
| **T03** | `fd0ba6e`、`3adf199`、`a3e7908`、`a404fca`、`d44f4e2` | M3/M5/M8 共 63 处走后门清零；账本端口补了 8 个只读查询 |

### 3. T03 的漏洞 → T03c

T03 说「全部清零」，**只对当时已登记为生产模块的 M3、M5、M8 成立**。检测器 `modules_port_clean` 只扫登记表里的模块。
T04 一把 M1、M7 登记成生产模块，检测器立刻在它们的包里查出后门，`modules_port_clean` 从 PASS 退回 BLOCKED。
在 `215d1e3` 上实测 5 个包共 111 处：intake 3、digitization 5、knowledge_extraction 22、assembly 28、review 53。
**结论：T03c 必须先做，否则 T04 一登记模块就红。** 做法照 T03，**不许缩小扫描范围**（那等于放宽检查）。

### 4. T04 做到哪、为什么暂停

T04 拆成两路并行（两个便宜执行器）：

- **T04A（M1→M6，EditionRun）**：执行器读完代码先停手报了 4 个问题，主 Agent 裁决见 `docs/handoff/t04a-ruling1.md`。按裁决做了一部分后额度到点、被切断。
- **T04B（M7→M8，ReleaseRun，含 T05f）**：只写了 2 条红用例（测试先行），实现还没动。它报了一条待裁决：登记 M7 会暴露 `assembly/` 的 28 处后门——也就是 T03c。

用户随后要求**停手交接**，并决定把 T03c 和 T04 移到云端做。

#### T04A 的 4 条裁决（摘要，全文见 `t04a-ruling1.md`）

1. **M1/M2 自己登记 StagePackage**。原先 `run_m1`/`run_m2` 从不登记阶段包，调度器 Gate 要求每阶段恰 1 个包，所以在 M1 就永远卡死。不许在调度器里代生成（那等于伪造模块产出）。
2. **生产登记表只登记电子文本路线**：运行输入显式声明 `route: text`，缺失或非 text 即拒收，**不许按产物去猜路线**；M3 入口换成 `run_m3_text`；删掉 `m1.fixture_import`、`m2.fixture_import`。（OCR 路线 M2 没有生产模块 → `TODO.md` T04c。）
3. **人工暂停与恢复**：`run_legacy` 接受 `awaiting_human` 终态；描述符加 `resume_entry`（m4 → `knowledge_extraction.step:resume_m4`，m6 → `review.step:close_review`）；**`resume_token` 只在内存里交给调用方，绝不写进账本或任何文件**，要有用例按字节搜证明没落盘。
4. **20.1 的宿主与判据**：宿主换 `pipeline/corpus/_fixture/qianyuan_ed01_text/`，判据改为 M1→M6 全线，**只许收紧**：每阶段恰 1 个生产阶段包；只在 M4、M6 停下等人；人工操作走公开入口（M4 用 fixture `m4/submission_*.yaml`，M6 经 `review/console.py` 公开 API）；不许直接写账本伪造人工结果。

#### 半成品在哪

| 分支 | 提交 | 内容 | 状态 |
|---|---|---|---|
| `wip/t04a-handoff` | `8332484` | M1/M2 登记阶段包（**绿**）；调度器 `human.resume` 走 `resume_entry`、`runner` 接受 `awaiting_human` 并回传 token、`run_inputs.py`、登记表改动；新全线用例 `test_edition_run_text_chain.py` | **红**：orchestrator 1E+6F、contract_registry 6F（本地环境）。原因见 `t04a.report.md` 末尾「交接」 |
| `wip/t04b-handoff` | `87e889d` | `pipeline/dataset_compiler/tests/test_t04b_m7_to_m8.py`（2 条红用例） | **红**（测试先行，实现未动）。下一步清单见 `t04b.report.md`「交接」 |

**两个分支都不许直接合并。** 建议做法：T03c 在 `main` 上完成并合入后，从新的 `main` 拉 T04 分支，把 `wip/` 里的改动按需 cherry-pick 或参照重写。

T04A 红的三个原因（主 Agent 实测）：
1. 全线用例跑到 M4 报 `ExtractionRefused: 缺少 technique_profile`：M4 需要的运行配置还没接进 `run_inputs`。
2. 旧用例锁着「首纵切 m1/m2/m3/m5」「m2 imported」「5 PASS 1 BLOCKED」等旧口径，按裁决 4 要改写，**每条写明改前/改后/为什么**。
3. `modules_port_clean` 退回 BLOCKED：即 T03c。

---

## 三、接下来的顺序

1. **T03c**：照 `docs/jules/T03c.md` 做（本来写给 Jules，云端 Claude 也照用）。完成判据：5 个包 `scan_ledger_internals` 全为 0，11 个包测试不比基线新增红或 skip，加守护用例。
2. **T04**：从 T03c 之后的 `main` 拉分支，合入两个 `wip/` 的有效改动，按 `t04a-ruling1.md` 与 `TODO.md` 的 T04 完成判据做完。
3. 然后按 `TODO.md` 顺序：T05（M8，先做 T05f）→ T06 → 其余。

---

## 四、云端环境与限制（重要）

```bash
bash tools/jules_setup.sh          # Python 3.14 + .venv/ + requirements-dev.txt
export LC_ALL=C.UTF-8 LANG=C.UTF-8 # 测试需要 UTF-8 locale
```

**有两样东西不在版本库里，云端没有：**

| 缺的东西 | 影响 |
|---|---|
| 派生页图目录（本地 `FIXTURE_ASSET_ROOT`） | `dataset_compiler` 36 条 skip；`orchestrator` 5 条 + `contract_registry` 1 条**会红**（写死本机有页图，是测试缺陷，见 `TODO.md` T14）。**这 6 条是云端的已知基线红，不是你改坏的** |
| 真书账本 `var/ledgers/qianyuan_w8/`（《乾元秘旨》M1–M6 的真实人工决定） | `assembly` 2 条 skip；**T04 完成判据第③条（真书在账本副本上由调度器跑 M1→M8）云端无法验证**，要在用户本机复验。云端能做的是在 `qianyuan_ed01_text` fixture 上跑全线 |

干净副本上的基线（`215d1e3`，无页图、无真书账本）见 `docs/jules/T03c.md` 第五节的表。

---

## 五、这条线踩过的坑（请务必遵守）

这几天反复出现「测试全绿、真实路径却不通」，一共七次以上。由此定下的纪律：

1. **不许放宽任何检查来换绿**：不改检测器范围、不写死期望值、不把 FAIL 改成 BLOCKED。
2. **R15：每一波都要有一条真实形状输入、从头走到尾的用例**；手工构造输入的单测只能证明函数本身没错。
3. **新增的公开函数必须在非测试代码里有调用点**，只有测试在调的一律当作「没接上」（M7 D 波、M8 T05f 都是这个问题）。
4. **「各模块过了自己的验收」≠「已连通」**。说「连通」之前必须跑 `bash openspec/acceptance/run_all.sh 20.1` 并 PASS。
5. **测试不许默认宿主有什么**：依赖真书账本、页图的用例，要按实际宿主计算期望或 skip 并写明原因（G2 修过一次，T14 还有 6 条）。
6. **先写测试确认转红，再实现**；每个修复配一条篡改探针（去掉修复，指定用例必须转红）。
7. **拿不准就停手写「待裁决」**，写清证据和候选方案；不要猜。
8. 状态判断要有证据：提交号、测试原文。不说「应该好了」。

---

## 六、文档地图

| 文件 | 用途 |
|---|---|
| `TODO.md` | **唯一待办入口**（T01–T14） |
| `docs/jules/T03c.md` | T03c 完整任务书 |
| `docs/handoff/t04a-ruling1.md` | T04A 的 4 条裁决 |
| `docs/handoff/t04a.report.md`、`t04b.report.md` | 两路执行器的回报与交接 |
| `docs/handoff/t04a.md`、`t04b.md`、`t04-common.md` | 两路的原始派单与共用背景 |
| `HANDOFF.md`、`PLAN.md` | 更早的交接与计划（`PLAN.md` 里的旧待办待核实，见 `TODO.md` T09） |
| `openspec/acceptance/run_all.sh` | 全仓库验收（20.1–20.11） |
| `docs/blackbox-spec-rework/work-items/impl-07-assembly/CHARTER-INCREMENTAL.md` | M7 的全部裁定记录 |
| `openspec/learn-system-blackbox-architecture.md` | 架构规格 |

## 七、需要用户决定、云端不要自行处理的

- `TODO.md` T01（XUAN 奇门底本答复）、T13（20.7 旧格局库怎么处理）：都在等用户决定。
- T04 第③条真书复验：需要用户本机。
