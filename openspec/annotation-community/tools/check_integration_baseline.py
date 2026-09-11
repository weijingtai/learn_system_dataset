#!/usr/bin/env python3
"""NC-001 集成基线校验器（NC-001-01）。

用法：
    check_integration_baseline.py --profile local|integrated --input PATH

判据来源：docs/blackbox-spec-rework/work-items/nc-001/VALIDATION_CONTRACT.md。
本工具只做结构校验：
- 对外部路径只调用 exists/is_file/is_dir 判断存在性，不读取其内容；
- 唯一读取内容的文件是 --input 指定的 JSON 与同目录的 INTEGRATION_BASELINE.md；
- 不执行 git 或其他子进程，不连接网络或 Emulator，不写文件或创建目录。

local 档校验契约 §2～§3（本地规划基线）；integrated 档在 §2～§3 之上叠加 §4～§5
的增量规则（联调结构基线）。
"""

import argparse
import json
import re
import sys
from pathlib import Path

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

REPOSITORY_NAMES = [
    "SPEC", "MIGRATION", "STORAGE", "SOCIAL", "NOTIFICATION", "REST", "SERVER", "NOTIFIER",
]

PORT_NAMES = [
    "HOST_INIT", "ACCOUNT_SCOPE", "HTTP", "STORAGE", "IM_NAVIGATION",
    "MENTION", "NOTIFICATION_RECEIVE", "SERVER_IDENTITY",
]

TEST_RUN_REPOS = ["SPEC", "STORAGE", "SOCIAL", "NOTIFICATION", "REST", "SERVER", "NOTIFIER"]

# integration 下各对象的通用规格：(未验证态取值, 验证态取值, 验证字段列表)。
# 常驻字段（不受 status 闸门约束）与 account_deletion 的固定值单独处理。
INTEGRATION_OBJECT_SPECS = {
    "backend": ("UNVERIFIED", "VERIFIED", ["project_id", "namespace_prefix", "credential_injection", "evidence"]),
    "emulator": ("CONFIG_ONLY_NOT_CONTACTED", "VERIFIED", ["start_command", "evidence"]),
    "rules": ("UNVERIFIED", "VERIFIED", ["path", "evidence"]),
    "notifier_binding": ("UNVERIFIED", "VERIFIED", ["evidence"]),
    "notification_presentation": ("UNVERIFIED", "VERIFIED", ["evidence"]),
    "mute_aggregation": ("UNVERIFIED", "VERIFIED", ["content_mute", "aggregation", "evidence"]),
    "account_deletion": (
        "UNVERIFIED", "VERIFIED",
        ["source", "delivery_semantics", "test_command", "exit_code", "count", "evidence"],
    ),
}

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")
NAMESPACE_PREFIX_RE = re.compile(r"^nc_[0-9]{8}_[0-9a-f]{4,12}$")


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


def check_repositories(repos, report):
    """契约 §3：repositories。数组元素结构或定位键集合不符时只报数组路径本身。"""
    if not isinstance(repos, list):
        return

    for item in repos:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            report.add("repositories")
            return

    names = [item["name"] for item in repos]
    if sorted(names) != sorted(REPOSITORY_NAMES):
        report.add("repositories")
        return

    by_name = {item["name"]: item for item in repos}
    for name in REPOSITORY_NAMES:
        item = by_name[name]
        prefix = f"repositories[{name}]"

        if "path" not in item or not _is_nonempty_str(item["path"]):
            report.add(f"{prefix}.path")

        wp_ok = "write_policy" in item and item["write_policy"] in ("READ_ONLY", "PER_TASK_WHITELIST")
        if not wp_ok:
            report.add(f"{prefix}.write_policy")
        elif name in ("MIGRATION", "NOTIFIER") and item["write_policy"] != "READ_ONLY":
            report.add(f"{prefix}.write_policy")

        if name == "MIGRATION":
            if "status" not in item or item["status"] != "UNAVAILABLE":
                report.add(f"{prefix}.status")
            continue

        if "git_root" not in item or not _is_nonempty_str(item["git_root"]):
            report.add(f"{prefix}.git_root")

        if "head" not in item or not isinstance(item.get("head"), str) or not HEX40_RE.match(item["head"]):
            report.add(f"{prefix}.head")

        dirty = item.get("dirty_entries")
        if "dirty_entries" not in item or not _is_plain_int(dirty) or dirty < 0:
            report.add(f"{prefix}.dirty_entries")

        tests = item.get("tests")
        if "tests" not in item or not isinstance(tests, dict):
            report.add(f"{prefix}.tests")
        else:
            status = tests.get("status")
            if "status" not in tests or status not in ("NOT_RUN", "PASSED", "FAILED"):
                report.add(f"{prefix}.tests.status")
            if status == "NOT_RUN":
                if "reason" not in tests or not _is_nonempty_str(tests["reason"]):
                    report.add(f"{prefix}.tests.reason")


def check_ports(ports, base_dir, report):
    """契约 §3：ports。数组元素结构或定位键集合不符时只报数组路径本身。"""
    if not isinstance(ports, list):
        return

    for item in ports:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            report.add("ports")
            return

    names = [item["name"] for item in ports]
    if sorted(names) != sorted(PORT_NAMES):
        report.add("ports")
        return

    by_name = {item["name"]: item for item in ports}
    for name in PORT_NAMES:
        item = by_name[name]
        prefix = f"ports[{name}]"

        file_val = item.get("file")
        if "file" not in item or not _is_nonempty_str(file_val) or not _resolve_path(base_dir, file_val).is_file():
            report.add(f"{prefix}.file")

        symbol = item.get("symbol")
        if "symbol" not in item or not isinstance(symbol, str) or not SYMBOL_RE.match(symbol):
            report.add(f"{prefix}.symbol")

        if "kind" not in item or item["kind"] not in ("EXISTING_IMPLEMENTATION", "NEW_ADAPTER"):
            report.add(f"{prefix}.kind")


def check_integration_object_common(name, obj, report):
    """契约 §3：integration 下对象的共同规则——status 枚举、未验证态时验证
    字段必须为 null。常驻字段与 account_deletion 固定值由调用方另行检查。
    调用方须保证 obj 已是 dict。"""
    unverified, verified, val_fields = INTEGRATION_OBJECT_SPECS[name]
    prefix = f"integration.{name}"

    status = None
    if "status" not in obj:
        report.add(f"{prefix}.status")
    else:
        status = obj["status"]
        if status not in (unverified, verified):
            report.add(f"{prefix}.status")

    for field in val_fields:
        if field not in obj:
            report.add(f"{prefix}.{field}")
        elif status == unverified and obj[field] is not None:
            report.add(f"{prefix}.{field}")


def check_integration(integration, base_dir, report):
    """契约 §3：integration。local 档只检查 devices/account_pairs/test_runs
    为 array（§4 的内容规则由 integrated 增量另行检查）。"""
    if not isinstance(integration, dict):
        return

    for key in ("devices", "account_pairs", "test_runs"):
        if key not in integration:
            report.add(f"integration.{key}")
        elif not isinstance(integration[key], list):
            report.add(f"integration.{key}")

    object_names = (
        "backend", "emulator", "rules", "notifier_binding",
        "notification_presentation", "mute_aggregation", "account_deletion",
    )
    for name in object_names:
        if name not in integration or not isinstance(integration[name], dict):
            report.add(f"integration.{name}")
            continue
        check_integration_object_common(name, integration[name], report)

    emulator = integration.get("emulator")
    if isinstance(emulator, dict):
        for field in ("firestore_config", "auth_config", "project_config"):
            if field not in emulator or not _is_nonempty_str(emulator[field]):
                report.add(f"integration.emulator.{field}")

    np_obj = integration.get("notification_presentation")
    if isinstance(np_obj, dict):
        if "choice" not in np_obj or np_obj["choice"] not in (
            "SOCIAL_NOTIFICATION_CENTER", "NOTIFICATION_PACKAGE_PAGE",
        ):
            report.add("integration.notification_presentation.choice")

        file_val = np_obj.get("file")
        if "file" not in np_obj or not _is_nonempty_str(file_val) or not _resolve_path(base_dir, file_val).is_file():
            report.add("integration.notification_presentation.file")

        symbol = np_obj.get("symbol")
        if "symbol" not in np_obj or not isinstance(symbol, str) or not SYMBOL_RE.match(symbol):
            report.add("integration.notification_presentation.symbol")

    ad_obj = integration.get("account_deletion")
    if isinstance(ad_obj, dict):
        if "consumer" not in ad_obj or ad_obj["consumer"] != "NC-026":
            report.add("integration.account_deletion.consumer")
        if "blocked_scope" not in ad_obj or ad_obj["blocked_scope"] != "NC-026_ACCOUNT_DELETION":
            report.add("integration.account_deletion.blocked_scope")


def _check_execution_evidence(obj, base_dir, prefix, report):
    """契约 §4「执行证据规则」：command 非空字符串；exit_code 为整数 0（bool
    不接受）；count 为正整数（bool 不接受）；evidence 为存在的文件。"""
    if not _is_nonempty_str(obj.get("command")):
        report.add(f"{prefix}.command")

    exit_code = obj.get("exit_code")
    if not _is_plain_int(exit_code) or exit_code != 0:
        report.add(f"{prefix}.exit_code")

    count = obj.get("count")
    if not _is_plain_int(count) or count <= 0:
        report.add(f"{prefix}.count")

    evidence = obj.get("evidence")
    if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
        report.add(f"{prefix}.evidence")


def check_devices(devices, report):
    """契约 §4：integration.devices，至少两条不满足条件之一只报数组路径本身。"""
    if not isinstance(devices, list):
        report.add("integration.devices")
        return

    ok = len(devices) >= 2
    if ok:
        ids = []
        any_p2p = False
        for d in devices:
            if not isinstance(d, dict):
                ok = False
                break
            if (
                not _is_nonempty_str(d.get("device_id"))
                or not _is_nonempty_str(d.get("platform"))
                or not _is_nonempty_str(d.get("os_version"))
                or not isinstance(d.get("p2p_peer"), bool)
            ):
                ok = False
                break
            ids.append(d["device_id"])
            if d["p2p_peer"] is True:
                any_p2p = True
        if ok and (len(set(ids)) != len(ids) or not any_p2p):
            ok = False

    if not ok:
        report.add("integration.devices")


def check_account_pairs(pairs, report):
    """契约 §4：integration.account_pairs，任一条件不满足只报数组路径本身。"""
    if not isinstance(pairs, list):
        report.add("integration.account_pairs")
        return

    ok = len(pairs) >= 2
    if ok:
        uids, app_ids = [], []
        for p in pairs:
            if not isinstance(p, dict):
                ok = False
                break
            if not _is_nonempty_str(p.get("uid")) or not _is_nonempty_str(p.get("app_user_id")):
                ok = False
                break
            if "token" in p or "password" in p:
                ok = False
                break
            uids.append(p["uid"])
            app_ids.append(p["app_user_id"])
        if ok and (len(set(uids)) != len(uids) or len(set(app_ids)) != len(app_ids)):
            ok = False

    if not ok:
        report.add("integration.account_pairs")


def check_test_runs(test_runs, base_dir, report):
    """契约 §4：integration.test_runs，集合不符只报数组路径；集合相符时逐条
    按执行证据规则报 integration.test_runs[<名>].<字段>。"""
    if not isinstance(test_runs, list):
        report.add("integration.test_runs")
        return

    for item in test_runs:
        if not isinstance(item, dict) or not isinstance(item.get("repository"), str):
            report.add("integration.test_runs")
            return

    names = [item["repository"] for item in test_runs]
    if sorted(names) != sorted(TEST_RUN_REPOS):
        report.add("integration.test_runs")
        return

    by_name = {item["repository"]: item for item in test_runs}
    for name in TEST_RUN_REPOS:
        _check_execution_evidence(by_name[name], base_dir, f"integration.test_runs[{name}]", report)


def check_repositories_tests_integrated(repositories, base_dir, report):
    """契约 §4：repositories[<名>].tests（MIGRATION 除外）。status 不是
    PASSED 只报 .status；PASSED 时按执行证据规则报逐字段路径。"""
    if not isinstance(repositories, list):
        return
    for item in repositories:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if name == "MIGRATION" or name not in REPOSITORY_NAMES:
            continue
        tests = item.get("tests")
        if not isinstance(tests, dict):
            continue  # 已由 §3 报告 repositories[<name>].tests
        prefix = f"repositories[{name}].tests"
        if tests.get("status") != "PASSED":
            report.add(f"{prefix}.status")
        else:
            _check_execution_evidence(tests, base_dir, prefix, report)


def check_account_deletion_integrated(ad, base_dir, report):
    """契约 §5：integration.account_deletion 的 integrated 增量规则。
    UNVERIFIED 时只报 status（闸门）；VERIFIED 时逐个报不合格的验证字段。"""
    if not isinstance(ad, dict):
        return

    if ad.get("status") != "VERIFIED":
        report.add("integration.account_deletion.status")
        return

    source = ad.get("source")
    if not isinstance(source, dict):
        report.add("integration.account_deletion.source")
    else:
        if not _is_nonempty_str(source.get("file")) or not _is_nonempty_str(source.get("symbol")):
            report.add("integration.account_deletion.source")
        if source.get("event_kind") != "ACCOUNT_DELETED":
            report.add("integration.account_deletion.source.event_kind")

    if ad.get("delivery_semantics") not in ("AT_LEAST_ONCE", "EXACTLY_ONCE"):
        report.add("integration.account_deletion.delivery_semantics")

    if not _is_nonempty_str(ad.get("test_command")):
        report.add("integration.account_deletion.test_command")

    exit_code = ad.get("exit_code")
    if not _is_plain_int(exit_code) or exit_code != 0:
        report.add("integration.account_deletion.exit_code")

    count = ad.get("count")
    if not _is_plain_int(count) or count <= 0:
        report.add("integration.account_deletion.count")

    evidence = ad.get("evidence")
    if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
        report.add("integration.account_deletion.evidence")


def check_integrated_extra(data, base_dir, report):
    """契约 §4～§5：integrated 增量规则。调用方须先完成 §2～§3 的共同检查
    （report 已累积其结果）。状态闸门只作用于本函数的增量检查：对象的
    status 不是验证态时，只报 <对象>.status，不再报该对象在本函数中的
    验证字段要求；§3 的半填检查不受本函数影响，独立生效。"""
    scope = data.get("scope")
    if scope not in ("INTEGRATED", "TEST_FIXTURE"):
        report.add("scope")

    client = data.get("client")
    if isinstance(client, dict):
        if client.get("state") != "EXISTING":
            report.add("client.state")
        if client.get("runtime_verified") is not True:
            report.add("client.runtime_verified")

    sdk = data.get("sdk")
    if isinstance(sdk, dict):
        if sdk.get("verification") != "RUNTIME_VERIFIED":
            report.add("sdk.verification")

    if data.get("resolution_status") != "RESOLVED":
        report.add("resolution_status")

    integration = data.get("integration")
    if isinstance(integration, dict):
        backend = integration.get("backend")
        if isinstance(backend, dict):
            if backend.get("status") != "VERIFIED":
                report.add("integration.backend.status")
            else:
                if not _is_nonempty_str(backend.get("project_id")):
                    report.add("integration.backend.project_id")
                ns = backend.get("namespace_prefix")
                if not isinstance(ns, str) or not NAMESPACE_PREFIX_RE.match(ns):
                    report.add("integration.backend.namespace_prefix")
                if backend.get("credential_injection") != "RUNTIME_ENV_VAR":
                    report.add("integration.backend.credential_injection")
                evidence = backend.get("evidence")
                if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
                    report.add("integration.backend.evidence")

        emulator = integration.get("emulator")
        if isinstance(emulator, dict):
            if emulator.get("status") != "VERIFIED":
                report.add("integration.emulator.status")
            else:
                if not _is_nonempty_str(emulator.get("start_command")):
                    report.add("integration.emulator.start_command")
                evidence = emulator.get("evidence")
                if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
                    report.add("integration.emulator.evidence")

        rules = integration.get("rules")
        if isinstance(rules, dict):
            if rules.get("status") != "VERIFIED":
                report.add("integration.rules.status")
            else:
                path_val = rules.get("path")
                if not _is_nonempty_str(path_val) or not _resolve_path(base_dir, path_val).is_file():
                    report.add("integration.rules.path")
                evidence = rules.get("evidence")
                if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
                    report.add("integration.rules.evidence")

        notifier_binding = integration.get("notifier_binding")
        if isinstance(notifier_binding, dict):
            if notifier_binding.get("status") != "VERIFIED":
                report.add("integration.notifier_binding.status")
            else:
                evidence = notifier_binding.get("evidence")
                if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
                    report.add("integration.notifier_binding.evidence")

        notification_presentation = integration.get("notification_presentation")
        if isinstance(notification_presentation, dict):
            if notification_presentation.get("status") != "VERIFIED":
                report.add("integration.notification_presentation.status")
            else:
                evidence = notification_presentation.get("evidence")
                if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
                    report.add("integration.notification_presentation.evidence")

        mute_aggregation = integration.get("mute_aggregation")
        if isinstance(mute_aggregation, dict):
            if mute_aggregation.get("status") != "VERIFIED":
                report.add("integration.mute_aggregation.status")
            else:
                if mute_aggregation.get("content_mute") not in ("SUPPORTED", "UNSUPPORTED_E_WIRING"):
                    report.add("integration.mute_aggregation.content_mute")
                if mute_aggregation.get("aggregation") not in ("SUPPORTED", "UNSUPPORTED_E_WIRING"):
                    report.add("integration.mute_aggregation.aggregation")
                evidence = mute_aggregation.get("evidence")
                if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
                    report.add("integration.mute_aggregation.evidence")

        check_account_deletion_integrated(integration.get("account_deletion"), base_dir, report)
        check_devices(integration.get("devices"), report)
        check_account_pairs(integration.get("account_pairs"), report)
        check_test_runs(integration.get("test_runs"), base_dir, report)

    openapi_validator = data.get("openapi_validator")
    if isinstance(openapi_validator, dict):
        if openapi_validator.get("status") != "VERIFIED":
            report.add("openapi_validator.status")
        else:
            evidence = openapi_validator.get("evidence")
            if not _is_nonempty_str(evidence) or not _resolve_path(base_dir, evidence).is_file():
                report.add("openapi_validator.evidence")

    check_repositories_tests_integrated(data.get("repositories"), base_dir, report)


def run_common_checks(data, base_dir):
    """契约 §2～§3：两种 profile 共同的检查，返回累积的 Report。"""
    report = Report()
    check_top_level(data, base_dir, report)
    check_client(data.get("client"), base_dir, report)
    check_sdk(data.get("sdk"), base_dir, report)
    check_dependencies(data.get("dependencies"), report)
    check_dependency_policy(data.get("dependency_policy"), report)
    check_identity(data.get("identity"), report)
    check_openapi_validator_common(data.get("openapi_validator"), base_dir, report)
    check_md_placeholder(base_dir, report)
    check_repositories(data.get("repositories"), report)
    check_ports(data.get("ports"), base_dir, report)
    check_integration(data.get("integration"), base_dir, report)
    return report


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

    if not isinstance(data, dict):
        print("root")
        return 1

    base_dir = input_path.parent
    report = run_common_checks(data, base_dir)

    if profile == "integrated":
        check_integrated_extra(data, base_dir, report)
        pass_word = "INTEGRATED_STRUCTURE_PASS"
    else:
        pass_word = "LOCAL_PREPARATION_PASS"

    if report.has_errors():
        for path in report.sorted_paths():
            print(path)
        return 1

    scope = data.get("scope")
    suffix = " (TEST_FIXTURE)" if scope == "TEST_FIXTURE" else ""
    print(pass_word + suffix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
