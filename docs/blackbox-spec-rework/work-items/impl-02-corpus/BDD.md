# BDD：impl-02 M3 结构层

## 1. 检查脚本（ACT 00）

- 1.1 Given PLAN 节 C「Artifact Ledger」已勾选且附反引号提交号，When 跑 `check_d16.py`，Then `D16 OK`；未附提交号或节 C 少一条，Then `FAIL R5`。

## 2. 编译器（ACT 01）

- 2.1 Given mini_ed01 的 manifest、三页 OCR、page_002 终态，When `compile_structural`，Then 产出 43 条 Span、5 个批次，序列化字节与 fixture `spans.yaml` 逐字节相同，两次运行字节相同。
- 2.2 Given 页 `deferred`、`known_unrecognizable` 却有文字行、文字页无行、缺页、页序外多页、非法终态、缺页图哈希、行数超 99、非法 source_id，Then 分别拒绝并给出对应错误码。

## 3. 独立 Gate（ACT 02）

- 3.1 Given fixture 金标 Span，Then 8 项结构检查全过，`semantic` 恒为 `not_evaluated`。
- 3.2 Given 删一条 Span、制造重叠、改 offset、改文字、改行框、改字框、改页图哈希、改行序号、改 Span 号、重复 Span 号、批次超长、批次跨页、表头计数错、整页无 Span、空页无终态、排除页无证据、`deferred` 页，Then 每种篡改都让指定检查失败、Gate 为 `failed`。
- 3.3 Gate 不 import 编译器。

## 4. Ledger 集成（ACT 03）

- 4.1 Given Ledger 只灌入 m1、m2，When `run_m3`，Then 冻结 6 个输入修订、每批一个 Checkpoint 共 5 个、`corpus_spans` 字节等于金标、m3 StagePackage 过 Schema 且血缘输入等于冻结输入、StepRun `succeeded`。
- 4.2 Given M2 未灌入或 M3 已封存，Then 拒绝且 Ledger 无新增写入。
- 4.3 Given 页修订哈希与 `ocr_page_set` 不符、Gate 失败、页终态为 `deferred`，Then StepRun `failed`、失败报告封存、不产出 m3 StagePackage。

## 5. 验收脚本（ACT 04）

- 5.1 Given mini_ed01，When `m3-coverage.sh`，Then 8 项 PASS、`semantic_layer` BLOCKED、exit 2。
- 5.2 Given 金标被改、编译结果少一条 Span、准备阶段崩溃，Then exit 1；缺 fixture，Then exit 3。
- 5.3 Given 被验目录自带的 `verify.sh` 被换成假脚本且数据被改，Then 仍 `FAIL fixture_host`、exit 1。
