# T24：Web 控制台接真流程 —— 工作文档（README）

状态：**只完成本文档（含 TDD.md、act/01.yaml、PRD 作废标注），未写实现代码**。范围收窄见文末「本轮范围」。
实现将由用户本机的外部 agent 按本文档独立执行；本文档要写到它不需要再回来问设计问题。

## 0. 基线（协调者 09-26 更正后）

**本 worktree 已 `git merge claude/wizardly-maxwell-pqrzh9`**（合并提交 `6a06144`，merge 不是
rebase，无冲突），因此本分支现在**含 T04 全部产出**：`registry.yaml` 里 m1～m8 全部登记，
m4/m6/m7 都带 `resume_entry`；`start_edition_run` 接受 `run_inputs`；`run_real_book_t04.py`、
`docs/handoff/ASK-2026-09-26.reply.md`、`docs/handoff/U07-decisions_supplement.yaml` 都已在本分支。
下面第 6 节的公开入口签名、路径、行号均已在**合并后**的树上逐一重新核对（见本节末尾），
以此为准；这不再是阻断，T24 的实现直接基于这条已合并的分支做。

**已核对的签名/行号（2026-09-26，合并提交 `6a06144` 上实测）**：

| 引用 | 位置 |
|---|---|
| `start_edition_run(port, *, edition_part_id, technique_id, run_inputs=None)` | `pipeline/orchestrator/edition_run.py:140` |
| `advance(port, registry, handle, *, modules=None, stages=EDITION_STAGES)` | `pipeline/orchestrator/edition_run.py:265` |
| `run_release(port, registry, edition_handle, *, modules=None)` | `pipeline/orchestrator/edition_run.py:369` |
| `run_until(...)` | `pipeline/orchestrator/edition_run.py:450` |
| `human.resume(port, registry, handle, step_run_id, resume_token, *, modules=None)`，legacy 绑定经 `_legacy_resume_entry` 调用描述符的 `resume_entry` | `pipeline/orchestrator/human.py:96-119`（`_legacy_resume_entry` 在 `:96`，`resume` 在 `:106`） |
| `registry.yaml` m4 登记，`resume_entry: "pipeline.knowledge_extraction.step:resume_m4"` | `pipeline/contract_registry/registry.yaml:94-99` |
| `registry.yaml` m6 登记，`resume_entry: "pipeline.review.step:close_review"` | `pipeline/contract_registry/registry.yaml:136-141` |
| `registry.yaml` m7 登记，`resume_entry: "pipeline.assembly.step:resume_m7"` | `pipeline/contract_registry/registry.yaml:157-162` |
| `run_m4_submit(...)` | `pipeline/knowledge_extraction/submit.py:69` |
| `record_category_ruling(service, step_run_id, resume_token, ruling_doc)` | `pipeline/knowledge_extraction/step.py:703` |
| `record_decision(service, step_run_id, resume_token, *, ...)` | `pipeline/review/step.py:434` |
| `resume_token_hash` 只存哈希，明文不落盘 | `pipeline/ledger/store.py:97, 194, 397-415` |

（第 8、9 节其余的行号引用同样已按合并后的树重新核实，不重复列在此表。）

## 1. 目标

把 `console_backend`（FastAPI）+ `console_frontend`（Vue 3）从"骨架/mock"改造成
**`pipeline.orchestrator` 人工节点的前端**：

- 用户在界面上传一本电子文本 → 后端经公开入口新建 EditionRun 并自动推进；
- 调度器在规格规定的人工节点（M4 分歧裁决、M6 审核）自动停在 `awaiting_human`；
- 界面把该节点的队列（M4 分歧 / M6 候选）**连同「AI 预审建议」**一起显示给用户；
- 用户在界面上逐条给出决定（不是命令行、不是直接改文件），决定经公开入口
  （`record_category_ruling` / `record_decision`）写入 Ledger，随后后端自动 `resume` 续跑；
- 全部人工节点走完后，界面显示 `run_release` 产出的 M8 结果，可下载发布包；
- 任一阶段失败，界面如实显示失败原因（不隐藏、不重新包装成"处理中"）；
- 刷新页面或重开浏览器，界面能查出当前这个 EditionRun 停在哪一步。

**定位改变**：控制台不再自己"审"（PRD 里 Task 2.5「AI 自动签发」、Task 4.1「全自动 AI 代审出包」
已在 `WEB_CONSOLE_PRD_AND_PLAN.md` 里标注**作废（T24，P7）**，理由：规格 P7——M4 裁决与 M6 审核
只能由用户本人做，不允许任何 Agent/AI 代签路径。控制台唯一的写账本方式是把用户在界面上点击/填写
的决定转成对公开入口的一次调用；调用参数里的 `actor_ref` 由用户在界面配置（默认 `user:wjt`），
代码不得编造成别人，也不得在用户没有点击的情况下自己调用这些入口。

## 2. 范围

**只做电子文本路线（`route: text`）**。OCR 路线、M4 模型自动抽取（T06）不在本次范围内——
M4 的候选内容仍由用户上传人工/半人工产出的提交件 YAML（同 `run_m4_submit` 现有用法）。

## 3. 本轮范围（本次会话实际交付）

协调者 09-26 缩小范围：**本次只交付 README.md / TDD.md / act/01.yaml 三份文档 + PRD 作废标注，
提交后停手，不写任何实现代码**。下面第 4～9 节是给后续实现者的完整设计，第 10 节起是给实现者
落地时要先做的核实清单。

## 4. 用户新增需求（09-26）：M4/M6 决定必须在界面做，并显示 AI 预审建议

用户明确要求：**M4 分歧裁决与 M6 审核，用户都在 Web 界面里操作，不看命令行、不直接编辑文件。**
界面在每个队列项（M4 dispute / M6 candidate）上，除了原文、候选内容之外，还要显示一条
**「AI 预审建议」**：由本机外部 agent（FreeBuff / OpenCode，T06 范畴，本次不实现该适配器本身）
事先跑出来、存成文件的建议——建议的 verdict/choice、理由、引用的原文片段。

用户可以：
- 一键「采纳建议」：把建议的 choice/verdict 和理由**填入**决定表单，**仍需用户点击提交**才算数；
- 修改建议后提交（改选、改理由）；
- 完全不看建议，自己写。

**硬性约束**：建议文件只是**展示数据**，任何情况下界面/后端不得因为存在建议文件就自动调用
`record_category_ruling` / `record_decision`。没有用户在界面上的一次显式提交动作，就不存在决定。
批量视图（按建议分组、按 verdict/choice 筛选、逐条过一遍）与进度统计（已审/未审/与建议不一致数）
要有，但"批量"仅指界面按队列展示与筛选的效率，**提交仍是逐条的一次 HTTP 调用一条决定**——
不允许"批量提交"把多条决定压成一次隐式全部通过。

### 4.1 建议文件格式（本次设计，T06 适配器将来产出，T24 只读取展示）

路径约定：`<edition_part 工作目录>/ai_review_suggestions/<stage>.yaml`
（`stage` 为 `m4` 或 `m6`；工作目录即控制台记录 EditionRun 时用户上传原文所在的目录，
与 `pipeline/corpus/_fixture/qianyuan_ed01_text/` 类比的宿主目录同级）。
控制台后端提供一个「上传预审建议文件」的端点，允许用户在 M4/M6 停在 `awaiting_human` 之后，
把外部 agent 产出的建议文件上传给控制台（不落 Ledger，只是控制台本地展示用的辅助文件）。

字段（YAML，每份文件是一个列表，一条队列项一条建议）：

```yaml
schema_version: "1.0.0"
stage: m4                      # 或 m6，必须与本文件对应的队列一致
generated_at: "2026-09-26T08:00:00Z"   # ISO8601，外部 agent 产出建议的时间
producer:
  model_id: "deepseek/deepseek-v4.1-flash"   # 沿用 M4 提交件里 producer.model_id 的写法
  tool: "freebuff"              # 或 opencode
file_sha256: "<整份文件规范化后的 sha256，由后端读入后校验；不由建议文件自己声明>"
items:
  - target_id: "dis_..."        # M4: dispute_id；M6: 队列项定位见下
    entity_kind: null           # M6 专用，assertion/school_view/pattern；M4 留空
    suggested_choice: "a"       # M4 用 choice 闭集（对应 record_category_ruling 的 choice）
    suggested_verdict: null     # M6 用 verdict 闭集（accept/modify/reject），M4 留空
    rationale: "两路候选语义收敛，引文可在原文定位，建议采 a 路。"
    evidence_quotes:
      - "《...》：原文引用片段，用于用户核对建议依据"
```

对位规则：
- M4：`target_id` 必须等于该队列项的 `dispute_id`（后端从 M4 disputes 修订里读到的同一个 ID）；
- M6：`target_id` + `entity_kind` 必须能定位到一条候选（沿用 `record_decision` 的
  `target.entity_id` / `target.entity_kind` 语义）；
- 一份建议文件里若出现队列里不存在的 `target_id`，或队列里某项没有对应的建议，
  **界面照实显示**（"建议：无匹配"或"队列中已找不到该建议对应的项，可能是队列已刷新"），
  不得因为对不上就报错阻断其他项的展示；
- `file_sha256` 由后端校验（读入文件后重新计算），不信任建议文件自称的哈希；校验失败则整份
  文件拒绝导入，界面提示"建议文件哈希不一致，已拒绝导入"。

### 4.2 建议来源与用户决定如何关联记录（不改账本 schema）

`record_category_ruling` 的 `ruling_doc` 与 `record_decision` 的参数里都没有可自由扩展的
"元数据"字段（`ruling_doc` 键集合是闭集：`schema_version/dispute_id/choice/rationale/
synthetic_fixture/actor_ref`；`record_decision` 的 `rationale` 是自由文本字符串）。
**本次设计选择：不改账本 schema**，约定当用户的决定采纳或参考了某条 AI 预审建议时，
后端在提交前把建议来源信息**追加进 `rationale` 文本**，格式（追加内容用户在界面上可见、
提交前可编辑/删除）：

```
<用户填写的理由原文>

[AI预审建议] model_id=deepseek/deepseek-v4.1-flash generated_at=2026-09-26T08:00:00Z suggestion_file_sha256=<sha256> adopted=<true|false>
```

`adopted` 标记用户是点了"采纳建议"还是自己写完全不同的理由；只要界面显示过建议且用户提交了
决定，就带上这段附注（哪怕用户没有采纳，也如实记 `adopted=false`，留痕"当时有建议、用户没采纳"）。
这段追加文本**不是**结构化字段，只能靠字符串前缀 `[AI预审建议]` 加 `key=value` 之后人工/脚本
解析；**如果将来需要结构化查询建议采纳率之类的统计，需要改 `ruling_doc`/`record_decision`
的 schema（新增可选字段），那是待裁决项，本文档不擅自扩展 schema。**

### 4.3 新增 BDD 场景（见第 5 节场景 S9、S10）

## 5. BDD 场景（Given / When / Then）

场景全部以「用户」为唯一决定主体，`actor_ref` 由界面配置项给出（默认 `user:wjt`）。

### S1 上传电子文本建 EditionRun

```gherkin
Given 控制台首页，用户尚未创建任何 EditionRun
When 用户上传一份电子文本文件（含 source_info.yaml 所需的元数据表单：书名/版本/technique_id 等）
Then 后端调用 pipeline.orchestrator.edition_run.start_edition_run(adapter, edition_part_id=..., technique_id=..., run_inputs={"route": "text", ...})
 And 界面显示新建的 edition_run_id / edition_part_id，状态为「进行中，M1」
```

### S2 自动推进到 M4 停下

```gherkin
Given 已创建的 EditionRun（M1 尚未跑）
When 控制台后端自动调用 run_until(adapter, registry, handle, "m3") 然后 advance(...) 推进到 m4
Then M1→M3 依次显示为 succeeded
 And M4 的 StepRun 状态为 awaiting_human，界面显示"等待 M4 分歧裁决"
 And 后端在内存中保留该 step_run_id 与 resume_token（不落盘，见第 8 节）
```

### S3 上传 M4 提交件

```gherkin
Given EditionRun 已停在 M3 succeeded、M4 尚未 advance，或 M4 已 advance 但提交件还没登记齐
When 用户在界面上传若干份 M4 提交件 YAML（对应现有 6 类命名，如 submission_assertion_a.yaml）
Then 后端逐份调用 run_m4_submit(service, edition_part_id, file_bytes, producer_module=..., producer_version=...)
 And 每份提交件的登记结果（succeeded/failed 及原因）逐份显示在界面
```

### S4 界面列出 M4 分歧队列，用户逐条裁决后续跑

```gherkin
Given M4 已 advance 到 awaiting_human，disputes 已经生成
When 用户打开"M4 分歧裁决"页面
Then 界面列出全部待裁决的 dispute（含每类候选内容、AI 预审建议——若已上传，见 S9）
When 用户对每一条选择 choice 并填写/采纳理由后逐条提交
Then 后端逐条调用 record_category_ruling(service, step_run_id, resume_token, ruling_doc)，actor_ref 为界面配置的用户身份
 And 界面显示"已裁决 N / 共 M"的进度
When 全部裁决完毕，用户点击"继续"
Then 后端调用 human.resume(adapter, registry, handle, step_run_id, resume_token)
 And 界面显示 M4 状态变为 succeeded，自动进入 M5
```

### S5 M5 自动过

```gherkin
Given M4 已 resume 成功
When 后端自动调用 advance(...) 推进 M5
Then 界面显示 M5 succeeded（若 M5 gate 有披露项 warning，如实显示，不隐藏）
 And 若 M5 失败（error 级门禁），界面显示失败原因，停止自动推进，不进入 M6
```

### S6 M6 审核队列逐条 accept/modify/reject 后续跑

```gherkin
Given M5 succeeded，后端 advance 到 M6 停在 awaiting_human
When 用户打开"M6 审核"页面
Then 界面列出全部候选（assertion/school_view/pattern），含 AI 预审建议（若已上传，见 S9）
When 用户对每一条给出 verdict（accept/modify/reject）与理由，modify 时给出 modified_content
Then 后端逐条调用 record_decision(service, step_run_id, resume_token, queue_item_id=..., verdict=..., rationale=..., modified_content=..., evidence_refs=...)
When 全部决定完毕，用户点击"继续"
Then 后端调用 human.resume(...)，M6 转为 succeeded，EditionRun 收口（advance 返回 action=complete）
```

### S7 run_release 出 M8，下载发布包

```gherkin
Given EditionRun 已收口（complete）
When 用户点击"生成发布包"
Then 后端调用 run_release(adapter, registry, handle)（签名 `run_release(port, registry, edition_handle, *, modules=None)`，
   `pipeline/orchestrator/edition_run.py:369`，合并后已核实与本文档一致）
 And 界面显示 M7 创世与 M8 编译的结果（knowledge_chain 状态、PublicationPackage 修订号）
When 用户点击"下载"
Then 后端把该 PublicationPackage 打包（或直接给出已封存的字节）供浏览器下载
```

### S8 任一阶段失败时界面如实显示失败原因；刷新/重开后能看到当前停在哪

```gherkin
Given 某阶段（如 M4 提交件校验、M5 门禁、M8 gate）执行失败
When 后端 advance/execute 收到失败的 step_result
Then 界面显示该阶段状态为 failed，附带后端返回的失败原因（不改写、不重新措辞成"处理中"或"成功"）
 And 不自动继续推进后续阶段

Given 用户已创建 EditionRun 并推进到某个阶段（含 awaiting_human 与 failed）
When 用户刷新页面或重新打开浏览器
Then 后端从 Ledger 查询该 edition_part_id 的最新 StepRun 状态（经 list_step_runs / run_status 等只读入口，
   不查控制台自己的 SQLite），界面据此显示当前停在哪一步
 And 若该 EditionRun 停在 awaiting_human 但后端进程已重启（resume_token 已丢失），界面显示
   "恢复凭证已丢失，点击「恢复审核」重新获取"，不假装能直接续跑（见第 8 节，用户已裁决
   候选 B——点击后经用户确认调用 `reissue_resume_token`，不自动重签）
```

### S9 M4/M6 界面显示 AI 预审建议，用户可采纳/修改/忽略（09-26 新增）

```gherkin
Given M4 已停在 awaiting_human，用户已上传对应的 ai_review_suggestions/m4.yaml
When 用户打开"M4 分歧裁决"页面
Then 每条 dispute 卡片上，原文/候选内容旁边显示该 dispute 对应的建议（choice、理由、引用片段）
 And 建议卡片显示来源（model_id、generated_at、file_sha256 前 8 位）
 And 队列中找不到对应建议的项，显示"无预审建议"；建议文件里有队列没有的 target_id，界面在建议列表
   单独提示"以下建议未匹配到当前队列项"（不阻断其他项显示）
When 用户点击某条的"采纳建议"
Then 决定表单的 choice 与理由被建议内容填充，光标停留在理由框，用户仍需点击"提交"才算完成一条裁决
When 用户提交（无论是否点过采纳）
Then 后端把 `[AI预审建议] model_id=... generated_at=... suggestion_file_sha256=... adopted=<true|false>` 追加进
   record_category_ruling 的 rationale 文本（约定见第 4.2 节），adopted 按用户是否点过"采纳建议"判定
 And 若用户在采纳后又手改了 choice 或理由，adopted 仍记 true（表示"当时以建议为起点"），
   界面不额外区分"完全采纳"与"部分参考"（本次范围不做更细粒度，见 TDD 里的待裁决）
```

同理适用于 M6 审核页面（`ai_review_suggestions/m6.yaml`，`suggested_verdict` 替代
`suggested_choice`，`target_id` + `entity_kind` 定位候选）。

### S10 批量视图与进度统计（09-26 新增）

```gherkin
Given M4 或 M6 的队列已加载，部分条目已上传预审建议
When 用户在队列页面按"与建议一致/不一致/无建议"筛选，或按 verdict/choice 分组浏览
Then 界面只做**客户端筛选/分组**（已加载的队列数据在前端过滤），不产生新的后端调用
 And 页面顶部显示进度："已审 X / 共 N；与建议不一致 Y 条"
When 用户使用"逐条过"模式（下一条/上一条导航）逐一提交
Then 每次提交仍是一次独立的 record_category_ruling / record_decision 调用（见 S4/S6），
   没有"全部通过"或"全部采纳建议"的批量提交按钮
```

## 6. 公开入口函数与调用顺序

按 `claude/wizardly-maxwell-pqrzh9` 上 `pipeline/tools/run_real_book_t04.py` 的驱动序列
（合并 `claude/wizardly-maxwell-pqrzh9` 后，本文档设计的调用顺序与函数签名已在 `6a06144` 上
逐一核对，见第 0 节的对照表；下面调用序列里的参数名与实际签名一致）：

```
start_edition_run(adapter, edition_part_id=..., technique_id=..., run_inputs={"route": "text", ...})
  → handle
run_until(adapter, registry, handle, "m3")           # 自动跑 M1→M3
run_m4_submit(service, edition_part_id, file_bytes, producer_module=..., producer_version=...)  # 每份提交件一次
advance(adapter, registry, handle)                    # 停在 M4 awaiting_human，取 step_run_id + resume_token
record_category_ruling(service, step_run_id, resume_token, ruling_doc)   # 每条 dispute 一次
human.resume(adapter, registry, handle, step_run_id, resume_token)
advance(adapter, registry, handle)                    # M5，自动
advance(adapter, registry, handle)                    # 停在 M6 awaiting_human
record_decision(service, step_run_id, resume_token, queue_item_id=..., verdict=..., rationale=..., ...)  # 每条候选一次
human.resume(adapter, registry, handle, step_run_id, resume_token)
advance(adapter, registry, handle)                    # 收口，action == "complete"
run_release(adapter, registry, edition_part_id=..., technique_id=...)   # M7 创世 + M8 编译
```

控制台后端的角色：把上面每一步包成一个 HTTP 端点（或在 advance 到人工节点前自动串联到人工节点为止），
**不新增任何绕过这条链路的写路径**。只读查询（列队列、查状态）用
`service.list_step_runs` / `service.list_human_events` / `service.get_step_run` /
`service.list_step_run_revisions` 等既有只读入口（`run_real_book_t04.py` 里已经在用这些）。

## 7. 要改/新增的文件（设计层面，供实现者规划,不是本次交付）

- `console_backend/app/orchestrator_client.py`（新增）：唯一允许调用上面第 6 节公开入口的模块；
  持有进程内存里的 `{step_run_id: resume_token}` 映射（第 8 节的内存态）。
- `console_backend/app/repository.py`：删除或改造——PipelineRun/M1/M2/审核队列/决定的持久化事实
  部分换成对 Ledger 的只读查询；纯 UI 偏好（如"用户上次打开的标签页"）可以留在 SQLite 或前端本地存储。
- `console_backend/app/routers/workbench.py`：删除 mock（`_create_default_mock_page_scan` 等），
  M4/M6 队列改为从 `orchestrator_client` 读取真实 disputes/candidates；`/review/decide` 改为逐条转发
  到 `record_decision`（不再自己判断"全部审核完成"，那由 `advance`/`resume` 之后的状态决定）。
- `console_backend/app/routers/pipeline.py`：新增/改造 EditionRun 生命周期端点（创建、advance、
  上传 M4 提交件、上传 AI 预审建议文件、resume、run_release、下载发布包、查状态）。
- `console_frontend/src/*`：把现有 mock 数据源换成对上面端点的真实请求；新增"AI 预审建议"展示
  与"采纳建议"交互（S9/S10），以及"恢复审核"按钮与确认框（§8.4）。
- `pipeline/ledger/service.py`：新增 `LedgerService.reissue_resume_token`（§8.1，唯一需要改的
  `pipeline/` 生产代码之一）。
- `pipeline/ledger/client.py`：新增 `LedgerClient.reissue_resume_token` 转发方法（§8.1）。
- `pipeline/contract_registry/ports.py`：`LEDGER_PORT_METHODS` 元组新增一项
  `"reissue_resume_token"`（§8.1，唯一改动点，`DirectLedgerAdapter`/`LedgerdClientAdapter`/
  `PortGuard` 自动跟随）。
- `docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md`：§1.1 新增一行登记
  `reissue_resume_token`（§8.6）。
- `pipeline/contract_registry` 下 `scan_ledger_internals` 对 `console_backend` 的扫描范围要覆盖
  新代码（见下方基线，它是通用函数、按传入的 `roots` 扫描，不需要改代码就能覆盖 `console_backend`，
  但目前没有任何契约测试拿 `console_backend` 当 `roots` 调用它——实现阶段要新增这条测试，
  而不是假设它已经被谁扫描了）。

### 7.1 `scan_ledger_internals(console_backend)` 当前基线（本次已实测，2026-09-26，`6a06144`）

```python
from pipeline.contract_registry.acceptance import scan_ledger_internals
scan_ledger_internals(["console_backend"])
# => []（0 处命中）
```

**这个 0 不是"已经干净"的证明，读法要小心**：`scan_ledger_internals` 的检测规则是
`LEDGER_INTERNAL_RE = r"\.store\b|\.objects\b"`（`pipeline/contract_registry/acceptance.py:53`）——
它找的是"对 LedgerPort/service 对象直接访问 `.store`/`.objects` 属性"这种绕过端口的写法。
`console_backend` 现在**完全没有 import `pipeline.orchestrator`/`pipeline.ledger`**（它自己的
`SqlitePipelineRepository` 是另一个独立的 SQLite 库，见 §7 上面几条），所以正则天然扫不到任何
东西——0 命中只说明"现在还没碰 Ledger"，不说明"改造完之后仍然干净"。
**实现阶段真正的判据是：接上 `orchestrator_client` 之后重跑这条扫描，必须仍然是 0**；
这条基线（改造前 0）本身没有意义，只是留作"改造前/改造后对照"的起点，且应该在
`pipeline/contract_registry/tests/` 里新增一条用例把 `console_backend` 纳入某个既有或新增的
`modules_port_clean` 同类检查里长期钉住（而不是只手动跑一次），否则以后谁悄悄写了
`service.store...` 也不会被回归发现。

## 8. resume_token 与后端重启问题：**已裁决 B（用户 2026-09-26）**

已读代码（本分支 `pipeline/ledger/service.py`、`pipeline/ledger/store.py`、
`pipeline/ledger/client.py`、`pipeline/contract_registry/ports.py`，均已在合并
`claude/wizardly-maxwell-pqrzh9` 后的树上重新核对行号）：

- `resume_token` 只在 `await_human()` 转换 `running → awaiting_human` 那一刻生成一次
  （`secrets.token_urlsafe(32)`，`service.py:988`），返回给调用方；Ledger **只存它的哈希**
  （`resume_token_hash = "v<status_version>:<sha256(token)>"`，`_token_hash` @ `service.py:99`），
  明文从不落盘（`store.py:97,194,397-415` 只有列定义/绑参，没有任何写文件路径）。这是有意设计，
  不是缺口，**本次裁决不改这一点**。
- `_check_token`（`service.py:958-983`）校验 token 时同时比对哈希与 `status_version`；
  `resume()`（`service.py:1065`）消费后把 `resume_token_hash` 置 `NULL`。
- `recover()`（`service.py:1133`）只处理 `suspended → awaiting_human/running` 这一种情况，
  且遇到"suspended 之前就是 awaiting_human"时是**保留旧 token**（把旧哈希的版本号前缀
  重新对齐到新版本，`service.py:1161-1166`，注释写"BDD 3.3"），这解决的是"操作者手里的
  token 还在、只是 status_version 变了"，**不是**"token 本身已经丢失"——两者是不同问题，
  之前的调查结论把这两者分清楚了。
- `resume_entry`（`registry.yaml` m4/m6/m7 各一条，见 §0 对照表）是 orchestrator 登记表
  描述符字段，告诉 `human.resume` 在 `mode="resumed"` 时该调用哪个模块函数——**它解决的
  是"resume 时该跑哪段代码"，不是"token 丢了怎么办"**，不要混淆。

**结论：没有公开途径能在 token 丢失后重新拿到它**——这就是候选 B 要新增的那个入口。

**用户 2026-09-26 裁决：选候选 B——在 LedgerPort 新增一个公开的「重签发 resume_token」
入口。** 候选 A（控制台本地落盘）与候选 C（只靠运维保活、不解决重启后恢复）不再采用；
候选 C 的"界面如实提示"行为仍保留，但只用于"重签发也失败/用户还没点重签发"时的兜底展示，
不再是唯一手段。**本条规格变更已获用户批准**，属于对 §17.1 人工暂停与恢复机制的扩展，
不是实现者自行决定的放宽，登记方式见 §8.4。

### 8.1 新入口设计：`reissue_resume_token`

**放在哪**：`pipeline/ledger/service.py` 的 `LedgerService` 类，紧邻 `resume`/`suspend`/
`recover`（建议插在 `recover()` 之后，`service.py:1131` 后）；`pipeline/ledger/client.py`
的 `LedgerClient` 加一个同名转发方法（仿 `resume`/`recover` 的写法，`client.py:316-332`
附近）；`pipeline/contract_registry/ports.py` 的 `LEDGER_PORT_METHODS` 元组（`ports.py:19-71`）
里加一行 `"reissue_resume_token",`（建议紧跟 `"recover",` 之后，`ports.py:33`）——这一处改动
会自动让 `DirectLedgerAdapter`、`LedgerdClientAdapter`、`PortGuard`、`port_surface`、
`missing_port_methods` 全部认得这个新方法，不需要在这几个类里手写委托代码（`ports.py:74-78`
的 `_DELEGATED_TO_SERVICE`/`_DELEGATED_TO_CLIENT` 都是从 `LEDGER_PORT_METHODS` 派生的）。
`ledgerd.py` 的 socket 服务端按方法名 `getattr(service, op)` 通用分派（`ledgerd.py:65-73`），
不需要改。**这是唯一需要动 `pipeline/` 生产代码的地方，且范围严格限定为这三个文件的这三处
改动**，其余按本任务第 7 条仍然只读。

**函数签名**：

```python
def reissue_resume_token(self, step_run_id, *, actor_ref, reason):
    """StepRun 仍处于 awaiting_human 但 resume_token 已丢失（例如控制台进程重启、
    内存映射清空）时，使旧 token 立即作废并签发一个新的单次使用 token（§8.2 之外
    再无其他改变：不影响已经登记过的人工事件/决定，见 §8.3）。"""
```

- `step_run_id`：目标 StepRun（M4 分歧裁决或 M6 审核所在的那次 `awaiting_human`）。
- `actor_ref`：**显式参数，不用 `self.actor()`**——与本项目其余 `resume`/`suspend`/`recover`
  不同，这里刻意要求调用方把"是谁点了这个按钮"当参数传进来，而不是依赖进程级的
  `actor_provider`。理由：P7 要求这类操作必须可追溯到界面上的一次用户点击，进程级
  actor 配置容易被误配成某个默认值（例如运维账号），显式参数逼着 `orchestrator_client`
  在调用前先拿到界面传来的用户身份。
- `reason`：自由文本，用户在界面上填写"为什么要重新获取凭证"（例如"后端重启，原恢复
  凭证已丢失"），写入 `step_run_events.reason` 与 `audit_log`，不做闭集校验（同
  `suspend(step_run_id, reason, source)` 的 `reason` 一样是自由文本）。

**前置条件**（不满足则拒绝，不静默）：

1. `step_run_id` 必须存在，否则 `MissingReference`（`code="REF_001"`，同其余方法的既有写法）。
2. StepRun 当前 `status` 必须是 `awaiting_human`；不是就抛 `IllegalTransition`
   （消息里带上当前实际状态，同 `recover()` 的写法 `service.py:1146-1150`）。
   **注意**：`STEP_RUN_TRANSITIONS["awaiting_human"]` 这张表（`states.py:35`）里没有
   `"awaiting_human"` 自己——因为这不是一次"状态迁移"（status 没变，只是版本号和 token
   换了）。所以本方法**不调用** `check_step_run_transition`，改成显式检查
   `if step["status"] != "awaiting_human": raise IllegalTransition(...)`。这是本设计
   唯一偏离"新状态变化都走 `check_step_run_transition`"这条既有惯例的地方，写在这里是
   为了让实现者知道这是刻意的，不是漏调用。
3. 不要求"旧 token 已经真的丢了"这件事本身可验证（后端没法知道调用方是不是真的丢了 token，
   这天然不可验证）——**任何时候用户在界面点了「恢复审核」并确认，都视为合法请求**；
   旧 token 立刻作废，即使它其实还没丢（这是候选 B 的固有代价：重签发是"一次性、不可逆"
   的操作，界面必须让用户确认自己不是手滑点到）。

**实现**（在 `awaiting_human` 状态内自转，不经过状态机表）：

```python
    def reissue_resume_token(self, step_run_id, *, actor_ref, reason):
        token = secrets.token_urlsafe(32)
        with self.store.transaction():
            step = self.store.get_step_run(step_run_id)
            if step is None:
                raise MissingReference("StepRun 不存在: %s" % step_run_id, code="REF_001")
            if step["status"] != "awaiting_human":
                raise IllegalTransition(
                    "reissue_resume_token 只允许 awaiting_human 状态: %s 当前为 %s"
                    % (step_run_id, step["status"])
                )
            bound_version = step["status_version"] + 1
            self.store.update_step_run_status(
                step_run_id,
                "awaiting_human",
                "awaiting_human",
                step["status_version"],
                fields={"resume_token_hash": _token_hash(token, bound_version)},
            )
            self.store.append_step_run_event(
                step_run_id,
                "resume_token_reissued",
                actor_ref,
                from_status="awaiting_human",
                to_status="awaiting_human",
                reason=reason,
            )
            self.store.append_audit(
                "reissue_resume_token", str(step_run_id), actor_ref,
                json.dumps({"reason": reason}, sort_keys=True, ensure_ascii=False),
            )
        return token
```

（`store.update_step_run_status` 的 `WHERE status=from_status AND status_version=expected`
天然支持"同状态自转"，`from_status="awaiting_human", to_status="awaiting_human"`
不需要改 `store.py`；乐观锁保证并发下两次重签发不会互相踩。）

### 8.2 旧 token 立即作废、审计记录（已在上面实现里体现，逐条对应约束）

- **旧 token 立即作废**：新的 `resume_token_hash` 绑定 `bound_version = 旧 status_version+1`，
  旧 token 的哈希对应的是旧版本号；旧 token 再拿去调 `resume()`/`record_human_event()`时，
  `_check_token` 里 `bound_version != step["status_version"]` 这一条（`service.py:979-982`）
  会先失败（版本号不匹配），**旧 token 被拒**，不需要额外维护"黑名单"。
- **审计记录**：两处，都在同一事务里：
  1. `step_run_events` 表新增一行，`event_type="resume_token_reissued"`，
     `from_status=to_status="awaiting_human"`，`actor_ref` 为传入的用户身份，
     `reason` 为用户填写的理由——这条经 `list_step_run_events(step_run_id)`
     （已在 `LEDGER_PORT_METHODS` 闭集里）**可以经端口读到**，是给控制台界面显示
     "这次审核的恢复凭证历史"用的。
  2. `audit_log` 表新增一行（`append_audit`），`action="reissue_resume_token"`，
     `target=step_run_id`，`actor_ref` 同上，`payload_json` 里带 `reason`——这条和
     其余 `resume`/`suspend`/`recover` 一样**不经端口读**（`count_audit`/`append_audit`
     都不在 `LEDGER_PORT_METHODS` 闭集里），测试要验证它存在得像既有 ledger 测试那样
     直接用 `DirectLedgerAdapter(...).unwrap().store` 读（只在测试代码里这样做，
     生产代码仍然不允许，同 `legacy_self_driving` 经 `unwrap()` 的既有例外）。

### 8.3 重签发不改变已记录的决定

`reissue_resume_token` 只碰 `step_runs.resume_token_hash`/`status_version` 与新增的两条
事件/审计记录，**不触碰**任何 `human_event`、`artifact_revisions`、`checkpoints`——用户在
本次 `awaiting_human` 里已经通过 `record_category_ruling`/`record_decision` 登记过的决定
（哪怕只登记了一部分，还没 `resume`）原样保留，重签发后用户可以继续用新 token 把剩下的
决定登记完，再 `resume`。这是"重签发只换凭证、不影响已登记内容"的字面含义，`TDD.md`
`test_reissue_does_not_change_recorded_decisions` 要直接断言这一点。

### 8.4 界面触发方式（不得后台自动重签）

控制台后端**不得**在检测到内存映射里没有某个 `awaiting_human` StepRun 的 token 时自动调用
`reissue_resume_token`——那等于绕开用户做决定，违反 P7 的精神（这个操作本身不是"审核决定"，
但仍然是一次有实际后果的写账本操作，必须由用户主动触发）。设计的触发流程：

1. 用户刷新页面/重开浏览器，界面查到某个 EditionRun 停在 `awaiting_human` 但控制台内存
   映射里没有对应 token（S8 场景已覆盖这种查询）；
2. 界面显示"该阶段的恢复凭证已丢失（多半是后端重启），点击「恢复审核」重新获取"，
   **不自动弹窗、不自动请求**，等用户主动点击；
3. 用户点击后，界面弹出确认框，要求填写/确认 `reason`（可给默认文案，但要让用户看到并
   能改），并显示"这会让旧凭证失效"的提示；
4. 用户确认后，前端才发一次 HTTP 请求到控制台后端的"重签发"端点，后端据此调用
   `reissue_resume_token(step_run_id, actor_ref=<界面配置的用户身份>, reason=<用户填写>)`，
   把新 token 存进内存映射，界面刷新出"可以继续审核"的状态。

这段流程本身不是本次交付的代码，是 README §5（BDD）与 §7（要改的文件）里
`console_backend/app/orchestrator_client.py`/`routers/pipeline.py` 的一部分，本节只是把
"必须用户主动点击确认"这条硬性约束写清楚，供实现阶段直接抄。

### 8.5 与 §7.1 基线的关系

`orchestrator_client.py` 仍然要维护一个进程内存里的 `{step_run_id: resume_token}` 映射
（§7 已列），这个映射本身是否被序列化/写文件，是 §7.1 那条 `scan_ledger_internals` 回归
要盯住的东西之一（正则扫不到"写文件"这种操作，所以还需要 TDD.md 里
`test_resume_token_never_written_to_disk_or_log` 这条独立的按字节搜索测试，两者互补，
不能只依赖 `scan_ledger_internals`）。`reissue_resume_token` 返回的新 token 同样只能进
这个内存映射，不许落盘——**候选 B 解决的是"丢了怎么重新拿"，不是"允许存起来"**，
`resume_token` 不落盘这条铁律本身没有变。

### 8.6 规格登记（此入口属于规格变更，已获用户批准）

`reissue_resume_token` 扩展了 §17.1 人工暂停与恢复机制，不是实现细节，要登记进
`docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md` **§1.1「调用、
事务与人工恢复」表**（该表现在到"人工事件"一行为止，见 `INTERFACES.md:17-34`；本文档
读过该表，行号已核实：表头 `:19`，"人工事件"行 `:30`）。**由实现者在开工时新增一行**
（本文档不越权改动 impl-00 包的文件），格式仿"人工事件"那一行：

```
| resume_token 重签发 | `reissue_resume_token(step_run_id, *, actor_ref, reason)`；仅
  `awaiting_human` 状态合法；旧 token 立即作废（新哈希绑定新 status_version）；
  写 `step_run_events`（`event_type="resume_token_reissued"`）与 `audit_log`；
  不改变已登记的人工事件/决定；token 仍不落盘，只返回给调用方 | 【草案】T24 ACT
  01（本包）；用户 2026-09-26 裁决候选 B（README.md §8） |
```

`INTERFACES.md` 顶部状态行（`:3`）若因此需要提及新增内容，也由实现者按该包既有的更新
习惯（写变更摘要+日期）处理，本文档不代做。

## 9. console_backend 现有 2 个测试 error：根因、已验证过的修法排除、确切可用修法

```
export LC_ALL=C.UTF-8 && .venv/bin/python -m unittest discover -s console_backend/tests -t .
# Ran 6 tests in 0.001s
# FAILED (errors=2)
# ERROR: console_backend.tests.test_api_and_ws
# ERROR: console_backend.tests.test_workbench_api
```

两个失败都发生在 **import 阶段**（`from fastapi.testclient import TestClient`），根因是
`.venv`（`uv venv --python 3.14` → 实际装出 **Python 3.14.0rc2**；`pydantic==2.13.5`；
`fastapi==0.141.1`，均见 `requirements-dev.txt:9,21,22`）的版本组合不兼容：
`fastapi/openapi/models.py` 在模块加载时构造 `Contact` 这个 pydantic 模型（字段
`email: EmailStr | None = None`），pydantic 的 `_typing_extra.eval_type_backport`（或
2.14.0b2 里改名后的 `eval_type`）调用了 `typing._eval_type(..., prefer_fwd_module=True)`，
而 **Python 3.14.0rc2** 标准库里的 `typing._eval_type` 不接受这个关键字参数，抛
`TypeError: _eval_type() got an unexpected keyword argument 'prefer_fwd_module'`，
被 pydantic 自己的异常处理吞掉后重新抛出 `AssertionError`。这不是 console_backend 代码的
逻辑缺陷，是 Python 3.14 预发布版与 pydantic 之间一个已知形态的兼容性缺口。

### 9.1 已实测、确认无效或不可行的修法（避免实现者重复踩坑）

- **升级 pydantic 到 `2.14.0b2`（当前唯一比 2.13.5 新的可安装版本，稳定版里 `2.13.5` 已是最新）**：
  `uv pip install --python .venv/bin/python "pydantic==2.14.0b2"` 之后重跑同样的测试，
  **仍然报同一个根因**（`prefer_fwd_module` 这个 kwarg 依旧被传给 `typing._eval_type`），
  只是报错信息前多了一行 `Unable to evaluate type annotation str | None.`（已实测，2026-09-26）。
  **升级 pydantic 到目前能拿到的最新版本不能解决这个问题**，不要在这个方向上重复尝试。
- **降级 pydantic 到 `2.10.6`**（更早、不含这段兼容代码的版本）：`uv pip install` 会去装配套的
  `pydantic-core==2.27.2`，但该版本在 PyPI 上**没有 Python 3.14 的预编译 wheel**，`uv` 会本地用
  `maturin`/`cargo` 从源码编译，实测**编译失败**（`command ['maturin', 'pep517', 'build-wheel', ...]
  returned non-zero exit status 1`）。降级路线在当前环境不可行（除非另外装 Rust 工具链并接受
  长编译时间，价值不高，不推荐）。

### 9.2 确切可用的修法（已实测通过）

**根因是 CPython 3.14.0rc2（预发布版）标准库 `typing` 模块缺一个 pydantic 期望存在的参数，
不是 pydantic 版本选得不对**。本机已经装有 **Python 3.13.12**（`/usr/bin/python3.13`，
`uv python list` 可见），用它建一个独立的 venv、装同一份 `requirements-dev.txt`，
`console_backend` 的两个测试模块 import 正常，全部测试通过：

```bash
cd /home/user/learn_system_dataset/.claude/worktrees/agent-a5cf1bfd2b8d5baa0
uv venv .venv-py313 --python 3.13.12
uv pip install --python .venv-py313/bin/python -r requirements-dev.txt
export LC_ALL=C.UTF-8
.venv-py313/bin/python -m unittest discover -s console_backend/tests -t .
# 实测输出：Ran 22 tests in 0.297s / OK
```

（"Ran 6 tests"→"Ran 22 tests"的差异是因为原来两个模块 import 失败时，`unittest` 只能把
每个失败模块记成一个占位的 `_FailedTest`，真正能收集到的用例数远少于模块内实际的测试方法数；
import 成功后才收集到全部 22 个真实用例。）

**建议做法**：不动 `pydantic`/`fastapi` 的版本锁定（`requirements-dev.txt` 不改），只是给
`console_backend` 的测试运行**换一个 Python 解释器版本**（3.13.12 而非 3.14.0rc2）。
具体落地方式留给实现者按仓库惯例二选一，写进回报里说明选了哪个：
- (a) 只给 `console_backend/tests` 单独维护一个 `.venv-console`（3.13），11 个 pipeline 包仍用
  现有 `.venv`（3.14），两套环境并存，`TDD.md`/CI 脚本分别指向各自的解释器；
- (b) 或者验证 11 个 pipeline 包在 Python 3.13.12 下全绿后，把整仓库的 `tools/jules_setup.sh`
  改成装 3.13（**本次未验证 11 个包在 3.13 下是否全绿，不能预先断言可行**，这一步本身要按
  "先跑一次基线、记录结果"来做，不能想当然）。

**这个问题独立于 T24 的设计工作，但会挡住 T24 实现阶段"先写测试红后绿"的第一步**，因此把它列为
`act/01.yaml` 的**前置修复步骤（第一步）**：实现者开工前先按上面命令验证通过，再开始写
TDD.md 第 1 节的新测试；这属于环境/依赖版本问题，修复它不算违反"不改 pipeline/ 下生产代码"
（`requirements-dev.txt` 与 venv 解释器版本都不是 `pipeline/` 下的生产代码）。

## 10. 实现者开工前必须先做的核实清单

本文档所依据的分支状态已经是合并后的 `6a06144`（本 worktree 当前 HEAD 的父提交之一）；
下面几条是**实现者在自己实际开工的那次会话/分支上**要重新确认的，因为不能保证实现者拿到的
分支就是原封不动的 `6a06144`（可能又有新提交、可能是另一次从 main 或别的地方开的 worktree）：

1. 确认自己所在分支包含本文档第 0 节列出的全部签名/行号（一条条重新 `grep`/`Read` 核对一遍，
   不要假设"文档写了就是对的"）；不一致就先按实际签名更新本文档，再动代码。
2. 按 §9.2 的确切命令先修好 `console_backend` 的测试环境（Python 3.13.12 起独立 venv），
   确认 `.venv-py313/bin/python -m unittest discover -s console_backend/tests -t .` → `OK`
   之后才开始写 TDD.md 第 1 节的新测试；对这一步本身做一次篡改探针（例如临时把
   `.venv-py313` 换回指向 3.14 的解释器，观察测试是否变回同样的 2 个 error，然后改回）。
3. resume_token 已裁决候选 B（§8）：先落地 `reissue_resume_token`（§8.1，`act/01.yaml`
   已排在"接 M4/M6 审核"之前作为独立步骤），跑绿 TDD.md 里对应的 ledger 层测试，再接
   `console_backend` 的触发端点；不要跳过 ledger 层直接在 `orchestrator_client.py` 里
   自己发明"重签发"逻辑（那会绕开 `LedgerPort` 的闭集机制，违反第一条硬约束）。
4. 重跑一次 §7.1 的 `scan_ledger_internals(["console_backend"])` 作为自己那次改动前的基线
   （预期仍是 `[]`，因为改造前 `console_backend` 还没接 Ledger）；每接入一块新代码
   （尤其是 `orchestrator_client.py`）就重跑一次，确保接入后仍然是 `[]`，并补一条
   `pipeline/contract_registry/tests/` 下的回归用例把这个检查钉住（§7.1 已说明原因）。
5. 按 §8.6 在 `INTERFACES.md` §1.1 补登记 `reissue_resume_token` 那一行。

## 11. 完成判据（对齐 act/01.yaml，汇总）

- 控制台能从上传一本电子文本起，经公开入口驱动一次 EditionRun 跑到 M8，可下载发布包；
- M4/M6 决定均在界面完成，`actor_ref` 来自用户配置，不存在任何自动/代签路径；
- M4/M6 页面能显示已上传的 AI 预审建议（若有），采纳与否都不影响"必须用户点击提交才算决定"；
- `scan_ledger_internals(console_backend)` 为空；
- resume_token 不落盘（有测试按字节搜索证明）；后端重启丢失 token 后，用户可在界面点击
  「恢复审核」经 `reissue_resume_token`（候选 B，§8）重新获得凭证续跑，全程不自动重签；
- 刷新/重开浏览器能看到当前停在哪一步；
- 任一阶段失败时界面如实显示失败原因；
- `reissue_resume_token` 已登记进 `INTERFACES.md` §1.1（§8.6）。
