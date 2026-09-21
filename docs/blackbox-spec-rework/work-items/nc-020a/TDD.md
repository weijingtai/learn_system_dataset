# NC-020a TDD：消费端书籍契约核对清单

## 正向判据

### T-01 清单文件存在且可读

```bash
test -f openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md
```
退出 0。

### T-02 校验脚本可执行且退出 0

```bash
python3 openspec/annotation-community/tools/check_book_contract.py
```
退出 0，输出含「PASS」。

### T-03 清单包含所有必要章节

```bash
grep -c "^## [0-9]" openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md
```
输出 ≥ 7（七个章节）。

### T-04 清单包含所有编号项

```bash
grep -cE "^\| [A-Z]" openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md
```
输出 ≥ 28（28 个编号项）。

### T-05 D-07/D-08 依赖已登记

```bash
grep "D-07" openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md
grep "D-08" openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md
```
两者均存在。

## 反向判据

### T-06 无「已冻结」状态

```bash
grep -c "已冻结" openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md | grep -v "未冻结"
```
输出 0（骨架阶段不允许出现「已冻结」）。

### T-07 校验脚本检测空状态失败

临时将清单某行状态列清空，运行校验脚本，退出码应为 1。

```bash
# 临时修改
cp openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md /tmp/bak.md
sed -i 's/| 未交付 |$/|  |/' openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md
python3 openspec/annotation-community/tools/check_book_contract.py; rc=$?
cp /tmp/bak.md openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md
exit $rc  # 应为 1
```

### T-08 校验脚本检测非法状态失败

临时将清单某行状态改为「已冻结」，运行校验脚本，退出码应为 1。

```bash
cp openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md /tmp/bak.md
sed -i 's/| 未交付 |$/| 已冻结 |/' openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md
python3 openspec/annotation-community/tools/check_book_contract.py; rc=$?
cp /tmp/bak.md openspec/annotation-community/BOOK_CONTRACT_ACCEPTANCE.md
exit $rc  # 应为 1
```
