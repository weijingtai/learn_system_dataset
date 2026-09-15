# NC-020a：消费端书籍契约核对清单

## 目标

创建 `openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md` 核对清单骨架，逐条列出消费端需要上游冻结的项目及判定标准，每项标注状态（已交付/有回执但未冻结/未交付）。

## 范围

- 输入：`docs/annotation-community/UPSTREAM_DATA_CONTRACT_REPLY.md`、`CONSUMER_ALIGNMENT_RESPONSE.md`
- 输出：`openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md`（核对清单骨架）
- 输出：`openspec/annotation-community/tools/check_book_contract.py`（校验脚本）

## 不做的事

- 不修改上游回执文件
- 不冻结任何 Schema（那是 NC-020b 的事）
- 不实现上传/导入/联调代码

## 依赖

- 无前置任务
- D-07/D-08 依赖登记在清单中但不阻断本任务

## 禁止项

- 不把「有回执」标为「已冻结」
- 不声明任何项目为「已交付」（骨架阶段全部未完成）
