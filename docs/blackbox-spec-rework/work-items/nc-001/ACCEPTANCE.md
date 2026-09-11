# NC-001-01 独立验收

当前：NC-001-01 `ACCEPTED`（2026-09-10，主 Agent 亲自验收，记录见文末）。整项 NC-001 的十项要求未关闭，总项仍 `PREPARING`。

1. ACT审查先核忠实性/覆盖性/可执行性/独立性；原任务本地/完整范围差异必须引用基线§6，不得悄悄降低总项标准。按 wjt-react 要求由符合独立性规则的审查者给出结论，本文不自签 READY。
2. 核对 act/01～act/04 四个提交合计只涉及两个工具文件，输入与旧门禁无diff；外部仓库无本任务改动。
3. 重跑TDD全部命令。命令1需发现并运行 TDD §3 列出的全部 32 个方法，且测试文件的 `REQUIRED_KEY_PATHS` 与 TDD §3.1 的 103 条逐字一致；命令2退出0且 stdout 恰为 `LOCAL_PREPARATION_PASS`；命令3退出1且 stdout 与 VALIDATION_CONTRACT §7 的 23 行逐字相同，这是必须保留的负例；`bash docs/blackbox-spec-rework/reviews/nc001_r2_guard.sh --require-impl` 退出 0。逐条捕获退出码，不以一串命令末条成功掩盖前面失败。`review_v1_5_guard.sh`、`verify.sh`、`git diff --check` 与 `nc001_r2_guard.sh` 的 K01 若因并行 G3 线的共享文件改动而失败，按外部失败记录，不计入本任务失败；判定依据是 `git diff --stat` 显示失败源不在两个工具文件之内。
4. 抽验至少三个变异：EXISTING指向空目录、PASSED却无测试证据、丢失一个联调前置。每个应非零，且不改文件。完整临时fixture可过只说明结构，不是真设备证明。
5. 核查没有skip/永真/空断言/从被测输出生成预期；status含义明确，local不泄漏为runtime_ready。
6. 独立语义审查通过后只验收NC-001-01；NC-001-02的设备/后端/真实测试缺证继续保留，不解锁需要完整集成的任务。

证据记录格式：commit；实际文件；每条command/exit_code/原始摘要；Red失败断言；变异案例输出；跳过项与剩余阻塞。主线程负责G6/PLAN/HANDOFF更新，执行者不修改。

Terra同厂商证据快审：已核本地版本/身份决定；指出外部HEAD停点超出READ范围，现改为输入基线HEAD字段变化并限定外部路径只读存在性。此快审不替代独立wjt-react，不给READY。

## v1.5 复核补充

核对 VALIDATION_CONTRACT.md 与 JSON、BDD B01～B23、TDD §3 的 32 个方法及 act/01～act/04 的读写范围闭合。R2 返工项与裁定见 `reviews/NC-001-REVIEW-R2.md`。当前输入 account_deletion.status=UNVERIFIED，local 可通过但 integrated 必须拒绝；将状态单独改成 VERIFIED 仍须拒绝。注销缺证只保留对应子项阻塞，不把它扩大为笔记本地工作全部停止。

## 验收记录（NC-001-01，2026-09-10，主 Agent C/S 会话）

- 执行提交（均只含两个工具文件，`git show --name-only` 逐一核对）：`272fb60` CLI 与顶层规则 → `11b4e46` 对象规则（一）→ `d75afb1` 对象规则（二）→ `11edbc7` integrated 档。
- 范围：`git diff --stat e64f2a4 11edbc7` 对输入 JSON/MD、四份规格、既有守卫、工作包、reviews 均为空；四个外部仓库 `git status` 为空；`reading-notes` 未被创建。
- 命令与退出码（`LC_ALL=en_US.UTF-8`）：命令 1 `Ran 32 tests OK` 退出 0；命令 2 退出 0、stdout 恰为 `LOCAL_PREPARATION_PASS`；命令 3 退出 1、stdout 与契约 §7 逐字 diff 为空（23 行）；`nc001_r2_guard.sh --require-impl` 退出 0（K01～K11 全 PASS）；`git diff --check` 0。
- 测试结构：方法集合与 TDD §3 的 32 个完全相等；`REQUIRED_KEY_PATHS` 用 AST 解析为 103 条、与 TDD §3.1 集合相等；23 行金标准与完整夹具取值为字面量；无 skip / assertTrue(True) / expectedFailure / except-pass；夹具为每个证据字段建独立文件。校验器只 `read_text` 输入 JSON 与 `INTEGRATION_BASELINE.md`，无 subprocess、网络、写文件。
- 第 4 条变异（临时副本，运行前后目录与哈希不变）：EXISTING 指向空目录 → 退出 1 `client.path`；STORAGE tests 改 PASSED 无证据（integrated）→ 含 `.command/.count/.evidence/.exit_code` 四行；删除 `integration.emulator` → 退出 1 `integration.emulator`。
- 矩阵外盲测 17 例全部符合契约：head 大写 hex、符号含冒号行号、schema_version 布尔、根为数组（`root`）、仓库重复、dependencies 多键、MD 含「待定」、integrated 半填 rules.path（同时报 path 与 status）、NOTIFIER 允许写、local TEST_FIXTURE 后缀、JSON 语法错误（退出 2、stdout 空）、未知 profile（退出 2）、client 为数组只报 `client`、account_deletion 半填、dirty_entries=-1、scope 注入 form-feed（报 `scope`）、未改动副本通过。真实输入运行前后哈希不变。
- 执行方自报的流程偏差：第 4 步先写了 §4/§5 实现再补测试，随后临时还原校验器至第 3 步提交内容取得真实 Red 后再恢复。交付物不受影响，Red 证据为事后构造，记录在案；下一工作包 PROMPT 明确「先写测试再改实现，违反即停」。
- 结论：NC-001-01 `ACCEPTED`。NC-001 总项保持 `PREPARING`，等 NC-001-02 真实联调取证（设备、后端、Emulator、真实测试、注销事件）；Firebase 去留须在此之前由用户决定。
