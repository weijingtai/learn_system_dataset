# NC-020a 执行提示词

你是 NC-020a 的执行 Agent。任务是创建消费端书籍契约核对清单骨架。

## 步骤

1. 读 `docs/annotation-community/UPSTREAM_DATA_CONTRACT_REPLY.md` 和 `CONSUMER_ALIGNMENT_RESPONSE.md`
2. 创建 `openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md`，包含：
   - 政策与发布门禁（P-01～P-04）
   - 机器 Schema 与文件映射（S-01～S-07）
   - D-06 选区与迁移（D-06-01～D-06-05）
   - 资产与交付（A-01～A-06）
   - 真实样例（E-01～E-04）
   - D-07/D-08 依赖登记
3. 创建 `openspec/annotation-community/tools/check_book_contract.py`
4. 运行校验脚本确认退出 0

## 禁止

- 不修改上游回执文件
- 不冻结任何 Schema
- 不声明「已冻结」状态
