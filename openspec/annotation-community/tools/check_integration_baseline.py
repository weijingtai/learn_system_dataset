#!/usr/bin/env python3
"""NC-001 集成基线校验器（NC-001-01）。

用法：
    check_integration_baseline.py --profile local|integrated --input PATH

判据来源：docs/blackbox-spec-rework/work-items/nc-001/VALIDATION_CONTRACT.md。
本工具只做结构校验：
- 对外部路径只调用 exists/is_file/is_dir 判断存在性，不读取其内容；
- 唯一读取内容的文件是 --input 指定的 JSON 与同目录的 INTEGRATION_BASELINE.md；
- 不执行 git 或其他子进程，不连接网络或 Emulator，不写文件或创建目录。

本步骤（act/01）只实现契约 §2（顶层规则）与 §6（输出格式）；
§3 及以后的对象规则由后续步骤补齐。--profile integrated 本步暂时退出 2。
"""

import argparse
import json
import sys
from pathlib import Path

STDERR_INTEGRATED_NOT_IMPLEMENTED = "integrated profile not implemented"


def _is_plain_int(value):
    """True 表示 value 是 int 且不是 bool（bool 是 int 子类，需排除）。"""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_nonempty_str(value):
    return isinstance(value, str) and value != ""


class Report:
    """收集全部错误路径，最终去重排序输出（契约 §6）。"""

    def __init__(self):
        self._paths = set()

    def add(self, path):
        self._paths.add(path)

    def sorted_paths(self):
        return sorted(self._paths)

    def has_errors(self):
        return bool(self._paths)


def check_top_level(data, report):
    """契约 §2：顶层键存在性、类型与固定值/枚举。

    调用方需先确认 data 是 dict（root 检查已在上一层完成）。
    """
    # schema_version：整数 1，bool 不接受
    if "schema_version" not in data:
        report.add("schema_version")
    else:
        v = data["schema_version"]
        if not _is_plain_int(v) or v != 1:
            report.add("schema_version")

    # spec_version：字符串 "1.5"
    if "spec_version" not in data:
        report.add("spec_version")
    elif data["spec_version"] != "1.5":
        report.add("spec_version")

    # task_id：字符串 "NC-001"
    if "task_id" not in data:
        report.add("task_id")
    elif data["task_id"] != "NC-001":
        report.add("task_id")

    # scope：LOCAL_PREPARATION / INTEGRATED / TEST_FIXTURE（两种 profile 共同的枚举范围）
    if "scope" not in data:
        report.add("scope")
    elif data["scope"] not in ("LOCAL_PREPARATION", "INTEGRATED", "TEST_FIXTURE"):
        report.add("scope")

    # book_work：DEFERRED_BY_USER
    if "book_work" not in data:
        report.add("book_work")
    elif data["book_work"] != "DEFERRED_BY_USER":
        report.add("book_work")

    # resolution_status：NOT_RUN / RESOLVED
    resolution_status = None
    if "resolution_status" not in data:
        report.add("resolution_status")
    else:
        resolution_status = data["resolution_status"]
        if resolution_status not in ("NOT_RUN", "RESOLVED"):
            report.add("resolution_status")

    # resolution_evidence：键必须存在；NOT_RUN 时为 null，RESOLVED 时为存在的文件
    if "resolution_evidence" not in data:
        report.add("resolution_evidence")
    else:
        evidence = data["resolution_evidence"]
        if resolution_status == "NOT_RUN":
            if evidence is not None:
                report.add("resolution_evidence")
        elif resolution_status == "RESOLVED":
            if not _is_nonempty_str(evidence) or not Path(evidence).is_file():
                report.add("resolution_evidence")
        # resolution_status 本身不合法/缺失时，不对 evidence 做额外判定（契约未写明）

    # client、sdk、dependencies、dependency_policy、identity、openapi_validator、integration：object
    for key in (
        "client",
        "sdk",
        "dependencies",
        "dependency_policy",
        "identity",
        "openapi_validator",
        "integration",
    ):
        if key not in data:
            report.add(key)
        elif not isinstance(data[key], dict):
            report.add(key)

    # repositories、ports：array
    for key in ("repositories", "ports"):
        if key not in data:
            report.add(key)
        elif not isinstance(data[key], list):
            report.add(key)


def build_arg_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--profile")
    parser.add_argument("--input")
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = build_arg_parser()
    try:
        ns, _unknown = parser.parse_known_args(argv)
    except SystemExit:
        sys.stderr.write("invalid arguments\n")
        return 2

    profile = ns.profile
    if profile not in ("local", "integrated"):
        sys.stderr.write("invalid or missing --profile (expected local or integrated)\n")
        return 2

    if not ns.input:
        sys.stderr.write("missing --input\n")
        return 2

    input_path = Path(ns.input)
    if not input_path.is_file():
        sys.stderr.write(f"input file not found: {ns.input}\n")
        return 2

    try:
        text = input_path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"cannot read --input: {exc}\n")
        return 2

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"invalid JSON input: {exc}\n")
        return 2

    if profile == "integrated":
        # 本步（act/01）尚未实现 integrated 档，§4 由 act/04 补齐。
        sys.stderr.write(STDERR_INTEGRATED_NOT_IMPLEMENTED + "\n")
        return 2

    # profile == "local"
    if not isinstance(data, dict):
        print("root")
        return 1

    report = Report()
    check_top_level(data, report)

    if report.has_errors():
        for path in report.sorted_paths():
            print(path)
        return 1

    scope = data.get("scope")
    suffix = " (TEST_FIXTURE)" if scope == "TEST_FIXTURE" else ""
    print("LOCAL_PREPARATION_PASS" + suffix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
