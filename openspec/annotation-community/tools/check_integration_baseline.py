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

DEPENDENCY_PINS = {
    "flutter_markdown_plus": "1.0.12",
    "drift": "2.31.0",
    "drift_dev": "2.31.0",
    "drift_flutter": "0.2.8",
    "sqlite3": "2.9.4",
    "sqlite3_flutter_libs": "0.5.42",
    "path_provider": "2.1.6",
    "build_runner": "2.15.1",
}


def _is_plain_int(value):
    """True 表示 value 是 int 且不是 bool（bool 是 int 子类，需排除）。"""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_nonempty_str(value):
    return isinstance(value, str) and value != ""


def _resolve_path(base_dir, raw):
    """契约 §1：JSON 中的相对路径相对于输入 JSON 所在目录解析，绝对路径保持原值。"""
    p = Path(raw)
    return p if p.is_absolute() else (base_dir / raw)


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


def check_top_level(data, base_dir, report):
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
            if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
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


def check_client(client, base_dir, report):
    """契约 §3：client。调用方保证 client 已由 §2 确认存在；若不是 object 则
    不下钻（由 §2 已报告 "client"）。"""
    if not isinstance(client, dict):
        return

    path_val = client.get("path")
    path_present = "path" in client
    path_valid_basic = _is_nonempty_str(path_val)
    if not path_present or not path_valid_basic:
        report.add("client.path")

    if "package" not in client:
        report.add("client.package")
    elif client["package"] != "reading_notes":
        report.add("client.package")

    state = client.get("state")
    if "state" not in client:
        report.add("client.state")
    elif state not in ("PLANNED_NEW", "EXISTING"):
        report.add("client.state")

    if "creation_owner" not in client:
        report.add("client.creation_owner")
    elif not isinstance(client["creation_owner"], str):
        report.add("client.creation_owner")

    if "vcs" not in client:
        report.add("client.vcs")
    elif client["vcs"] != "NEW_GIT_REPOSITORY":
        report.add("client.vcs")

    if "runtime_verified" not in client:
        report.add("client.runtime_verified")
    elif not isinstance(client["runtime_verified"], bool):
        report.add("client.runtime_verified")

    if state == "PLANNED_NEW":
        creation_owner = client.get("creation_owner")
        if creation_owner != "NC-004":
            report.add("client.creation_owner")
        if path_valid_basic:
            p = _resolve_path(base_dir, path_val)
            if not p.parent.is_dir():
                report.add("client.path")
            if p.exists():
                report.add("client.state")
    elif state == "EXISTING":
        if path_valid_basic:
            p = _resolve_path(base_dir, path_val)
            if not (p / "pubspec.yaml").is_file():
                report.add("client.path")
            if not (p / "lib").is_dir():
                report.add("client.path")
            if not (p / ".git").exists():
                report.add("client.path")


def check_sdk(sdk, base_dir, report):
    """契约 §3：sdk。"""
    if not isinstance(sdk, dict):
        return

    if "flutter" not in sdk:
        report.add("sdk.flutter")
    elif sdk["flutter"] != "3.44.6":
        report.add("sdk.flutter")

    if "dart" not in sdk:
        report.add("sdk.dart")
    elif sdk["dart"] != "3.12.2":
        report.add("sdk.dart")

    if "evidence" not in sdk:
        report.add("sdk.evidence")
    else:
        evidence = sdk["evidence"]
        if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
            report.add("sdk.evidence")

    if "verification" not in sdk:
        report.add("sdk.verification")
    elif sdk["verification"] not in ("CACHE_METADATA_ONLY", "RUNTIME_VERIFIED"):
        report.add("sdk.verification")


def check_dependencies(deps, report):
    """契约 §3：dependencies，恰好 8 个键，值逐字相等。"""
    if not isinstance(deps, dict):
        return

    extra = set(deps.keys()) - set(DEPENDENCY_PINS.keys())
    if extra:
        report.add("dependencies")

    for key, expected in DEPENDENCY_PINS.items():
        if key not in deps:
            report.add(f"dependencies.{key}")
        elif deps[key] != expected:
            report.add(f"dependencies.{key}")


def check_dependency_policy(policy, report):
    """契约 §3：dependency_policy。"""
    if not isinstance(policy, dict):
        return

    if "offline_failure" not in policy:
        report.add("dependency_policy.offline_failure")
    elif policy["offline_failure"] != "ENV_BLOCKED":
        report.add("dependency_policy.offline_failure")

    if "flutter_markdown_plus_rationale" not in policy:
        report.add("dependency_policy.flutter_markdown_plus_rationale")
    elif not _is_nonempty_str(policy["flutter_markdown_plus_rationale"]):
        report.add("dependency_policy.flutter_markdown_plus_rationale")


def check_identity(identity, report):
    """契约 §3：identity。"""
    if not isinstance(identity, dict):
        return

    if "policy" not in identity:
        report.add("identity.policy")
    elif identity["policy"] != "HOST_SCOPE_ONLY":
        report.add("identity.policy")

    if "new_identity_system" not in identity:
        report.add("identity.new_identity_system")
    elif identity["new_identity_system"] is not False:
        report.add("identity.new_identity_system")

    if "public_profile_id" not in identity:
        report.add("identity.public_profile_id")
    elif not _is_nonempty_str(identity["public_profile_id"]):
        report.add("identity.public_profile_id")


def check_openapi_validator_common(ov, base_dir, report):
    """契约 §3：openapi_validator 两种 profile 共同的规则。§4 的 VERIFIED
    档 evidence 存在性检查由 integrated 增量规则另行实现（本函数不检查）。"""
    if not isinstance(ov, dict):
        return

    if "package" not in ov:
        report.add("openapi_validator.package")
    elif ov["package"] != "openapi-spec-validator":
        report.add("openapi_validator.package")

    if "version" not in ov:
        report.add("openapi_validator.version")
    elif ov["version"] != "0.9.0":
        report.add("openapi_validator.version")

    if "install_command" not in ov:
        report.add("openapi_validator.install_command")
    elif not _is_nonempty_str(ov["install_command"]):
        report.add("openapi_validator.install_command")

    if "offline_failure" not in ov:
        report.add("openapi_validator.offline_failure")
    elif ov["offline_failure"] != "ENV_BLOCKED":
        report.add("openapi_validator.offline_failure")

    status = None
    if "status" not in ov:
        report.add("openapi_validator.status")
    else:
        status = ov["status"]
        if status not in ("NOT_INSTALLED_IN_CURRENT_PYTHON", "VERIFIED"):
            report.add("openapi_validator.status")

    if "evidence" not in ov:
        report.add("openapi_validator.evidence")
    else:
        evidence = ov["evidence"]
        if status == "NOT_INSTALLED_IN_CURRENT_PYTHON":
            if evidence is not None:
                report.add("openapi_validator.evidence")
        # status == "VERIFIED" 时 local 档不检查 evidence 是否存在（§4 检查）；
        # status 不合法/缺失时不额外判定 evidence。


def check_md_placeholder(base_dir, report):
    """契约 §3：同目录 INTEGRATION_BASELINE.md 必须存在，且不含 TBD/待定。"""
    md_path = base_dir / "INTEGRATION_BASELINE.md"
    if not md_path.is_file():
        report.add("INTEGRATION_BASELINE.md")
        return
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        report.add("INTEGRATION_BASELINE.md")
        return
    if "TBD" in text or "待定" in text:
        report.add("INTEGRATION_BASELINE.md")


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

    base_dir = input_path.parent
    report = Report()
    check_top_level(data, base_dir, report)
    check_client(data.get("client"), base_dir, report)
    check_sdk(data.get("sdk"), base_dir, report)
    check_dependencies(data.get("dependencies"), report)
    check_dependency_policy(data.get("dependency_policy"), report)
    check_identity(data.get("identity"), report)
    check_openapi_validator_common(data.get("openapi_validator"), base_dir, report)
    check_md_placeholder(base_dir, report)

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
