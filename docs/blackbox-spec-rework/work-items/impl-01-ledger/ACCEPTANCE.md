# ACCEPTANCE：impl-01 Artifact Ledger

状态：`ACCEPTED`（2026-09-11）。H1 `ba9b68e`/`823bead`/`0dff35d`；H2 `401b449`/`01d32ca`/`45d99a1`；返工 ACT 06 `c939575`。见 §5

## 0. 转译审查（主 Agent 四查，2026-09-11）

- 忠实性：ACT 01 常量逐字取自规格 §8.1 三表与 §8.2 四表；ACT 03 方法覆盖 §7.1（await/record_human_event/resume、token 单次、无自动超时）、§17（事务序列九步、suspended/recovery 对账、ActorProvider、必记字段）、§17.1（Checkpoint 五条）；ACT 04 对应 D-04 决议（单机本地进程、单写入者、WAL、只读并发）；ACT 05 的 20.2/20.3 判据严格对应 §20 第 2/3 条原文；无新前缀。
- 覆盖性：BDD 1–6 每条对应 ACT `tests` 用例名与 TDD §1 Green 值；假绿由 TDD §2 的篡改/恒真检查覆盖；`run_all.sh` 改动限三处且 BLOCKED 名闭集不变。
- 可执行性：`run_all.sh` 三锚点、`check_d16.py` R3 行、根 `.gitignore`、Python 3.14 + yaml/jsonschema 已由主 Agent 核对（见下）；每个 ACT 有用例名清单、签名、DDL、CLI 用法与退出码；无模糊词；时长 10/40/90/120/60/90 分钟。
- 独立性：H1、H2 串行；ACT 05 对 `service.py` 的追加限一个方法。

派发前核对（主 Agent 脚本，2026-09-11，HEAD `375ff8b` 之后）：`run_all.sh` 三锚点各 1（a2 按脚本实际行 `OK) block_line … ;;` 订正）；`check_d16.py` R3 第 229–230 行为 `!= 43`；根 `.gitignore` 存在且无 `var/`；`var/`、`pipeline/ledger/` 不存在；Python 3.14.6、sqlite 3.53.4、`yaml`/`jsonschema`/`fcntl`/`secrets` 可导入；§19 第一列含「测试宿主匮乏」；fixture 常量（三包 `stage_package_id`/`artifact_revision_id`/`step_run_id`/输出修订/配置修订/operation、`edition_part` `art_…e1`、`technique_id qizheng`、anomalies page_002 `known_unrecognizable`）与 ACT 05 引用一致。

## 1. 范围核对

每个提交只含 ACT `commit.add` 路径；`var/` 与 `pipeline/ledger/tests` 产物不入库；`git diff --check`；fixture、Schema、规格、`.gitignore`（除一行）未动。

## 2. 门禁与判据（干净导出树，软链 `.venv`，`FIXTURE_ASSET_ROOT` 指本机页图）

- 三门禁绿；`unittest` 全过且用例数满足 TDD §1 各阈值；ACT 05 后 `run_all.sh` = `pass=2 fail=1 blocked=8`、exit 1。
- TDD §2 附加判据逐条实跑：签名逐字、状态表逐字、迁移穷举、半成品、篡改 Object、篡改 Ledger 判定、恒真检查、BLOCKED 行名、无新前缀。
- 矩阵外篡改 ≥ 5 例（主 Agent 自定，不预告）。

## 3. 语义与质量审查（主 Agent）

- `service.py` 每个写方法在单个事务内；状态更新走乐观锁；`resume_token` 不落明文；终态不可改写。
- Checkpoint 链跨 StepRun 接链且封存后只允许后继 StepRun 续写；恢复不重做已完成任务。
- `acceptance.py` 每个 PASS 名称都有对应 FAIL 出口；`fixture_ingest` 不读 fixture 之外的文件、不写 fixture。
- `ledgerd` 第二实例退出码 3；SIGTERM 清理。
- 中文注释；无 `except: pass`。

## 4. 结论

H1、H2 各自通过后记 `ACCEPTED`；全部通过后：SUBAGENT_TODO G7 impl-01 `ACCEPTED`、PLAN D-16 节 C「Artifact Ledger」条目勾选（附提交）、HANDOFF 同步；下一批 impl-02（M3 Corpus Compilation 在 Ledger 上的真实编译，目标 `run_all.sh 20.1` 的 fixture 部分）。

## 5. 验收记录

### 5.1 H1（2026-09-11，`git archive 0dff35d` 干净树，软链 `.venv`）

执行者上报三点，裁定：① DDL 表数 16 是对的，ACT/TDD 的「15」为主 Agent 数错，已订正；② `from`/`to` 为 Python 关键字，采纳 `from_status`/`to_status`；③ 采纳 `insert_stage_package` 与四个只读 helper（`stage_packages` 表在 contract 内，H2 需用而 ACT 03 scope 不含 `store.py`）。三点已回写 `act/02.yaml`/`TDD.md`。

- 范围：三提交分别 1 / 8 / 6 文件，只含 `commit.add` 路径；无 `var/`、`__pycache__`；`git diff --check` 通过；`.gitignore` +3 行（空行、中文注释、`var/`）。
- 门禁：`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` `D16 OK`（R3 已为 `< 43` 才 FAIL）。
- ACT 00 篡改：表 B 追加合法行（44）→ `D16 OK`；删一行（42）→ `FAIL R3 …=42（应 ≥ 43）`。
- ACT 01：`unittest` 26/26；`ids.PATTERNS` 19 项与 ACT 逐字相等；`ARTIFACT_TRANSITIONS`/`STEP_RUN_TRANSITIONS` 与 §8.2 表逐字相等；5×5 与 6×6 迁移穷举结果与表一致；表外取值 `SCH_002`；`ERROR_CODES` 九码逐字；`kind_of` 最长前缀（`co_shared_`、`prun_` 优先）；`pr_`+hex32 冒充 processing_run_id → `ID_001`；`LocalActorProvider` 返回 `local_owner`。
- ACT 02：`sqlite_master` 16 张表逐字；抽查四表列名齐全；外键 20 条；`journal_mode=wal`；`schema_meta` 1.0.0；Object Store 去重、篡改一字节 `verify` False、缺对象 `REF_001`、无 tmp 残留；跨进程第二写入者 `WriterLocked`、释放后可取得；只读连接写入 `OperationalError`；乐观锁过期版本 `IllegalTransition`、成功后 `status_version` 递增；异常事务回滚审计计数不变。
- 质量：导入只有标准库 + 自身包；中文 docstring；测试只用 `tempfile`。
- 主 Agent 自误：验收脚本用 `multiprocessing` 从 stdin 起子进程在 macOS 失败，改为 `subprocess` 复验，与执行者无关。

### 5.2 H2（2026-09-11，`git archive 45d99a1` 干净树，软链 `.venv` 与工作台 assets，`FIXTURE_ASSET_ROOT` 指本机页图）

执行者登记六点，裁定：① m3 输出类型 `corpus_package` 以 fixture 为准（`e2ecc9c` 已回写）；② `step_runs.stage` 从配置修订内容的 `stage` 键推导——采纳，但属主 Agent ACT 03 契约缺口（StepRequest 无 stage 字段），登记为已知缺口，待后续批次改 L0 Schema 时显式化，本批不动 Schema；③ `StepResult.status_version` 取迁移后值（当前 + 1），以 Schema `minimum: 1` 为准；④ `put_run_artifact` 提交归属提前到 `401b449`，如实登记，不 rebase；⑤ `LedgerReadMixin` 让两类共享九个只读方法，采纳；⑥ `--asset-root` 本切片只保留接口，采纳。

- 范围：`401b449` 3 文件、`01d32ca` 4 文件、`45d99a1` 5 文件，均只含 `commit.add` 路径；fixture、Schema、规格、`.gitignore` 未动；无 `var/`、`__pycache__`；`git diff --check`（限 `pipeline`、`openspec/acceptance`）通过。
- `run_all.sh`：+12/−2，只有 `ledger_check` 定义与两行替换，20.3 的 lineage 预检保留。
- 门禁：`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` OK；`unittest` 71/71。
- 完成判据：`run_all.sh` → `PASS 20.2`、`PASS 20.3`、`SUMMARY pass=2 fail=1 blocked=8`、exit 1；BLOCKED 行名 4 个逐字属 §19 第一列；`acceptance --check 20_2` 5 PASS、`20_3` 8 PASS；fixture 副本删 span → `FAIL 20.2`、`FAIL 20.3`；缺 fixture exit 3。
- 签名：ACT 03 `contract.methods` 22 个方法在 `service.py` 各恰 1 个 `def`，`inspect` 参数名与顺序零差异。
- 矩阵外篡改 8 例全部精确命中且只命中该项：删 m2 中间 Checkpoint → `chain_lengths`；改 m3 第三个 Checkpoint 的 prev 指针 → `chain_lengths`；把原 m3 StepRun 改 failed → `failed_run_preserved`；删 m2 人工决定关联 → `human_decisions_recorded`；配置修订类型改 step_log → `config_recorded`；m3 塞入非冻结输入 → `inputs_recorded`；m1 tool_version 置空 → `tool_recorded`；m1 输出改 quarantined → `outputs_recorded`。
- 半成品：`finish_step_run` 内注入 `_seal_step_manifest` 崩溃 → status `running`、version 0、无 StepManifest、无 succeeded 事件、`result_json` NULL。
- Object 篡改：封存前改一字节 → `SRC_003` 且 `quarantined`。
- 恢复凭据：库内只存 `v<version>:<sha256>`，明文不落库；错凭据与二次 `resume` 均 `InvalidResumeToken`。
- 质量：判定函数异常经 `_safe` 一律转 FAIL；场景失败时三个场景判定均 FAIL；无 `except: pass`；字符串中出现的前缀全部属登记册 19 个。
- **缺陷（返工 ACT 06）**：注入 `fixture_ingest.ingest` 抛异常 → `acceptance.main` 返回 3，`run_all.sh` 显示 `BLOCKED 测试宿主匮乏`。Ledger 写路径的真实回归会被显示为「前置缺失」而非 FAIL，违反 ACT 05「3 仅用于 fixture 不存在或缺依赖」。修法：准备或判定异常一律退出码 1。

### 5.3 返工 ACT 06（`c939575`，`git archive` 干净树）ACCEPTED

- 范围：2 文件（`acceptance.py` +4/−3，`tests/test_acceptance.py` +35）；`git diff --check` 通过。
- 门禁绿；`unittest` 73/73；`run_all.sh` 仍 `SUMMARY pass=2 fail=1 blocked=8`、exit 1。
- `return 3` 恰 2 处：fixture `manifest.yaml` 不存在、`_environment_error()` 非 None；缺 fixture 实跑 exit 3。
- 注入：`fixture_ingest.ingest` 抛异常 → exit 1、首行 `FAIL 20_2 宿主准备失败: RuntimeError`；`evaluate` 抛异常 → exit 1；缺依赖 → exit 3 `BLOCKED_ENV`。
- 端到端：临时把导出树的 `ingest` 改为首行抛异常 → `run_all.sh 20.2 20.3` 输出 `FAIL 20.2`、`FAIL 20.3`、`SUMMARY pass=0 fail=2 blocked=0`（修复前为 BLOCKED）。

### 5.4 结论

impl-01 `ACCEPTED`。完成判据达成：`openspec/acceptance/run_all.sh` 20.2、20.3 由 BLOCKED 变 PASS，且账本写路径缺陷、fixture 篡改、Ledger 记录篡改都能把它们打回 FAIL。

- 未勾 PLAN D-16 节 C「Artifact Ledger」：`check_d16.py` R5 要求节 C 恰 3 条 `- [ ]`，勾选会让 D-16 门禁变红（主 Agent 当初规则缺陷）。impl-02 ACT 00 先把 R5 改为「节 C 条目合计 3 条（`- [ ]` 与 `- [x]` 合计）」，再勾选并附 `c939575`。
- 已知缺口：`step_runs.stage` 从配置修订内容推导（StepRequest 无 stage 字段），后续改 L0 Schema 时显式化。
- 本批未做（按范围）：Pipeline / OCR FastAPI / Flutter 三个消费者接入 Ledger 客户端；旧存储迁移（`legacy-storage-transition.md` 状态不变）。
