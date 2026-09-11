# NC-001-01 独立验收

当前：NOT_EXECUTED。整项 NC-001 的十项要求未关闭。

1. ACT审查先核忠实性/覆盖性/可执行性/独立性；原任务本地/完整范围差异必须引用基线§6，不得悄悄降低总项标准。按 wjt-react 要求由符合独立性规则的审查者给出结论，本文不自签 READY。
2. 核对 act/01～act/04 四个提交合计只涉及两个工具文件，输入与旧门禁无diff；外部仓库无本任务改动。
3. 重跑TDD全部命令。命令1需发现并运行 TDD §3 列出的全部 31 个方法，且测试文件的 `REQUIRED_KEY_PATHS` 与 TDD §3.1 的 103 条逐字一致；命令2退出0且 stdout 恰为 `LOCAL_PREPARATION_PASS`；命令3退出1且 stdout 与 VALIDATION_CONTRACT §7 的 23 行逐字相同，这是必须保留的负例；`bash docs/blackbox-spec-rework/reviews/nc001_r2_guard.sh --require-impl` 退出 0。逐条捕获退出码，不以一串命令末条成功掩盖前面失败。
4. 抽验至少三个变异：EXISTING指向空目录、PASSED却无测试证据、丢失一个联调前置。每个应非零，且不改文件。完整临时fixture可过只说明结构，不是真设备证明。
5. 核查没有skip/永真/空断言/从被测输出生成预期；status含义明确，local不泄漏为runtime_ready。
6. 独立语义审查通过后只验收NC-001-01；NC-001-02的设备/后端/真实测试缺证继续保留，不解锁需要完整集成的任务。

证据记录格式：commit；实际文件；每条command/exit_code/原始摘要；Red失败断言；变异案例输出；跳过项与剩余阻塞。主线程负责G6/PLAN/HANDOFF更新，执行者不修改。

Terra同厂商证据快审：已核本地版本/身份决定；指出外部HEAD停点超出READ范围，现改为输入基线HEAD字段变化并限定外部路径只读存在性。此快审不替代独立wjt-react，不给READY。

## v1.5 复核补充

核对 VALIDATION_CONTRACT.md 与 JSON、BDD B01～B22、TDD §3 的 31 个方法及 act/01～act/04 的读写范围闭合。R2 返工项与裁定见 `reviews/NC-001-REVIEW-R2.md`。当前输入 account_deletion.status=UNVERIFIED，local 可通过但 integrated 必须拒绝；将状态单独改成 VERIFIED 仍须拒绝。注销缺证只保留对应子项阻塞，不把它扩大为笔记本地工作全部停止。
