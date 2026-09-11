"""NC-001-01 集成基线校验器单元测试。

判据来源：docs/blackbox-spec-rework/work-items/nc-001/VALIDATION_CONTRACT.md
与同目录 TDD.md。测试通过 subprocess 调用同目录的
check_integration_baseline.py，不导入其内部函数，只断言 CLI 的
退出码与 stdout/stderr。

本文件按 TDD §1 分四步（act/01～act/04）累计追加测试方法，前面步骤已
写入的方法在后续步骤保持不变、继续通过。
"""

import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).with_name("check_integration_baseline.py")
REAL_JSON = Path(__file__).resolve().parent.parent / "integration_baseline.json"

# TDD §3.1：必填键全表，逐字抄录，103 条，顺序不限。
REQUIRED_KEY_PATHS = [
    "schema_version",
    "spec_version",
    "task_id",
    "scope",
    "book_work",
    "resolution_status",
    "resolution_evidence",
    "client",
    "sdk",
    "dependencies",
    "dependency_policy",
    "identity",
    "openapi_validator",
    "integration",
    "repositories",
    "ports",
    "client.path",
    "client.package",
    "client.state",
    "client.creation_owner",
    "client.vcs",
    "client.runtime_verified",
    "sdk.flutter",
    "sdk.dart",
    "sdk.evidence",
    "sdk.verification",
    "dependencies.flutter_markdown_plus",
    "dependencies.drift",
    "dependencies.drift_dev",
    "dependencies.drift_flutter",
    "dependencies.sqlite3",
    "dependencies.sqlite3_flutter_libs",
    "dependencies.path_provider",
    "dependencies.build_runner",
    "dependency_policy.offline_failure",
    "dependency_policy.flutter_markdown_plus_rationale",
    "identity.policy",
    "identity.new_identity_system",
    "identity.public_profile_id",
    "openapi_validator.package",
    "openapi_validator.version",
    "openapi_validator.install_command",
    "openapi_validator.offline_failure",
    "openapi_validator.status",
    "openapi_validator.evidence",
    "repositories[SPEC].path",
    "repositories[SPEC].write_policy",
    "repositories[SPEC].git_root",
    "repositories[SPEC].head",
    "repositories[SPEC].dirty_entries",
    "repositories[SPEC].tests",
    "repositories[SPEC].tests.status",
    "repositories[SPEC].tests.reason",
    "repositories[MIGRATION].path",
    "repositories[MIGRATION].status",
    "repositories[MIGRATION].write_policy",
    "ports[HTTP].file",
    "ports[HTTP].symbol",
    "ports[HTTP].kind",
    "integration.devices",
    "integration.account_pairs",
    "integration.test_runs",
    "integration.backend",
    "integration.emulator",
    "integration.rules",
    "integration.notifier_binding",
    "integration.notification_presentation",
    "integration.mute_aggregation",
    "integration.account_deletion",
    "integration.backend.status",
    "integration.backend.project_id",
    "integration.backend.namespace_prefix",
    "integration.backend.credential_injection",
    "integration.backend.evidence",
    "integration.emulator.firestore_config",
    "integration.emulator.auth_config",
    "integration.emulator.project_config",
    "integration.emulator.status",
    "integration.emulator.start_command",
    "integration.emulator.evidence",
    "integration.rules.status",
    "integration.rules.path",
    "integration.rules.evidence",
    "integration.notifier_binding.status",
    "integration.notifier_binding.evidence",
    "integration.notification_presentation.choice",
    "integration.notification_presentation.file",
    "integration.notification_presentation.symbol",
    "integration.notification_presentation.status",
    "integration.notification_presentation.evidence",
    "integration.mute_aggregation.status",
    "integration.mute_aggregation.content_mute",
    "integration.mute_aggregation.aggregation",
    "integration.mute_aggregation.evidence",
    "integration.account_deletion.status",
    "integration.account_deletion.source",
    "integration.account_deletion.delivery_semantics",
    "integration.account_deletion.test_command",
    "integration.account_deletion.exit_code",
    "integration.account_deletion.count",
    "integration.account_deletion.evidence",
    "integration.account_deletion.consumer",
    "integration.account_deletion.blocked_scope",
]


def make_fixture(tmp):
    """在临时目录 tmp 中写出一份键与当前 integration_baseline.json 完全
    相同的 JSON，把全部外部路径改到临时目录内；同目录写一份不含占位符的
    INTEGRATION_BASELINE.md。返回 (data, json_path, md_path)。

    不依赖任何真实外部路径；真实输入只由 TDD 命令 2、3 覆盖。
    """
    tmp = Path(tmp)
    data = json.loads(REAL_JSON.read_text(encoding="utf-8"))

    client_parent = tmp / "client_parent"
    client_parent.mkdir(parents=True, exist_ok=True)
    data["client"]["path"] = str(client_parent / "reading_notes")

    sdk_evidence = tmp / "sdk_evidence.json"
    sdk_evidence.write_text("{}", encoding="utf-8")
    data["sdk"]["evidence"] = str(sdk_evidence)

    for port in data["ports"]:
        port_file = tmp / f"port_{port['name']}.dart"
        port_file.write_text("", encoding="utf-8")
        port["file"] = str(port_file)

    np_file = tmp / "notification_center.dart"
    np_file.write_text("", encoding="utf-8")
    data["integration"]["notification_presentation"]["file"] = str(np_file)

    json_path = tmp / "integration_baseline.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = tmp / "INTEGRATION_BASELINE.md"
    md_path.write_text("# 夹具基线\n\n本文件不含占位符，供单元测试使用。\n", encoding="utf-8")

    return data, json_path, md_path


def dump(data, json_path):
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_checker(json_path, profile):
    return subprocess.run(
        [sys.executable, str(CHECKER), "--profile", profile, "--input", str(json_path)],
        capture_output=True,
        text=True,
    )


def set_nested(data, dotted_path, value):
    """按点号路径设置嵌套字典的值，例如 set_nested(data, 'client.path', 'x')。"""
    parts = dotted_path.split(".")
    node = data
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value


_ARRAY_SEGMENT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\[([A-Za-z0-9_]+)\]$")


def _step_into(node, segment):
    """按契约 §6 写法解析一个路径片段：普通键名或 数组名[定位名]。"""
    m = _ARRAY_SEGMENT_RE.match(segment)
    if m:
        arr = node[m.group(1)]
        return next(it for it in arr if it.get("name") == m.group(2))
    return node[segment]


def delete_key_path(data, dotted_path):
    """按 REQUIRED_KEY_PATHS 的写法删除对应键，用于 test_missing_required_keys。"""
    parts = dotted_path.split(".")
    node = data
    for part in parts[:-1]:
        node = _step_into(node, part)
    last = parts[-1]
    m = _ARRAY_SEGMENT_RE.match(last)
    if m:
        arr = node[m.group(1)]
        item = next(it for it in arr if it.get("name") == m.group(2))
        arr.remove(item)
    else:
        del node[last]


def find_repo(data, name):
    return next(it for it in data["repositories"] if it.get("name") == name)


def find_port(data, name):
    return next(it for it in data["ports"] if it.get("name") == name)


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TopLevelTests(unittest.TestCase):
    def test_local_fixture_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, json_path, _ = make_fixture(tmp)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "LOCAL_PREPARATION_PASS\n")

    def test_local_test_fixture_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_fixture(tmp)
            data["scope"] = "TEST_FIXTURE"
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "LOCAL_PREPARATION_PASS (TEST_FIXTURE)\n")

    def test_cli_errors_exit2(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, json_path, _ = make_fixture(tmp)

            bad_json = Path(tmp) / "bad.json"
            bad_json.write_text("{not valid json", encoding="utf-8")
            r_bad_json = subprocess.run(
                [sys.executable, str(CHECKER), "--profile", "local", "--input", str(bad_json)],
                capture_output=True, text=True,
            )

            missing = Path(tmp) / "does_not_exist.json"
            r_missing_input = subprocess.run(
                [sys.executable, str(CHECKER), "--profile", "local", "--input", str(missing)],
                capture_output=True, text=True,
            )

            r_missing_profile = subprocess.run(
                [sys.executable, str(CHECKER), "--input", str(json_path)],
                capture_output=True, text=True,
            )

            r_unknown_profile = subprocess.run(
                [sys.executable, str(CHECKER), "--profile", "foo", "--input", str(json_path)],
                capture_output=True, text=True,
            )

            for label, r in (
                ("bad_json", r_bad_json),
                ("missing_input", r_missing_input),
                ("missing_profile", r_missing_profile),
                ("unknown_profile", r_unknown_profile),
            ):
                with self.subTest(case=label):
                    self.assertEqual(r.returncode, 2)
                    self.assertEqual(r.stdout, "")
                    self.assertNotIn("Traceback", r.stderr)

    def test_root_not_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            for literal in ("[]", '"x"', "null"):
                json_path = Path(tmp) / "root.json"
                json_path.write_text(literal, encoding="utf-8")
                r = run_checker(json_path, "local")
                with self.subTest(literal=literal):
                    self.assertEqual(r.returncode, 1)
                    self.assertEqual(r.stdout, "root\n")

    def test_top_level_values(self):
        contains_cases = [
            ({"schema_version": True}, "schema_version"),
            ({"schema_version": "1"}, "schema_version"),
            ({"spec_version": "1.4"}, "spec_version"),
            ({"task_id": "NC-002"}, "task_id"),
            ({"scope": "X"}, "scope"),
            ({"book_work": "ACTIVE"}, "book_work"),
            ({"resolution_status": "DONE"}, "resolution_status"),
            ({"resolution_status": "RESOLVED", "resolution_evidence": None}, "resolution_evidence"),
            ({"resolution_status": "RESOLVED", "resolution_evidence": "/no/such/file"}, "resolution_evidence"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for overrides, expect in contains_cases:
                data, json_path, _ = make_fixture(tmp)
                data.update(copy.deepcopy(overrides))
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(overrides=overrides):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(expect, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

            # 父级不是 object 时只报父级路径，不下钻。
            data, json_path, _ = make_fixture(tmp)
            data["client"] = []
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "client\n")


class ClientSdkDependencyTests(unittest.TestCase):
    """TDD §3.3：步骤 2 的 8 个方法（client/sdk/dependencies/dependency_policy/
    identity/openapi_validator 规则与 INTEGRATION_BASELINE.md 占位扫描）。"""

    def test_planned_new_rules(self):
        # creation_owner 不是 NC-004
        with tempfile.TemporaryDirectory() as tmp1:
            data, json_path, _ = make_fixture(tmp1)
            data["client"]["creation_owner"] = "NC-005"
            dump(data, json_path)
            before = sorted(str(p.relative_to(tmp1)) for p in Path(tmp1).rglob("*"))
            r = run_checker(json_path, "local")
            after = sorted(str(p.relative_to(tmp1)) for p in Path(tmp1).rglob("*"))
            self.assertEqual(r.returncode, 1)
            self.assertIn("client.creation_owner", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)
            self.assertEqual(before, after)

        # path 的父目录不存在
        with tempfile.TemporaryDirectory() as tmp2:
            data, json_path, _ = make_fixture(tmp2)
            data["client"]["path"] = str(Path(tmp2) / "no_such_parent" / "reading_notes")
            dump(data, json_path)
            before = sorted(str(p.relative_to(tmp2)) for p in Path(tmp2).rglob("*"))
            r = run_checker(json_path, "local")
            after = sorted(str(p.relative_to(tmp2)) for p in Path(tmp2).rglob("*"))
            self.assertEqual(r.returncode, 1)
            self.assertIn("client.path", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)
            self.assertEqual(before, after)

        # path 本身已存在
        with tempfile.TemporaryDirectory() as tmp3:
            data, json_path, _ = make_fixture(tmp3)
            Path(data["client"]["path"]).mkdir(parents=True, exist_ok=True)
            dump(data, json_path)
            before = sorted(str(p.relative_to(tmp3)) for p in Path(tmp3).rglob("*"))
            r = run_checker(json_path, "local")
            after = sorted(str(p.relative_to(tmp3)) for p in Path(tmp3).rglob("*"))
            self.assertEqual(r.returncode, 1)
            self.assertIn("client.state", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)
            self.assertEqual(before, after)

    def test_existing_client_rules(self):
        for missing in ("pubspec.yaml", "lib", "git"):
            with tempfile.TemporaryDirectory() as tmp:
                data, json_path, _ = make_fixture(tmp)
                existing_dir = Path(tmp) / "existing_client"
                existing_dir.mkdir(parents=True, exist_ok=True)
                (existing_dir / "pubspec.yaml").write_text("name: reading_notes\n", encoding="utf-8")
                (existing_dir / "lib").mkdir(exist_ok=True)
                (existing_dir / ".git").mkdir(exist_ok=True)
                if missing == "pubspec.yaml":
                    (existing_dir / "pubspec.yaml").unlink()
                elif missing == "lib":
                    (existing_dir / "lib").rmdir()
                elif missing == "git":
                    (existing_dir / ".git").rmdir()
                data["client"]["state"] = "EXISTING"
                data["client"]["path"] = str(existing_dir)
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(missing=missing):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn("client.path", r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

    def test_client_and_identity_values(self):
        cases = [
            ("client.package", "notes", "client.package"),
            ("client.state", "OTHER", "client.state"),
            ("client.vcs", "SUBMODULE", "client.vcs"),
            ("client.runtime_verified", "no", "client.runtime_verified"),
            ("client.path", "", "client.path"),
            ("sdk.verification", "X", "sdk.verification"),
            ("sdk.dart", "3.12.3", "sdk.dart"),
            ("identity.policy", "X", "identity.policy"),
            ("identity.public_profile_id", "", "identity.public_profile_id"),
            ("dependency_policy.offline_failure", "IGNORE", "dependency_policy.offline_failure"),
            ("dependency_policy.flutter_markdown_plus_rationale", "", "dependency_policy.flutter_markdown_plus_rationale"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for dotted, value, expect in cases:
                data, json_path, _ = make_fixture(tmp)
                set_nested(data, dotted, value)
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(dotted=dotted):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(expect, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

    def test_sdk_evidence_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_fixture(tmp)
            Path(data["sdk"]["evidence"]).unlink()
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("sdk.evidence", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

    def test_pins_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_fixture(tmp)
            data["dependencies"]["drift"] = "2.34.0"
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("dependencies.drift", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_fixture(tmp)
            data["dependencies"]["extra_pkg"] = "1.0.0"
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("dependencies", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_fixture(tmp)
            data["sdk"]["flutter"] = "3.44.7"
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("sdk.flutter", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

    def test_identity_and_book_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_fixture(tmp)
            data["identity"]["new_identity_system"] = True
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("identity.new_identity_system", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_fixture(tmp)
            data["identity"]["new_identity_system"] = "false"
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("identity.new_identity_system", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_fixture(tmp)
            data["book_work"] = "ACTIVE"
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("book_work", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

    def test_openapi_validator_rules(self):
        cases = [
            ({"package": "x"}, "openapi_validator.package"),
            ({"version": "0.8.0"}, "openapi_validator.version"),
            ({"install_command": ""}, "openapi_validator.install_command"),
            ({"offline_failure": "IGNORE"}, "openapi_validator.offline_failure"),
            ({"status": "INSTALLED"}, "openapi_validator.status"),
            ({"evidence": "x"}, "openapi_validator.evidence"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for overrides, expect in cases:
                data, json_path, _ = make_fixture(tmp)
                data["openapi_validator"].update(copy.deepcopy(overrides))
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(overrides=overrides):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(expect, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

    def test_placeholder_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, md_path = make_fixture(tmp)
            md_path.write_text(md_path.read_text(encoding="utf-8") + "\nTBD\n", encoding="utf-8")
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("INTEGRATION_BASELINE.md", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

            data, json_path, md_path = make_fixture(tmp)
            md_path.write_text(md_path.read_text(encoding="utf-8") + "\n待定\n", encoding="utf-8")
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("INTEGRATION_BASELINE.md", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

            data, json_path, md_path = make_fixture(tmp)
            md_path.unlink()
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("INTEGRATION_BASELINE.md", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)


class RepositoriesPortsIntegrationTests(unittest.TestCase):
    """TDD §3.4：步骤 3 的 9 个方法（repositories、ports、integration 各对象
    规则与必填键全表）。"""

    def test_missing_required_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in REQUIRED_KEY_PATHS:
                data, json_path, _ = make_fixture(tmp)
                delete_key_path(data, path)
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(path=path):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(path, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

            # 两个定位键用例
            data, json_path, _ = make_fixture(tmp)
            del find_repo(data, "SPEC")["name"]
            dump(data, json_path)
            r = run_checker(json_path, "local")
            with self.subTest(path="repositories[SPEC].name"):
                self.assertEqual(r.returncode, 1)
                self.assertIn("repositories", r.stdout.splitlines())
                self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_fixture(tmp)
            del find_port(data, "HTTP")["name"]
            dump(data, json_path)
            r = run_checker(json_path, "local")
            with self.subTest(path="ports[HTTP].name"):
                self.assertEqual(r.returncode, 1)
                self.assertIn("ports", r.stdout.splitlines())
                self.assertNotIn("PASS", r.stdout)

    def test_repositories_rules(self):
        contains_cases = [
            (lambda d: find_repo(d, "SPEC").__setitem__("head", "ABC"), "repositories[SPEC].head"),
            (lambda d: find_repo(d, "SPEC").__setitem__("head", "A" * 40), "repositories[SPEC].head"),
            (lambda d: find_repo(d, "SPEC").__setitem__("dirty_entries", True), "repositories[SPEC].dirty_entries"),
            (lambda d: find_repo(d, "SPEC").__setitem__("dirty_entries", -1), "repositories[SPEC].dirty_entries"),
            (lambda d: find_repo(d, "SPEC").__setitem__("write_policy", "WRITE_ALL"), "repositories[SPEC].write_policy"),
            (lambda d: find_repo(d, "NOTIFIER").__setitem__("write_policy", "PER_TASK_WHITELIST"),
             "repositories[NOTIFIER].write_policy"),
            (lambda d: find_repo(d, "MIGRATION").__setitem__("status", "AVAILABLE"), "repositories[MIGRATION].status"),
            (lambda d: find_repo(d, "MIGRATION").__setitem__("write_policy", "PER_TASK_WHITELIST"),
             "repositories[MIGRATION].write_policy"),
            (lambda d: find_repo(d, "SPEC")["tests"].__setitem__("status", "SKIPPED"),
             "repositories[SPEC].tests.status"),
            (lambda d: (find_repo(d, "SPEC")["tests"].__setitem__("status", "NOT_RUN"),
                        find_repo(d, "SPEC")["tests"].__setitem__("reason", "")),
             "repositories[SPEC].tests.reason"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for mutate, expect in contains_cases:
                data, json_path, _ = make_fixture(tmp)
                mutate(data)
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(expect=expect):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(expect, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_fixture(tmp)
            data["repositories"] = [it for it in data["repositories"] if it["name"] != "STORAGE"]
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "repositories\n")

            data, json_path, _ = make_fixture(tmp)
            data["repositories"].append(copy.deepcopy(find_repo(data, "SPEC")))
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "repositories\n")

            data, json_path, _ = make_fixture(tmp)
            data["repositories"][0] = "x"
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "repositories\n")

    def test_ports_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_fixture(tmp)
            data["ports"] = [it for it in data["ports"] if it["name"] != "MENTION"]
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "ports\n")

            contains_cases = [
                (lambda d: find_port(d, "HTTP").__setitem__("symbol", "42"), "ports[HTTP].symbol"),
                (lambda d: find_port(d, "HTTP").__setitem__("symbol", "a.dart:42"), "ports[HTTP].symbol"),
                (lambda d: find_port(d, "HTTP").__setitem__("file", "/no/such/file.dart"), "ports[HTTP].file"),
                (lambda d: find_port(d, "HTTP").__setitem__("kind", "MOCK"), "ports[HTTP].kind"),
            ]
            for mutate, expect in contains_cases:
                data, json_path, _ = make_fixture(tmp)
                mutate(data)
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(expect=expect):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(expect, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_fixture(tmp)
            data["ports"].append(copy.deepcopy(find_port(data, "HTTP")))
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "ports\n")

    def test_emulator_constants(self):
        cases = [
            ({"firestore_config": ""}, "integration.emulator.firestore_config"),
            ({"auth_config": None}, "integration.emulator.auth_config"),
            ({"project_config": 123}, "integration.emulator.project_config"),
            ({"status": "RUNNING"}, "integration.emulator.status"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for overrides, expect in cases:
                data, json_path, _ = make_fixture(tmp)
                data["integration"]["emulator"].update(copy.deepcopy(overrides))
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(overrides=overrides):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(expect, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

    def test_notification_presentation_rules(self):
        cases = [
            ({"choice": "OTHER"}, "integration.notification_presentation.choice"),
            ({"file": "/no/such/file.dart"}, "integration.notification_presentation.file"),
            ({"symbol": "42"}, "integration.notification_presentation.symbol"),
            ({"status": "DONE"}, "integration.notification_presentation.status"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for overrides, expect in cases:
                data, json_path, _ = make_fixture(tmp)
                data["integration"]["notification_presentation"].update(copy.deepcopy(overrides))
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(overrides=overrides):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(expect, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

    def test_account_deletion_constants(self):
        cases = [
            ({"consumer": "NC-025"}, "integration.account_deletion.consumer"),
            ({"blocked_scope": "X"}, "integration.account_deletion.blocked_scope"),
            ({"status": "DONE"}, "integration.account_deletion.status"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for overrides, expect in cases:
                data, json_path, _ = make_fixture(tmp)
                data["integration"]["account_deletion"].update(copy.deepcopy(overrides))
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(overrides=overrides):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(expect, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

    def test_account_deletion_unverified_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_fixture(tmp)
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "LOCAL_PREPARATION_PASS\n")

            data["integration"]["account_deletion"]["test_command"] = "x"
            dump(data, json_path)
            r = run_checker(json_path, "local")
            self.assertEqual(r.returncode, 1)
            self.assertIn("integration.account_deletion.test_command", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

    def test_half_filled_unverified_rejected(self):
        cases = [
            (("rules", "path", "x"), "integration.rules.path"),
            (("backend", "project_id", "p"), "integration.backend.project_id"),
            (("mute_aggregation", "aggregation", "SUPPORTED"), "integration.mute_aggregation.aggregation"),
            (("backend", "status", "VERIFYING"), "integration.backend.status"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for (obj_name, field, value), expect in cases:
                data, json_path, _ = make_fixture(tmp)
                data["integration"][obj_name][field] = value
                dump(data, json_path)
                r = run_checker(json_path, "local")
                with self.subTest(obj_name=obj_name, field=field):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(expect, r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

    def test_inputs_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, md_path = make_fixture(tmp)
            before_json_hash = sha256_of(json_path)
            before_md_hash = sha256_of(md_path)
            before_listing = sorted(str(p.relative_to(tmp)) for p in Path(tmp).rglob("*"))

            run_checker(json_path, "local")
            run_checker(json_path, "integrated")

            after_json_hash = sha256_of(json_path)
            after_md_hash = sha256_of(md_path)
            after_listing = sorted(str(p.relative_to(tmp)) for p in Path(tmp).rglob("*"))

            self.assertEqual(before_json_hash, after_json_hash)
            self.assertEqual(before_md_hash, after_md_hash)
            self.assertEqual(before_listing, after_listing)


# TDD §3.1：契约 §7 的期望输出（23 行，逐字），只在测试文件字面量写出，不从
# VALIDATION_CONTRACT.md 或校验器输出反推。
GOLDEN_23 = [
    "client.runtime_verified",
    "client.state",
    "integration.account_deletion.status",
    "integration.account_pairs",
    "integration.backend.status",
    "integration.devices",
    "integration.emulator.status",
    "integration.mute_aggregation.status",
    "integration.notification_presentation.status",
    "integration.notifier_binding.status",
    "integration.rules.status",
    "integration.test_runs",
    "openapi_validator.status",
    "repositories[NOTIFICATION].tests.status",
    "repositories[NOTIFIER].tests.status",
    "repositories[REST].tests.status",
    "repositories[SERVER].tests.status",
    "repositories[SOCIAL].tests.status",
    "repositories[SPEC].tests.status",
    "repositories[STORAGE].tests.status",
    "resolution_status",
    "scope",
    "sdk.verification",
]

TEST_RUN_REPOS = ["SPEC", "STORAGE", "SOCIAL", "NOTIFICATION", "REST", "SERVER", "NOTIFIER"]


def make_verified_fixture(tmp):
    """在 make_fixture 基础上构造完整验证态夹具（scope=TEST_FIXTURE），
    供 integrated 档结构通过测试使用。取值按 TDD §3.5 逐字写死。
    返回 (data, json_path, md_path)。"""
    data, json_path, md_path = make_fixture(tmp)
    tmp = Path(tmp)

    data["scope"] = "TEST_FIXTURE"

    existing_dir = tmp / "existing_client"
    existing_dir.mkdir(parents=True, exist_ok=True)
    (existing_dir / "pubspec.yaml").write_text("name: reading_notes\n", encoding="utf-8")
    (existing_dir / "lib").mkdir(exist_ok=True)
    (existing_dir / ".git").mkdir(exist_ok=True)
    data["client"]["state"] = "EXISTING"
    data["client"]["path"] = str(existing_dir)
    data["client"]["runtime_verified"] = True

    data["sdk"]["verification"] = "RUNTIME_VERIFIED"

    resolution_evidence = tmp / "resolution_evidence.txt"
    resolution_evidence.write_text("resolved", encoding="utf-8")
    data["resolution_status"] = "RESOLVED"
    data["resolution_evidence"] = str(resolution_evidence)

    openapi_evidence = tmp / "openapi_evidence.txt"
    openapi_evidence.write_text("verified", encoding="utf-8")
    data["openapi_validator"]["status"] = "VERIFIED"
    data["openapi_validator"]["evidence"] = str(openapi_evidence)

    backend_evidence = tmp / "backend_evidence.txt"
    backend_evidence.write_text("backend", encoding="utf-8")
    data["integration"]["backend"] = {
        "status": "VERIFIED",
        "project_id": "demo-xuan-test",
        "namespace_prefix": "nc_20260910_ab12cd",
        "credential_injection": "RUNTIME_ENV_VAR",
        "evidence": str(backend_evidence),
    }

    emulator_evidence = tmp / "emulator_evidence.txt"
    emulator_evidence.write_text("emulator", encoding="utf-8")
    data["integration"]["emulator"]["status"] = "VERIFIED"
    data["integration"]["emulator"]["start_command"] = "firebase emulators:start --only firestore,auth"
    data["integration"]["emulator"]["evidence"] = str(emulator_evidence)

    rules_path = tmp / "rules_path.txt"
    rules_path.write_text("rules", encoding="utf-8")
    rules_evidence = tmp / "rules_evidence.txt"
    rules_evidence.write_text("rules-evidence", encoding="utf-8")
    data["integration"]["rules"] = {
        "status": "VERIFIED",
        "path": str(rules_path),
        "evidence": str(rules_evidence),
    }

    notifier_evidence = tmp / "notifier_binding_evidence.txt"
    notifier_evidence.write_text("notifier", encoding="utf-8")
    data["integration"]["notifier_binding"] = {
        "status": "VERIFIED",
        "evidence": str(notifier_evidence),
    }

    np_evidence = tmp / "notification_presentation_evidence.txt"
    np_evidence.write_text("np", encoding="utf-8")
    data["integration"]["notification_presentation"]["status"] = "VERIFIED"
    data["integration"]["notification_presentation"]["evidence"] = str(np_evidence)

    mute_evidence = tmp / "mute_aggregation_evidence.txt"
    mute_evidence.write_text("mute", encoding="utf-8")
    data["integration"]["mute_aggregation"] = {
        "status": "VERIFIED",
        "content_mute": "SUPPORTED",
        "aggregation": "UNSUPPORTED_E_WIRING",
        "evidence": str(mute_evidence),
    }

    ad_source_file = tmp / "auth_coordinator.dart"
    ad_source_file.write_text("class AuthCoordinator {}\n", encoding="utf-8")
    ad_evidence = tmp / "account_deletion_evidence.txt"
    ad_evidence.write_text("account-deletion", encoding="utf-8")
    data["integration"]["account_deletion"].update({
        "status": "VERIFIED",
        "source": {
            "file": str(ad_source_file),
            "symbol": "AuthCoordinator.deleteAccount",
            "event_kind": "ACCOUNT_DELETED",
        },
        "delivery_semantics": "AT_LEAST_ONCE",
        "test_command": "python3 -m unittest",
        "exit_code": 0,
        "count": 1,
        "evidence": str(ad_evidence),
    })

    data["integration"]["devices"] = [
        {"device_id": "device-a", "platform": "android", "os_version": "14", "p2p_peer": True},
        {"device_id": "device-b", "platform": "ios", "os_version": "17", "p2p_peer": False},
    ]

    data["integration"]["account_pairs"] = [
        {"uid": "uid-1", "app_user_id": "app-user-1"},
        {"uid": "uid-2", "app_user_id": "app-user-2"},
    ]

    test_runs = []
    for name in TEST_RUN_REPOS:
        evidence = tmp / f"test_run_{name}_evidence.txt"
        evidence.write_text("test-run", encoding="utf-8")
        test_runs.append({
            "repository": name,
            "command": "flutter test",
            "exit_code": 0,
            "count": 1,
            "evidence": str(evidence),
        })
    data["integration"]["test_runs"] = test_runs

    for repo in data["repositories"]:
        if repo["name"] == "MIGRATION":
            continue
        evidence = tmp / f"repo_tests_{repo['name']}_evidence.txt"
        evidence.write_text("repo-tests", encoding="utf-8")
        repo["tests"] = {
            "status": "PASSED",
            "command": "flutter test",
            "exit_code": 0,
            "count": 1,
            "evidence": str(evidence),
        }

    dump(data, json_path)
    return data, json_path, md_path


class IntegratedProfileTests(unittest.TestCase):
    """TDD §3.5：步骤 4 的 10 个方法（契约 §4～§7）。"""

    def test_integrated_current_golden(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_fixture(tmp)
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "\n".join(GOLDEN_23) + "\n")

    def test_integrated_fixture_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_verified_fixture(tmp)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "INTEGRATED_STRUCTURE_PASS (TEST_FIXTURE)\n")

    def test_integrated_fixture_evidence_removed(self):
        cases = [
            (lambda d: d["integration"]["backend"]["evidence"], "integration.backend.evidence"),
            (lambda d: d["integration"]["emulator"]["evidence"], "integration.emulator.evidence"),
            (lambda d: d["integration"]["rules"]["path"], "integration.rules.path"),
            (lambda d: d["integration"]["rules"]["evidence"], "integration.rules.evidence"),
            (lambda d: d["integration"]["notifier_binding"]["evidence"], "integration.notifier_binding.evidence"),
            (lambda d: d["integration"]["notification_presentation"]["evidence"],
             "integration.notification_presentation.evidence"),
            (lambda d: d["integration"]["mute_aggregation"]["evidence"], "integration.mute_aggregation.evidence"),
            (lambda d: d["openapi_validator"]["evidence"], "openapi_validator.evidence"),
            (lambda d: d["integration"]["account_deletion"]["evidence"], "integration.account_deletion.evidence"),
            (lambda d: find_repo(d, "STORAGE")["tests"]["evidence"], "repositories[STORAGE].tests.evidence"),
            (lambda d: next(t for t in d["integration"]["test_runs"] if t["repository"] == "SERVER")["evidence"],
             "integration.test_runs[SERVER].evidence"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for get_path, expect in cases:
                data, json_path, _ = make_verified_fixture(tmp)
                evidence_path = Path(get_path(data))
                evidence_path.unlink()
                dump(data, json_path)
                r = run_checker(json_path, "integrated")
                with self.subTest(expect=expect):
                    self.assertEqual(r.returncode, 1)
                    self.assertEqual(r.stdout, expect + "\n")

    def test_fake_test_pass_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_fixture(tmp)
            find_repo(data, "STORAGE")["tests"]["status"] = "PASSED"
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            lines = r.stdout.splitlines()
            for suffix in (".command", ".count", ".evidence", ".exit_code"):
                self.assertIn(f"repositories[STORAGE].tests{suffix}", lines)
            self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_verified_fixture(tmp)
            find_repo(data, "STORAGE")["tests"]["exit_code"] = True
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertIn("repositories[STORAGE].tests.exit_code", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_verified_fixture(tmp)
            find_repo(data, "STORAGE")["tests"]["count"] = 0
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertIn("repositories[STORAGE].tests.count", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

    def test_integrated_half_filled_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_fixture(tmp)
            data["integration"]["rules"]["path"] = "x"
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            lines = r.stdout.splitlines()
            self.assertIn("integration.rules.path", lines)
            self.assertIn("integration.rules.status", lines)
            self.assertNotIn("PASS", r.stdout)

    def test_account_deletion_verified_missing_fields(self):
        fields = ["source", "delivery_semantics", "test_command", "exit_code", "count", "evidence"]
        with tempfile.TemporaryDirectory() as tmp:
            for field in fields:
                data, json_path, _ = make_verified_fixture(tmp)
                data["integration"]["account_deletion"][field] = None
                dump(data, json_path)
                r = run_checker(json_path, "integrated")
                with self.subTest(field=field):
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(f"integration.account_deletion.{field}", r.stdout.splitlines())
                    self.assertNotIn("PASS", r.stdout)

    def test_account_deletion_kind_and_delivery_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_verified_fixture(tmp)
            data["integration"]["account_deletion"]["source"]["event_kind"] = "sign_out"
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertIn("integration.account_deletion.source.event_kind", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_verified_fixture(tmp)
            data["integration"]["account_deletion"]["delivery_semantics"] = "BEST_EFFORT"
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertIn("integration.account_deletion.delivery_semantics", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

            data, json_path, _ = make_verified_fixture(tmp)
            data["integration"]["account_deletion"]["source"] = "x"
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertIn("integration.account_deletion.source", r.stdout.splitlines())
            self.assertNotIn("PASS", r.stdout)

    def test_devices_and_pairs_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_verified_fixture(tmp)
            data["integration"]["devices"] = data["integration"]["devices"][:1]
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.devices\n")

            data, json_path, _ = make_verified_fixture(tmp)
            data["integration"]["devices"][1]["device_id"] = data["integration"]["devices"][0]["device_id"]
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.devices\n")

            data, json_path, _ = make_verified_fixture(tmp)
            for dvc in data["integration"]["devices"]:
                dvc["p2p_peer"] = False
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.devices\n")

            data, json_path, _ = make_verified_fixture(tmp)
            data["integration"]["devices"][0]["p2p_peer"] = "yes"
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.devices\n")

            data, json_path, _ = make_verified_fixture(tmp)
            data["integration"]["account_pairs"][0]["token"] = "secret"
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.account_pairs\n")

            data, json_path, _ = make_verified_fixture(tmp)
            data["integration"]["account_pairs"][1]["uid"] = data["integration"]["account_pairs"][0]["uid"]
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.account_pairs\n")

    def test_test_runs_set_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, json_path, _ = make_verified_fixture(tmp)
            data["integration"]["test_runs"] = [
                t for t in data["integration"]["test_runs"] if t["repository"] != "SPEC"
            ]
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.test_runs\n")

            data, json_path, _ = make_verified_fixture(tmp)
            next(t for t in data["integration"]["test_runs"] if t["repository"] == "SERVER")["exit_code"] = 1
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.test_runs[SERVER].exit_code\n")

            data, json_path, _ = make_verified_fixture(tmp)
            next(t for t in data["integration"]["test_runs"] if t["repository"] == "SERVER")["command"] = ""
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.test_runs[SERVER].command\n")

            data, json_path, _ = make_verified_fixture(tmp)
            next(t for t in data["integration"]["test_runs"] if t["repository"] == "SERVER")["count"] = 0
            dump(data, json_path)
            r = run_checker(json_path, "integrated")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "integration.test_runs[SERVER].count\n")

    def test_integrated_value_rules(self):
        cases = [
            (lambda d: d["integration"]["backend"].__setitem__("namespace_prefix", "nc_2026_ab"),
             "integration.backend.namespace_prefix"),
            (lambda d: d["integration"]["backend"].__setitem__("namespace_prefix", "NC_20260910_ab12"),
             "integration.backend.namespace_prefix"),
            (lambda d: d["integration"]["backend"].__setitem__("credential_injection", "FILE"),
             "integration.backend.credential_injection"),
            (lambda d: d["integration"]["backend"].__setitem__("project_id", ""),
             "integration.backend.project_id"),
            (lambda d: d["integration"]["emulator"].__setitem__("start_command", ""),
             "integration.emulator.start_command"),
            (lambda d: d["integration"]["mute_aggregation"].__setitem__("content_mute", "YES"),
             "integration.mute_aggregation.content_mute"),
            (lambda d: d["integration"]["mute_aggregation"].__setitem__("aggregation", "PARTIAL"),
             "integration.mute_aggregation.aggregation"),
            (lambda d: d.__setitem__("sdk", []), "sdk"),
            (lambda d: d["integration"].__setitem__("devices", {}), "integration.devices"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for mutate, expect in cases:
                data, json_path, _ = make_verified_fixture(tmp)
                mutate(data)
                dump(data, json_path)
                r = run_checker(json_path, "integrated")
                with self.subTest(expect=expect):
                    self.assertEqual(r.returncode, 1)
                    self.assertEqual(r.stdout, expect + "\n")


if __name__ == "__main__":
    unittest.main()
