#!/usr/bin/env python3
"""NC-020a 核对清单校验器。

红条件：
1. 清单中存在未标注状态的项（状态列为空或非「已交付/有回执但未冻结/未交付」）
2. 把「有回执」标为「已冻结」（不允许跳过冻结步骤）

运行：python3 openspec/annotation-community/tools/check_book_contract.py
退出 0 表示通过。
"""

import re
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent
清单 = SPEC / "BOOK_CONTRACT_ACCEPTANCE.md"

有效状态 = {"已交付", "有回执但未冻结", "未交付"}


def 校验():
    错误 = []
    行号 = 0
    in_table = False

    if not 清单.is_file():
        print(f"FAIL  清单文件不存在: {清单}")
        return 1

    内容 = 清单.read_text(encoding="utf-8")
    行列表 = 内容.splitlines()

    for 行 in 行列表:
        行号 += 1
        # 检测表格行（以 | 开头和结尾）
        if 行.strip().startswith("|") and 行.strip().endswith("|"):
            # 跳过分隔行（|---|）
            if re.match(r"^\|[\s\-|]+\|$", 行.strip()):
                in_table = True
                continue
            # 跳过表头行
            if "编号" in 行 and "项目" in 行:
                continue
            # 解析数据行
            单元格 = [c.strip() for c in 行.strip().strip("|").split("|")]
            if len(单元格) >= 4:
                编号 = 单元格[0].strip()
                状态 = 单元格[3].strip()
                if 编号 and not 编号.startswith("##"):
                    if not 状态:
                        错误.append(f"行 {行号}: {编号} 状态列为空")
                    elif 状态 not in 有效状态:
                        错误.append(f"行 {行号}: {编号} 状态「{状态}」不在有效集合中")
                    # 红条件 2：不允许「已冻结」
                    if "已冻结" in 状态 and "未冻结" not in 状态:
                        错误.append(f"行 {行号}: {编号} 状态包含「已冻结」——NC-020a 骨架阶段不允许跳过冻结步骤")

    if 错误:
        for e in 错误:
            print(f"FAIL  {e}")
        print(f"\nNC-020a 校验失败: {len(错误)} 项")
        return 1
    else:
        print("PASS  NC-020a 核对清单校验通过")
        return 0


if __name__ == "__main__":
    sys.exit(校验())
