"""M1 电子文本入库命令行入口。

提供 --source-dir, --source-json, --edition-part-id, --ledger-dir 选项。
成功 exit 0，末行以 "M1 OK" 开头；
IntakeRefused exit 2；
SourceAssetMissing exit 3。
"""

import argparse
import json
import sys
from pathlib import Path

from pipeline.ledger.service import LedgerService

from .errors import IntakeRefused, SourceAssetMissing
from .source import load_source, read_source_files
from .step import run_m1


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口函数。"""
    parser = argparse.ArgumentParser(description="M1 电子文本入库")
    parser.add_argument("--source-dir", required=True, help="来源文件所在目录")
    parser.add_argument("--source-json", required=True, help="来源申报 JSON 字符串或文件路径")
    parser.add_argument("--edition-part-id", required=True, help="版本部件 artifact_id")
    parser.add_argument("--ledger-dir", required=True, help="Ledger 根目录路径")

    args = parser.parse_args(argv)

    try:
        # 解析 source-json（支持文件路径或 JSON 字符串）
        json_path = Path(args.source_json)
        if json_path.is_file():
            source_raw = json.loads(json_path.read_text(encoding="utf-8"))
        else:
            source_raw = json.loads(args.source_json)

        # 校验来源
        source_info = load_source(source_raw)

        # 读取文件
        files = read_source_files(args.source_dir, source_info["pages"])

        # 初始化服务并执行入库
        service = LedgerService(args.ledger_dir)
        try:
            res = run_m1(service, source_info, files, args.edition_part_id)
            if "error" in res:
                print(f"M1 FAILED: {res['error']}", file=sys.stderr)
                return 1

            print(f"manifest_revision_id: {res['manifest_revision_id']}")
            print(f"raw_text_revision_ids: {res['raw_text_revision_ids']}")
            print(f"M1 OK {res['step_run_id']}")
            return 0
        finally:
            service.close()

    except SourceAssetMissing as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except IntakeRefused as exc:
        print(f"INTAKE REFUSED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
