# T04A 裁决（主 Agent 2026-09-23）

你的 4 条待裁决都问在点子上，证据我核过属实。裁定如下，按此实现，一次做完并提交。
读完后先把本文件的裁定摘要追加进回报 `/Users/jingtaiwei/tmux-agents/runs/t04a.report.md` 的「## 待裁决」下（标题改为「## 待裁决（已裁，见裁决 1）」），然后开工。

## 裁决 1：选 (a) —— M1/M2 模块自己登记 StagePackage

理由：M3–M8 都是模块自己登记包；在调度器里替模块合成包，等于调度器替模块伪造产出，这正是我们要消灭的「桩」。
- 授权改 `pipeline/intake/step.py`、`pipeline/digitization/step.py`：**只许在末尾追加登记 StagePackage**（包清单列本步实际写出的修订），不改入口签名、不改既有产出的内容与顺序。
- validation_report 只写模块**实际做过**的检查（M1：清单/哈希核对；M2：sanitization_report 的结论）。模块没做过的检查不许编进报告。
- M1、M2 既有用例必须保持全绿；新增用例：`test_run_m1_registers_stage_package`、`test_run_m2_registers_stage_package`（断言恰 1 个包、包内修订号等于本步写出的修订）。
- 真书账本正本只读，不回填旧 StepRun 的包。

## 裁决 2：生产登记表只登记电子文本路线；路线在运行输入里显式声明

登记表一个 stage 只能有一个 Module（`catalog.module_for` 多于 1 个即 ID_002），且 OCR 路线的 M2 **没有生产模块**，所以：
- m1 → intake 的薄适配；m2 → `digitization.run_m2` 的薄适配；**m3 条目授权改为 `run_m3_text`**（经薄适配）。
- EditionRun 的运行输入里必须显式写 `route: text`。`route` 缺失或不是 `text` → 调度器拒收，理由写「OCR 路线 M2 无生产模块（TODO T04c）」。**不许按「有没有某种产物」去猜路线。**
- 删除 `m1.fixture_import`、`m2.fixture_import` 两个条目。直接走 `fixture_ingest` 的其他测试（不经调度器的）不动。
- 我会在 TODO.md 新增 T04c「OCR 路线 M2 生产模块」，你不用管。

## 裁决 3：你的拟方案采纳，加一条硬约束

1、2、3 条全部采纳（`run_inputs` 落成运行级 configuration 修订；描述符加 `resume_entry`；`run_legacy` 接受 `awaiting_human` 终态）。
**硬约束：`resume_token` 只以内存返回值交给调用方，绝不写进 ledger、configuration、日志、report 或任何文件。**
- 新增用例 `test_resume_token_never_persisted`：跑到 m4 暂停后，把 `ledger.sqlite` 与 `objects/` 下全部文件按字节搜 token 明文，必须 0 命中。
- `human.resume` 在 `legacy_self_driving` 下走 `resume_entry`；`step_request` 的旧路径不许变。

## 裁决 4：授权改 20.1 的宿主与判据，但只许收紧、不许放宽

- 宿主换成 `pipeline/corpus/_fixture/qianyuan_ed01_text/`；`_check_real_chain` 改写为 **M1→M6 全线**：`route: text`，调度器 `run_until(..., "m6")`。
- 判据（全部要成立）：
  1. m1..m6 每个 stage **恰 1 个**阶段包，且来自生产模块（binding 不是 `imported`）
  2. 只在 m4、m6 两处停成 `awaiting_human`；除这两处外**不许**有任何手工推进
  3. 人工环节只能走公开入口：M4 的提交用 fixture `m4/submission_*.yaml`，经 M4 公开提交入口交进去；M6 的签发经审核台（`review/console.py`）公开 API 逐条操作。**不许直接写 ledger 伪造人工结果，不许手写金标。**
  4. 恢复经 `human.resume` → `resume_entry`，之后调度器自动续跑到 m6 succeeded
- `_check_registered_modules`：m4/m6 登记后按真实登记情况判，不再写死 BLOCKED。
- `run_all.sh`：**只许改 20.1 这一段**，探针改读新宿主；其余各项一字不动。
- 如果 fixture 里的 M4 提交或 M6 的操作步骤不足以把线走完（缺数据），**停手写待裁决**，不许为凑通过去造数据。

## 不变的纪律

- 先写测试确认转红（贴 Red 原文），再实现。
- 不许放宽任何 Gate / 验收判据；不许碰 `learn_system-wt-t04b` 与 M7/M8 文件。
- 每完成一步往回报「## 步骤记录」追加一段；至少每 15 分钟更新一次。
- 全部完成后：跑 11 个包全套 + `bash openspec/acceptance/run_all.sh 20.1` 贴全文，提交，回报末尾写一行「完成：<提交号>」。
- 额度快到时先把进度写进回报再停。
