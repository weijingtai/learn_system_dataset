## 背景（T04 两份派单共用）

目标：learn_system 的 M1→M8 由**调度器**（`pipeline/orchestrator/`）连成一条线。一个 EditionPart 从 M1 自动推进到 M6（EditionRun），
再经发布段 M7→M8（ReleaseRun）产出 PublicationPackage。遇到规格规定的人工节点（M4 提交、M6 审核、M7 裁决）就以 `awaiting_human` 暂停，
经人工接口（`pipeline/orchestrator/human.py` 的 record_human_event / resume）处理后自动续跑。**除这些节点外不需要任何手动推进。**

主 Agent 2026-09-23 实查（HEAD d44f4e2，11 个包全绿）：
- 登记表 `pipeline/contract_registry/registry.yaml`：M1、M2 是 `thin_import`（从 fixture 导入顶替，不是生产模块）；M3/M5/M8 是生产模块（`binding: legacy_self_driving`）；**M4、M6、M7 没登记**；M8 的 `consumes` 不含 M7。
- 调度器 `pipeline/orchestrator/__init__.py`：`EDITION_STAGES=(m1..m6)`、`FIRST_SLICE_EDITION_STAGES=(m1,m2,m3,m5)`、`RELEASE_STAGES=(m8,)`、`DEFERRED_STAGES=(m4,m6,m7)`。
  推进在 `edition_run.py`（`advance` / `run_release` / `run_until`），模块绑定在 `module.py`（`bind_module`，binding 闭集 imported / step_request / legacy_self_driving），人工在 `human.py`。
- 各阶段生产入口都已存在：`intake/step.py:run_m1`、`digitization/step.py:run_m2`、`corpus_compiler/step.py:run_m3`（电子文本路线另有 `step_offset.py:run_m3_text`）、
  `knowledge_extraction/step.py:run_m4`（另有 `submit.py:run_m4_submit`）、`validation/step.py:run_m5`、`review/step.py:run_m6`、`assembly/step.py:run_m7`、`dataset_compiler/step.py:run_m8`。
- 真书账本 `var/ledgers/qianyuan_w8/`（**只读，任何写入都在副本上做**）：M1–M6 是手动逐段推进的，M4 人工事件 24 条、M6 26 条，M6 有 1 次停在 awaiting_human；**M7、M8 从未在真书上跑过**。
- 登记表有一致性校验（`contract_registry` 的 `check_registry`；同一 stage 两个非桩 Module 会 `RegistryInvalid`）。验收：`bash openspec/acceptance/run_all.sh 20.1`（现 BLOCKED）、`20.2`（现 PASS，不许退步）。

### 纪律

1. 先读相关代码与测试再动手；**先写测试确认转红（贴 Red 原文），再实现**。
2. 只改派单写明的范围；越界需要改的，停手写「## 待裁决」。
3. 真书账本只读；实跑一律在 `cp -R` 的副本上。
4. 不许为了让线跑通而放宽任何 Gate / 验收判据；不许把人工节点改成自动放行。
5. 某阶段的入口参数调度器给不了（例如 M1 需要源文件清单），**不要硬编码真书路径**——设计成由 EditionRun 的配置传入，并在回报里说明。
6. `export LC_ALL=en_US.UTF-8`；corpus_compiler 测试中间几行 `FAIL m3_acceptance` 是已知噪声，以最后一行 OK 为准。
7. 不许 push、不许删分支、不许动 `var/`。
8. **每做完一步就在回报里追加**（做了什么、测试输出）。只有标题视为未完成。拿不准就停手写「## 待裁决」。
