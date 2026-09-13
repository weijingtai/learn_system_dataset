"""§20.10 验收判定（规格 §19.0/§20 第 10 条）。

用法::

    python -m pipeline.contract_registry.acceptance [--registry <path>] [--keep]

退出码：3 仅限 PyYAML/jsonschema 不可导入；某项准备或判定抛异常 → 该项 FAIL 宿主准备失败；
        任一 FAIL → 1；无 FAIL 有 BLOCKED → 2；全部 PASS → 0。
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import jsonschema
    import yaml
except ImportError:  # 宿主缺依赖：main 返回 3
    yaml = None
    jsonschema = None

from pipeline.contract_registry.catalog import (
    check_registry,
    interface_fingerprint,
    load_registry,
)
from pipeline.contract_registry.conformance import substitution_report
from pipeline.contract_registry.ports import DirectLedgerAdapter, LedgerdClientAdapter

try:
    from pipeline.orchestrator.suites import stub_edition_suite
except ImportError:  # 宿主缺依赖：main 返回 3
    stub_edition_suite = None

REPO_ROOT = Path(__file__).resolve().parents[2]

CHECKS = (
    "l0_schemas_verified",
    "registry_consistent",
    "storage_port_substitutable",
    "modules_port_clean",
    "other_ports_adapters",
)

LEDGER_INTERNAL_RE = re.compile(r"\.store\b|\.objects\b")
ORCHESTRATOR_SCAN_ROOTS = [REPO_ROOT / "pipeline" / "orchestrator"]

# 每模块最多列出的命中数
_MAX_HITS_PER_MODULE = 5


def _dependencies_available():
    return yaml is not None and jsonschema is not None and stub_edition_suite is not None


def _rel(path):
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def scan_ledger_internals(roots):
    """遍历 ``roots`` 下 ``*.py``（排除任意层级 ``tests/``），返回 ``(路径, 行号)``。"""
    hits = []
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if "tests" in path.relative_to(root).parts:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if LEDGER_INTERNAL_RE.search(line):
                    hits.append((_rel(path), lineno))
    hits.sort()
    return hits


def _l0_schemas_verified():
    process = subprocess.run(
        ["bash", "openspec/schemas/verify.sh"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode == 0:
        return ("PASS", "l0_schemas_verified", "")
    return (
        "FAIL",
        "l0_schemas_verified",
        "verify.sh 退出码 %d" % process.returncode,
    )


def _registry_consistent(registry):
    problems = check_registry(registry, resolve_entries=True)
    if not problems:
        return ("PASS", "registry_consistent", "")
    return (
        "FAIL",
        "registry_consistent",
        "%s: %s（共 %d 项）"
        % (problems[0]["code"], problems[0]["detail"], len(problems)),
    )


def _m2_events(outcome):
    if not outcome:
        return []
    for step in outcome.get("steps", []):
        if step.get("stage") == "m2":
            return list(step.get("event_types") or [])
    return []


def _subsequence(events, expected):
    index = 0
    for event in events:
        if index < len(expected) and event == expected[index]:
            index += 1
    return index == len(expected)


def _storage_port_substitutable(registry, keep):
    def direct_factory():
        root = Path(tempfile.mkdtemp(prefix="cr-storage-"))
        adapter = DirectLedgerAdapter(root)

        def cleanup():
            adapter.close()
            if not keep:
                shutil.rmtree(root, True)

        return adapter, cleanup

    def ledgerd_factory():
        root = Path(tempfile.mkdtemp(prefix="cr-storage-"))
        socket_path = root / "ledger.sock"
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT)
        env["LC_ALL"] = "en_US.UTF-8"
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "pipeline.ledger.ledgerd",
                "--root",
                str(root),
                "--socket",
                str(socket_path),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.time() + 25
        while time.time() < deadline and not socket_path.exists():
            time.sleep(0.05)
        adapter = LedgerdClientAdapter(socket_path)

        def cleanup():
            adapter.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=20)
            for stream in (process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
            if not keep:
                shutil.rmtree(root, True)

        return adapter, cleanup

    fingerprint_value = hashlib.sha256(
        json.dumps(
            sorted(
                interface_fingerprint(registry, module["module_id"])
                for module in registry.modules
            )
        ).encode("utf-8")
    ).hexdigest()
    report = substitution_report(
        "storage",
        {"ledger_direct": direct_factory, "ledgerd_client": ledgerd_factory},
        stub_edition_suite,
        fingerprint=lambda adapter_id: fingerprint_value,
    )
    if not report["substitutable"]:
        return (
            "FAIL",
            "storage_port_substitutable",
            "; ".join(report["problems"]) or "替换判定不成立",
        )
    for adapter_id in report["adapters"]:
        events = _m2_events(report["outcomes"][adapter_id])
        if not _subsequence(events, ("await_human", "human_event", "resume")):
            return (
                "FAIL",
                "storage_port_substitutable",
                "%s 的 m2 事件未覆盖人工恢复路径: %s" % (adapter_id, events),
            )
    return ("PASS", "storage_port_substitutable", "")


def _modules_port_clean(registry):
    hits = scan_ledger_internals(ORCHESTRATOR_SCAN_ROOTS)
    if hits:
        return (
            "FAIL",
            "modules_port_clean",
            "Orchestrator 越过 LedgerPort: %s"
            % ", ".join("%s:%d" % item for item in hits[:10]),
        )

    dirty = []
    for module in registry.modules:
        if module.get("kind") == "stub" or module.get("binding") == "imported":
            continue
        entry = module.get("entry")
        if not isinstance(entry, str) or ":" not in entry:
            continue
        module_path = entry.split(":", 1)[0]
        package_dir = REPO_ROOT.joinpath(*module_path.split(".")[:-1])
        entry_file = _rel(REPO_ROOT.joinpath(*module_path.split(".")).with_suffix(".py"))
        all_hits = scan_ledger_internals([package_dir])
        # 「入口直接访问」：入口文件（registry entry 指向的文件）的命中排在前面，其余按路径序跟随
        module_hits = [hit for hit in all_hits if hit[0] == entry_file] + [
            hit for hit in all_hits if hit[0] != entry_file
        ]
        if module_hits:
            dirty.append((module["module_id"], module_hits))

    if not dirty:
        return ("PASS", "modules_port_clean", "")
    segments = []
    for module_id, module_hits in dirty:
        body = ", ".join(
            "%s:%d" % item for item in module_hits[:_MAX_HITS_PER_MODULE]
        )
        if len(module_hits) > _MAX_HITS_PER_MODULE:
            body += "，等共 %d 处" % len(module_hits)
        segments.append("%s 入口直接访问 Ledger 内部（%s）" % (module_id, body))
    return (
        "BLOCKED",
        "modules_port_clean",
        "前置缺失: Contract Registry；" + "；".join(segments),
    )


def _other_ports_adapters(registry):
    counts = {}
    for port_id in ("ocr", "model", "index"):
        port = registry.ports.get(port_id) or {}
        counts[port_id] = sum(
            1 for adapter in (port.get("adapters") or []) if adapter.get("entry")
        )
    if any(counts[port_id] < 2 for port_id in counts):
        return (
            "BLOCKED",
            "other_ports_adapters",
            "前置缺失: Contract Registry；ocr/model/index 端口 Adapter 数不足 2"
            "（ocr=%d, model=%d, index=%d）"
            % (counts["ocr"], counts["model"], counts["index"]),
        )
    return (
        "BLOCKED",
        "other_ports_adapters",
        "前置缺失: Contract Registry；ocr/model/index 端口未登记一致性套件",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pipeline.contract_registry.acceptance",
        description="§20.10 验收判定（规格 §19.0/§20 第 10 条）",
    )
    parser.add_argument("--registry", default=None)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args(argv)

    if not _dependencies_available():
        print(
            "FAIL contract_registry_acceptance 宿主准备失败: "
            "ImportError: PyYAML/jsonschema 不可导入"
        )
        print("SUMMARY pass=0 fail=1 blocked=0")
        return 3

    registry = load_registry(args.registry) if args.registry else load_registry()
    checks = (
        ("l0_schemas_verified", lambda: _l0_schemas_verified()),
        ("registry_consistent", lambda: _registry_consistent(registry)),
        (
            "storage_port_substitutable",
            lambda: _storage_port_substitutable(registry, args.keep),
        ),
        ("modules_port_clean", lambda: _modules_port_clean(registry)),
        ("other_ports_adapters", lambda: _other_ports_adapters(registry)),
    )

    results = []
    for name, checker in checks:
        try:
            results.append(checker())
        except Exception as exc:  # noqa: BLE001 - 记为 FAIL 而非中断
            results.append(
                ("FAIL", name, "宿主准备失败: %s: %s" % (type(exc).__name__, exc))
            )

    pass_count = fail_count = blocked_count = 0
    for status, name, detail in results:
        if status == "PASS":
            pass_count += 1
            print("PASS %s%s" % (name, (" " + detail) if detail else ""))
        elif status == "FAIL":
            fail_count += 1
            print("FAIL %s %s" % (name, detail))
        else:
            blocked_count += 1
            print("BLOCKED %s %s" % (name, detail))
    print(
        "SUMMARY pass=%d fail=%d blocked=%d" % (pass_count, fail_count, blocked_count)
    )
    if fail_count > 0:
        return 1
    if blocked_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
