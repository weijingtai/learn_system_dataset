# T-11 主 Agent 验收清单

状态：`ACCEPTED`（G3 R1）

## 范围

- [x] 仅修改 §19、T-11 的 TDD/ACT/Acceptance 与 `verify-T.sh`。
- [x] 未触碰业务代码、Schema、数据库、fixture、PLAN、HANDOFF、TODO。

## 事实与规格

- [x] M1 使用真实路径 `pipeline/tools/ingest_epub.py`，不再引用不存在的 `tools/ingest_epub.py`。
- [x] M1/M6/M8 写入 HEAD 可复核事实：496 rules、`original_text` 非空 0、`is_verified=1` 为 0、`ge_ju_versions` 0 行、`conditions` 404、`chapter` 486、148 span→18 键/6 组碰撞。
- [x] 私有依赖、启动覆盖、保存即 verified 明确标为 G2 已遏制的历史缺口，不再当作当前缺口。
- [x] tracked 非 OCR 测试数明确为 3，统计口径使用 `git ls-files` 且排除 `.venv`。
- [x] 当前差距补齐二元“修复前失败/修复后成功”判据；观察型命令不作为通过门禁。

## 证据

- [x] 负向变异：主 Agent 将真实路径改回错误路径后，`verify-T.sh` 退出码 1。
- [x] 全量 `bash docs/blackbox-spec-rework/verify-T.sh` 通过（退出码 0，FAIL 合计 0）。
- [x] `git diff --check` 通过。
- [x] 主 Agent 完成独立语义复核并标记 `ACCEPTED`。

最终结论：`ACCEPTED`。路径、HEAD 事实、历史缺口状态和二元判据均已独立复核。
