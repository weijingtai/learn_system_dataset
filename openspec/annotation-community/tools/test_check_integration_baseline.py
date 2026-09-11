"""NC-001-01 集成基线校验器单元测试。

判据来源：docs/blackbox-spec-rework/work-items/nc-001/VALIDATION_CONTRACT.md
与同目录 TDD.md。测试通过 subprocess 调用同目录的
check_integration_baseline.py，不导入其内部函数，只断言 CLI 的
退出码与 stdout/stderr。

本文件按 TDD §1 分四步（act/01～act/04）累计追加测试方法，前面步骤已
写入的方法在后续步骤保持不变、继续通过。
"""

import copy
import json
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


if __name__ == "__main__":
    unittest.main()
