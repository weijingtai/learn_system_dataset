# impl-01：Artifact Ledger（§17）首纵切第一批

状态：`READY`（主 Agent 2026-09-11 四查通过；H1 待派发）

## 1. 目标

在 `pipeline/ledger/` 落地规格 §17 的 Artifact Ledger 第一切片：标识与状态机（§8.1/§8.2）、SQLite Metadata Ledger + content-addressed Object Store、StepRun 事务序列（§17 末段）与人工恢复（§7.1）、`suspended`/`recovery` 对账（§17）、StageCheckpoint（§17.1）、单写入者本地进程与本地客户端（§17 D-04 决议）、`ActorProvider`。以 `pipeline/corpus/_fixture/mini_ed01/` 为统一宿主，把 `openspec/acceptance/run_all.sh` 的 **20.2 与 20.3 由 `BLOCKED` 变 `PASS`**。

完成判据（本批唯一的「做完」定义）：

```bash
bash openspec/acceptance/run_all.sh          # 期望 PASS 20.2、PASS 20.3；SUMMARY pass=2 fail=1 blocked=8；退出码 1（20.7 预期 FAIL 不变）
.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t .   # 全部通过
```

## 2. 依据（只读来源，执行者不得偏离）

- 规格 §7、§7.1（接口、StepRun 生命周期、`resume_token`、`record_human_event`/`resume`）
- 规格 §8.1（标识格式：17 个前缀，`[0-9a-f]{32}`，`<stage>` 闭集 m1–m8）、§8.2（Artifact status 5 态与迁移表；StepRun status 6 态与迁移表；9 个错误码；8 个 ReviewDecision 类型）
- 规格 §17（混合存储、单机本地进程、单写入者、WAL、`suspended` 对账、`ActorProvider`、Artifact 必记字段、步骤事务序列）、§17.1（StageCheckpoint）
- `openspec/schemas/{artifact_ref,step_request,step_result,stage_package}.schema.json`（L0，不得改）
- `openspec/legacy-storage-transition.md` §2–§4（Object Store 不进 Git；旧路径不碰）
- `openspec/id-prefix-registry.md` §4 规则 1：**不得新增任何 ID 前缀**（Transformation、事件等用 SQLite 整数主键或既有 `rev_`）
- `pipeline/corpus/_fixture/mini_ed01/`（constants 与 expected 三包）
- `openspec/acceptance/run_all.sh` 现行 20.2/20.3 规则（D-18 产物，本批按 ACT 05 精确改写）

## 3. 范围

写（全部新建，除标注外）：`pipeline/ledger/**`（含 `tests/`）、根 `.gitignore`（追加一行 `var/`）、`openspec/acceptance/run_all.sh`（只改 20.2/20.3 两个 case 体，ACT 05）、`docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py`（ACT 00 只改 R3 行数条件）。

禁止：改 `openspec/schemas/**`、`verify-T.sh`、`mutations.sh`、规格正文、`PLAN.md`、fixture 目录任何文件、`pipeline/` 既有脚本；新增第三方依赖（只用标准库 + 已装 PyYAML/jsonschema）；新增 ID 前缀；把 Ledger 数据写进 Git（默认根目录 `var/ledger/`，被 `.gitignore`）；在 fixture 目录内生成 Ledger；用 `pytest`（本机无，用 `unittest`）。

## 4. 主 Agent 决定（记录，执行者不重议）

1. **20.2/20.3 的判定宿主**：由 ACT 05 的 `fixture_ingest` 把 mini_ed01 的三个 expected 阶段包经 **真实 Ledger 写路径**灌入临时 Ledger，再由 `pipeline/ledger/acceptance.py` 在其上做场景判定（20.2：失败 StepRun 保留 + 从最近 Checkpoint 恢复不重做已完成任务；20.3：每个 Transformation 六项记录齐全）。M4–M6 未实现不影响这两条；20.1 仍 BLOCKED（Gate 归 Orchestrator）。
2. **进程模型**：`ledgerd` 用 Unix domain socket + 换行分隔 JSON；单写入者用 `fcntl.flock` 独占 `writer.lock`；`LedgerService` 直连模式与 `ledgerd` 共用同一把锁；只读查询用 `LedgerReader`（SQLite `mode=ro`，不取锁）。Pipeline/OCR/Flutter 接入在后续批次。
3. **导入路径允许调用方指定 ID**：`fixture_ingest` 与未来 `LegacyImportAdapter` 需要沿用既有 ID（fixture 常量）；服务 API 的 `*_id` 可选参数只在格式合法且未被占用时接受，否则 `ID_001`/`ID_002`。正常运行路径一律 `uuid4().hex` 生成。
4. **错误码**：只在语义吻合时使用 §8.2 第 3 表的 9 个码（`ID_001` 格式、`ID_002` 重复、`REF_001` 引用不存在、`SRC_003` 哈希不符、`SCH_001` 缺字段、`SCH_002` 非法枚举）；状态迁移非法、写锁被占等 Ledger 内部错误用异常类表达，不新造错误码。
5. **StageCheckpoint 与人工事件都是 Artifact**：Checkpoint 内容 JSON 存 Object Store，元数据进 `stage_checkpoints` 表；人工事件是 `artifact_type=human_event` 的封存 Revision。
6. **测试框架** `unittest`；每个 ACT 先写测试（Red），再实现（Green）；执行者报告必须含 Red 原文。
7. 分两轮派发：H1 = ACT 00–02，H2 = ACT 03–05；H1 验收通过后才派 H2。

## 5. 目录（ACT 落地后）

```text
pipeline/ledger/
  __init__.py
  ids.py            标识生成/校验（§8.1）
  states.py         Artifact/StepRun 状态与迁移表（§8.2）
  errors.py         异常类 + 9 个错误码常量
  objects.py        Object Store
  store.py          SQLite Metadata Ledger（DDL、连接、WAL、事务）
  lock.py           写入者锁
  actor.py          ActorProvider / LocalActorProvider
  service.py        LedgerService（写 API）+ LedgerReader（只读 API）
  ledgerd.py        本地进程
  client.py         LedgerClient
  cli.py            python -m pipeline.ledger.cli
  fixture_ingest.py mini_ed01 → Ledger
  acceptance.py     20.2 / 20.3 场景判定
  tests/            test_ids.py test_states.py test_objects.py test_store.py test_service.py test_checkpoint.py test_daemon.py test_ingest.py test_acceptance.py
```
