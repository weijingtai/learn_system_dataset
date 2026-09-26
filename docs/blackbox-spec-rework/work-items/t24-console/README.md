# T24：Web 控制台接真流程 —— 工作文档（README）

状态：**只完成本文档（含 TDD.md、act/01.yaml、PRD 作废标注），未写实现代码**。范围收窄见文末「本轮范围」。
实现将由用户本机的外部 agent 按本文档独立执行；本文档要写到它不需要再回来问设计问题。

## 0. 前置阻断（写在最前面，因为它挡住一切实现）

**本 worktree 所在分支（`worktree-agent-a5cf1bfd2b8d5baa0`，基于 `main`）没有 T04 的产出。**
`main` 上 `pipeline/orchestrator/edition_run.py` 的 `start_edition_run(port, *, edition_part_id, technique_id)`
不接受 `run_inputs`（无 `route: text`）；`advance()`、`run_release()` 的签名也和
`docs/handoff/ASK-2026-09-26.reply.md`、`pipeline/tools/run_real_book_t04.py` 里描述的不一样；
`pipeline/contract_registry/registry.yaml` 里 m4/m6/m7 的登记与 `resume_entry` 机制在本分支不存在。

这些东西存在于另一条分支 **`claude/wizardly-maxwell-pqrzh9`**（本地已有该 ref，未合并进
`main`，与本分支在 `f4df613` 分叉，各自往下走了不同的提交；两分支互不包含对方全部提交）。
`TODO.md` 里 T24 这一条本身也只在 `claude/wizardly-maxwell-pqrzh9` 的 `TODO.md`（`f8d0d44`）里，
本分支的 `TODO.md` 停在 T19。

**结论：T24 的实现动不了，直到人类决定这两条分支怎么合。** 本文档按
`claude/wizardly-maxwell-pqrzh9` 上已经存在的公开入口（`run_real_book_t04.py` 的调用序列）来写
设计，是因为那是当前唯一「M1→M8 真的连通过一次」的证据；但实现者接手时的第一件事，
必须是确认自己所在分支上这些入口是否存在、签名是否与本文档一致——不一致就停手，不要自己改公开
入口的签名来凑。

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
Then 后端调用 run_release(adapter, registry, edition_part_id=..., technique_id=...)（**注意**：本分支
   与 claude/wizardly-maxwell-pqrzh9 的 run_release 签名不同，实现者要先核实自己分支上的真实签名，
   见第 0 节）
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
 And 若该 EditionRun 停在 awaiting_human 但后端进程已重启（resume_token 已丢失，见第 8 节待裁决），
   界面如实提示"该阶段需要重新获取恢复凭证，当前无法从界面直接续跑"，不假装能继续
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
（本文档设计的调用顺序**以它为基准**，实现时先核对自己分支上的真实签名，见第 0 节与第 10 节）：

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
  与"采纳建议"交互（S9/S10）。
- `pipeline/contract_registry` 下 `scan_ledger_internals` 对 `console_backend` 的扫描范围要覆盖
  新代码（若该函数按目录扫描则自动覆盖，需实现者核实）。

## 8. resume_token 与后端重启问题（调查结论）

已读代码（本分支 `pipeline/orchestrator/human.py`、`pipeline/ledger/store.py`）：

- `resume_token` 只在"running → awaiting_human"转换那一刻生成一次，返回给调用方；
  Ledger **只存它的哈希**（`resume_token_hash = "v<status_version>:<sha256(token)>"`），
  明文从不落盘（`store.py` 第 97、100、958-981 行）。这是有意设计，不是缺口。
- `claude/wizardly-maxwell-pqrzh9` 的交接文档（`docs/handoff/CLOUD-HANDOFF.md`、`t04a-ruling1.md`、
  `t04a.report.md`）提到的 `resume_entry`，是**登记表描述符的一个字段**（如 m4 → 
  `pipeline.knowledge_extraction.step:resume_m4`），用来告诉 `human.resume` 在 `mode="resumed"`
  时应该调用哪个模块函数——**它解决的是"resume 时该跑哪段代码"，不是"token 丢了怎么办"**。
  两者是完全不同的问题，不要混淆。
- 没有找到任何公开入口可以在 token 丢失后重新拿到它或让 Ledger 重新签发一个（`recover()`
  能把状态对回 `awaiting_human` 但不返回新 token；`rerun_from_checkpoint` 是给 `failed/suspended`
  用的，不是给 `awaiting_human` 用的）。

**结论：待裁决。** 没有公开途径能在控制台后端进程重启后重新获得已丢失的 `resume_token`。
按 ACT 19 铁律，本文档遵照第 3 条硬性约束"resume_token 只存进程内存，不许落盘"，
**这意味着后端重启后，任何已停在 awaiting_human 但尚未 resume 的 EditionRun，界面只能显示
"停在 M4/M6，需要重新获取恢复凭证"，无法自行续跑**，直到人类在下列候选里选一个：

- 候选 A：不改账本，允许控制台进程内**持久化到本地磁盘文件**（非 Ledger）保存
  `{step_run_id: resume_token}`，用文件权限而非 Ledger 完整性来保护；风险：违反本任务书
  第 3 条"resume_token 不许落盘"的字面约束，需要用户重新裁决这条约束是否允许"控制台自己的
  本地文件"这种例外。
- 候选 B：给 Ledger 新增一个公开入口，允许在 `awaiting_human` 状态下**重新签发**一个新
  `resume_token`（旧哈希失效、换新哈希），代价是要改 `pipeline/ledger`（生产代码），
  违反本任务第 7 条"不改 pipeline/ 下生产代码"，需要单独裁决是否破例。
  好处是不违反"不许落盘"。
- 候选 C：约束运维流程——控制台进程常驻不重启（容器/进程管理器保活），把"后端重启丢 token"
  当作已知运维风险而非产品问题；配合 S8 场景里"如实提示，不假装能继续"。这是本文档默认采用的
  展示行为，但不解决"万一真的重启了"的恢复问题。

本文档不擅自选定，写在这里等人类裁决；实现者在开工前应先确认是否已有裁决，没有裁决就先按候选 C
的展示行为实现（如实提示），不要自己发明落盘方案。

## 9. console_backend 现有 2 个测试 error 的原因（已查明，非代码逻辑 bug）

```
export LC_ALL=C.UTF-8 && .venv/bin/python -m unittest discover -s console_backend/tests -t .
# Ran 6 tests ... FAILED (errors=2)
# ERROR: console_backend.tests.test_api_and_ws
# ERROR: console_backend.tests.test_workbench_api
```

两个失败都发生在 **import 阶段**（`from fastapi.testclient import TestClient`），根因是
本机 `.venv`（Python 3.14.0rc2 + `pydantic==2.13.5` + `fastapi==0.141.1`）的版本组合不兼容：
`fastapi/openapi/models.py` 在模块加载时构造 `Contact` 这个 pydantic 模型，pydantic 的
`_typing_extra.eval_type_backport` 调用了 `typing._eval_type(..., prefer_fwd_module=True)`，
而 Python 3.14.0rc2 的标准库 `typing._eval_type` 不接受这个关键字参数，最终抛
`TypeError: _eval_type() got an unexpected keyword argument 'prefer_fwd_module'`，
被 pydantic 自己的异常处理吞掉后重新抛出 `AssertionError`。

这**不是 console_backend 代码的逻辑缺陷**，是环境里 pydantic 与 Python 3.14 之间的兼容性问题，
任何 import `fastapi` 的测试模块在这套环境下都会这样错。修法候选（本次不做，留给实现者或
`tools/jules_setup.sh` 的维护者裁定，因为这属于环境/依赖版本，不属于本文档"只写文档"的范围）：
- 升级/降级 `pydantic`（或连带 `fastapi`）到一个与 Python 3.14.0rc2 兼容的版本组合，
  重新锁定 `console_backend/requirements*.txt`（若有）或 `tools/jules_setup.sh` 里的版本；
- 或者等 Python 3.14 出正式版、pydantic 出适配版本后再验证。
**这个问题独立于 T24 的设计工作，但会挡住 T24 实现阶段"先写测试红后绿"的第一步**
（因为新写的 console_backend 测试大概率也要 `from fastapi.testclient import TestClient`）。
实现者开工前应先确认这个环境问题是否已被别的会话修过；没修过就先修（不算违反"不改
pipeline/ 生产代码"，这是环境依赖版本，不是 pipeline 代码）。

## 10. 实现者开工前必须先做的核实清单

1. 确认本 worktree/分支是否已经合并/rebase 了 `claude/wizardly-maxwell-pqrzh9` 的 T04 相关提交
   （或人类已经决定了别的合并方案）；没有就先停手上报，不要自己 merge/rebase 到 main
   （铁律 2、4）。
2. 在自己真正要跑的分支上，重新读一遍 `pipeline/orchestrator/edition_run.py`、
   `pipeline/orchestrator/human.py`、`pipeline/knowledge_extraction/step.py`、
   `pipeline/review/step.py` 的公开函数签名，逐一核对本文档第 6 节的调用序列——签名不同就
   按实际签名改文档（先改文档再写代码），不要靠猜。
3. 确认 §9 的环境问题是否仍然存在；仍存在就先修，按"先写测试确认红，再修，再确认绿"的顺序，
   并做一次篡改探针（如临时把 pydantic 版本改错再改回，观察测试红绿）。
4. 确认 §8 的 resume_token 落盘问题是否已有裁决；没有就按候选 C 的展示行为实现，不要自创方案。
5. 跑一次 `pipeline.contract_registry` 的 `scan_ledger_internals`（或等价扫描）针对
   `console_backend`，作为改造前基线记录下来（预期非空，因为现在整个 repository.py 都在绕开
   LedgerPort）。

## 11. 完成判据（对齐 act/01.yaml，汇总）

- 控制台能从上传一本电子文本起，经公开入口驱动一次 EditionRun 跑到 M8，可下载发布包；
- M4/M6 决定均在界面完成，`actor_ref` 来自用户配置，不存在任何自动/代签路径；
- M4/M6 页面能显示已上传的 AI 预审建议（若有），采纳与否都不影响"必须用户点击提交才算决定"；
- `scan_ledger_internals(console_backend)` 为空；
- resume_token 不落盘（有测试按字节搜索证明）；
- 刷新/重开浏览器能看到当前停在哪一步；
- 任一阶段失败时界面如实显示失败原因。
