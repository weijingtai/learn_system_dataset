# NC-002 执行提示

发送前提：wjt-react 四查判定 READY，且主线程已在 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你在 `/Users/jingtaiwei/Git/Public/learn_system`（act/01～05）与 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`（act/06）执行 NC-002。其他 Agent 在 learn_system 同一工作树并行工作，不要回退、暂存或提交任何不属于你的改动。

**先读（按顺序）**：`AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-002/` 下的 README.md、BDD.md、TDD.md、ACT.yaml、act/01～06.yaml、ACCEPTANCE.md；`openspec/annotation-community/contracts/community-models.md`、`contracts/state-machines.md`；`openspec/annotation-community/fixtures/community/` 全部 9 个文件；`openspec/schemas/verify.sh` 与 `openspec/schemas/artifact_ref.schema.json`（写法参考）。

**先写测试再改实现**：每一步必须先写本步的示例/测试并取得真实 Red（原文保存），再写 Schema/实现。先实现后补测试即违反流程，须在报告中如实写明；主 Agent 会核对提交内的文件时序。

**只允许写**：各 ACT 的 WRITE_NEW / WRITE 清单。`openspec/schemas/verify.sh` 全程不改（决定 D-NC002-11）；社区 Schema 只用 `openspec/schemas/verify_community.sh` 校验。允许且仅允许新建文件，不新建目录（`openspec/schemas/examples/`、`tools/`、SERVER `tests/fixtures/` 均已存在）。

**禁止**：修改契约、fixture、参考编码器 `tools/nchash_reference.py`、本工作包、四份规格、既有守卫、既有 Schema 与示例、PLAN/HANDOFF/SUBAGENT_TODO；读取或 import 参考编码器代码；安装依赖（含 pytest）、创建 venv、连网、连 Emulator；写入 xuan-migration；SERVER 除三个新建文件外任何改动。

**判据来源**：字段、枚举、正则、限额只来自两份契约；期望值只来自 fixture 与 TDD。契约有两种以上解释、fixture 与契约矛盾、需要写白名单外文件、check-jsonschema 不可用：立即停止并原样报告，不自行裁定。

**共享守卫**：`review_v1_5_guard.sh`、`openspec/annotation-community/verify.sh`、`git diff --check`、`nc002_guard.sh` 的 K01 读取共享工作树，并行线可能让它们失败。失败时先 `git diff --stat`；失败来源不在你的白名单文件之内的，判为外部失败，写进报告即可，不返工、不停工。`nc002_guard.sh` 的 K02～K08 失败仍按本任务失败停工。

**提交**：learn_system 五步各一个提交，SERVER 一个提交（不 push），只 `git add` 本步 WRITE_NEW 文件。提交消息按各 ACT 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。`git commit` 因 index.lock 失败则等 10 秒重试一次，再失败即停。

**交付报告**（每步一节）：
1. commit 哈希、仓库与 `git show --stat` 原文；
2. Red：命令、退出码、失败原文；
3. Green：该 ACT VERIFICATION 每条命令的退出码与输出末 20 行；
4. act/06 另附：`python3 -m unittest tests.test_community_hash_parity -v` 全文（Ran 8 tests）、`cmp` 退出码、`nc002_guard.sh --require-impl` 退出码；
5. 跳过项、未运行项、外部失败记录与剩余风险。

不要把本任务说成 NC-002 总项完成：CLIENT 的 Dart 一致性测试推迟到 NC-004，CommandRecord 按操作的成对 Schema 推迟到 NC-003。
