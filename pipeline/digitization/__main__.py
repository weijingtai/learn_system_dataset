"""M2 电子文本清洗命令行入口。

提供 --raw-text-revision-id, --source-json, --edition-part-id, --ledger-dir 选项。
成功 exit 0，末行以 "M2 OK" 开头；
DigitizationRefused exit 2；
Gate 失败 exit 1。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline.ledger.service import LedgerService

from .errors import DigitizationRefused
from .step import run_m2


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口函数。"""
    parser = argparse.ArgumentParser(description="M2 电子文本清洗")
    parser.add_argument(
        "--raw-text-revision-id", required=True, help="原始文本修订 ID"
    )
    parser.add_argument(
        "--source-json", required=True, help="来源申报 JSON 字符串或文件路径"
    )
    parser.add_argument("--edition-part-id", required=True, help="版本部件 artifact_id")
    parser.add_argument("--ledger-dir", required=True, help="Ledger 根目录路径")

    args = parser.parse_args(argv)

    try:
        # 解析 source-json（支持文件路径或 JSON 字符串）
        json_path = Path(args.source_json)
        if json_path.is_file():
            source_info = json.loads(json_path.read_text(encoding="utf-8"))
        else:
            source_info = json.loads(args.source_json)

        # 初始化服务并执行清洗
        service = LedgerService(args.ledger_dir)
        try:
            res = run_m2(
                service,
                args.raw_text_revision_id,
                source_info,
                args.edition_part_id,
            )
            if "error" in res:
                print(f"M2 FAILED: {res['error']}", file=sys.stderr)
                return 1

            gate_res = res.get("gate_result")
            if gate_res is not None and not gate_res.passed:
                print(
                    f"M2 GATE FAILED: {gate_res.failed_checks}",
                    file=sys.stderr,
                )
                return 1

            print(f"cleaned_revision_id: {res['cleaned_revision_id']}")
            print(f"patch_revision_id: {res['patch_revision_id']}")
            print(f"report_revision_id: {res['report_revision_id']}")
            print(f"M2 OK {res['step_run_id']}")
            return 0
        finally:
            service.close()

    except DigitizationRefused as exc:
        print(f"DIGITIZATION REFUSED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
