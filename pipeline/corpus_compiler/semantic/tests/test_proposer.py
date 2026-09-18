from pipeline.corpus_compiler.semantic.prompt_registry import PromptProfile, PromptRegistry, get_default_registry
"""act/04 Proposer Adapter（prompt 模板、请求体隔离、录制回放、禁用桩、零网络）具名用例。

synthetic_fixture: true —— 录制内容为内联合成数据，标 synthetic: true，不写 fixture 目录（P4）。
P6 红线：本组零模型调用、零网络；`socket` 只在测试里被**拦截**用于取证。
"""

import hashlib
import json
import os
import socket
import unittest
from pathlib import Path
from unittest import mock

from pipeline.corpus_compiler.semantic.proposer import (
    LIVE_PROPOSER_ENV_FLAG,
    PROMPT_TEMPLATE,
    PROMPT_TEMPLATE_ID,
    PROMPT_TEMPLATE_SHA256,
    LiveProposer,
    ModelCallDisabled,
    RecordingMiss,
    RecordingSchemaError,
    ReplayProposer,
    build_request,
    load_recordings,
)
from pipeline.corpus_compiler.semantic.proposals import parse_proposal

WORK = "qianyuan"
MODEL = {"name": "replay", "version": "0"}

WINDOW_A_TEXT = "天地玄黄宇宙洪荒日月盈昃"  # 12 字符
WINDOW_B_TEXT = "寒来暑往秋收冬藏闰余成岁"  # 12 字符
SEGMENTS_A = [[0, 6], [6, 12]]
SEGMENTS_B = [[0, 12]]
OPPONENT_SLOT_CONTENT = "对端 slot 的提议内容不得泄漏"


def make_window(window_id, text, raw_start):
    """构造一个窗口字典（键序与 offset_rules.select_text_windows 一致）。"""
    return {
        "window_id": window_id,
        "span_id": "ss_%s_ed01_o%07d" % (WORK, raw_start),
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "raw_start": raw_start,
        "raw_end": raw_start + len(text),
    }


def make_window_a():
    return make_window("%s_w001" % WORK, WINDOW_A_TEXT, 0)


def make_window_b():
    return make_window("%s_w002" % WORK, WINDOW_B_TEXT, 12)


def response_bytes(segments, *, reason_prefix="r"):
    items = [
        {
            "start_offset": start,
            "end_offset": end,
            "reason": "%s%d" % (reason_prefix, index),
        }
        for index, (start, end) in enumerate(segments)
    ]
    return json.dumps({"segments": items}, ensure_ascii=False)


def recordings_doc(*, synthetic=True, template_id=PROMPT_TEMPLATE_ID, schema="m3_boundary_recordings/1"):
    """合成录制文档（JSON 为 YAML 子集，load_recordings 两种都吃）。"""
    return {
        "schema": schema,
        "synthetic": synthetic,
        "template_id": template_id,
        "recordings": [
            {
                "window_id": "%s_w001" % WORK,
                "slot": "a",
                "response": response_bytes(SEGMENTS_A, reason_prefix="a"),
            },
            {
                "window_id": "%s_w001" % WORK,
                "slot": "b",
                "response": response_bytes(SEGMENTS_A, reason_prefix="b"),
            },
            {
                "window_id": "%s_w002" % WORK,
                "slot": "a",
                "response": response_bytes(SEGMENTS_B, reason_prefix="a"),
            },
            {
                "window_id": "%s_w002" % WORK,
                "slot": "b",
                "response": response_bytes(SEGMENTS_B, reason_prefix="b"),
            },
        ],
    }


def recordings_bytes(**kwargs):
    return json.dumps(recordings_doc(**kwargs), ensure_ascii=False).encode("utf-8")


class TestPromptTemplateAndRequest(unittest.TestCase):
    """模板常量与请求体隔离（§12.2）。"""

    def test_template_sha256_matches_constant(self):
        """PROMPT_TEMPLATE 的 sha256 必须与常量 PROMPT_TEMPLATE_SHA256 一致（防模板漂移）。"""
        self.assertEqual(PROMPT_TEMPLATE_ID, "m3_boundary_v1")
        self.assertEqual(
            hashlib.sha256(PROMPT_TEMPLATE.encode("utf-8")).hexdigest(),
            PROMPT_TEMPLATE_SHA256,
        )
        self.assertIn("JSON", PROMPT_TEMPLATE)
        self.assertIn("不得复述原文", PROMPT_TEMPLATE)

    def test_request_bytes_deterministic(self):
        """同一 (slot, model, window) 反复构造，请求体字节完全一致。"""
        first = build_request(slot="a", model=MODEL, window=make_window_a())
        second = build_request(slot="a", model=MODEL, window=make_window_a())
        self.assertIsInstance(first, bytes)
        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest()
        )
        # 换 slot 必须换请求体
        self.assertNotEqual(
            first, build_request(slot="b", model=MODEL, window=make_window_a())
        )

    def test_request_contains_only_current_window_text(self):
        """护栏：请求体只含本窗口原文，绝不泄漏其它窗口或对端 slot 内容（§12.2）。"""
        request_a = build_request(slot="a", model=MODEL, window=make_window_a())
        request_b = build_request(slot="b", model=MODEL, window=make_window_b())

        self.assertIn(WINDOW_A_TEXT.encode("utf-8"), request_a)
        self.assertNotIn(WINDOW_A_TEXT.encode("utf-8"), request_b)
        self.assertIn(WINDOW_B_TEXT.encode("utf-8"), request_b)
        self.assertNotIn(WINDOW_B_TEXT.encode("utf-8"), request_a)

        # 另一窗口的 id 不得出现在本窗口请求体中
        self.assertNotIn(b"w002", request_a)
        self.assertNotIn(b"w001", request_b)

        # 对端 slot 的提议内容不得出现在任何请求体中
        opponent = OPPONENT_SLOT_CONTENT.encode("utf-8")
        self.assertNotIn(opponent, request_a)
        self.assertNotIn(opponent, request_b)

        # 请求体不得夹带任何其它窗口的文本集合
        payload = json.loads(request_a.decode("utf-8"))
        self.assertEqual(payload["slot"], "a")
        self.assertNotIn("windows", payload)
        self.assertNotIn("other_slot", payload)

        with self.assertRaises(ValueError):
            build_request(slot="c", model=MODEL, window=make_window_a())


class TestLoadRecordings(unittest.TestCase):
    """录制文档校验。"""

    def test_load_recordings_valid(self):
        """合法录制（schema/synthetic/template_id 齐备）返回解析后的字典。"""
        doc = load_recordings(recordings_bytes())
        self.assertIsInstance(doc, dict)
        self.assertEqual(doc["schema"], "m3_boundary_recordings/1")
        self.assertIs(doc["synthetic"], True)
        self.assertEqual(doc["template_id"], PROMPT_TEMPLATE_ID)
        self.assertEqual(len(doc["recordings"]), 4)

    def test_load_recordings_rejects_synthetic_false(self):
        """synthetic 非 True（冒充真实模型输出）必须拒绝。"""
        with self.assertRaises(RecordingSchemaError):
            load_recordings(recordings_bytes(synthetic=False))

        with self.assertRaises(RecordingSchemaError):
            load_recordings(recordings_bytes(schema="m3_boundary_recordings/2"))

        with self.assertRaises(RecordingSchemaError):
            load_recordings(recordings_bytes(template_id="m3_boundary_v2"))

        with self.assertRaises(RecordingSchemaError):
            load_recordings(b"{not a recording}")


class TestReplayProposer(unittest.TestCase):
    """回放提议。"""

    def test_replay_proposer_returns_recorded_response(self):
        """回放器逐字返回录制响应，且该响应可被 parse_proposal 判为有效。"""
        proposer = ReplayProposer(load_recordings(recordings_bytes()))
        response_a = proposer.propose(slot="a", window=make_window_a())
        self.assertEqual(response_a.decode("utf-8"), response_bytes(SEGMENTS_A, reason_prefix="a"))
        self.assertEqual(response_a, response_bytes(SEGMENTS_A, reason_prefix="a").encode("utf-8"))

        parsed = parse_proposal(response_a, WINDOW_A_TEXT)
        self.assertTrue(parsed["valid"], parsed["error"])
        self.assertEqual(parsed["segments"], SEGMENTS_A)

        response_b = proposer.propose(slot="b", window=make_window_b())
        self.assertEqual(response_b.decode("utf-8"), response_bytes(SEGMENTS_B, reason_prefix="b"))

    def test_replay_proposer_miss_raises_RecordingMiss(self):
        """无对应录制（窗口未知、或该 slot 缺录制）必须抛 RecordingMiss，不得静默返回空提议。"""
        proposer = ReplayProposer(load_recordings(recordings_bytes()))
        with self.assertRaises(RecordingMiss):
            proposer.propose(slot="a", window=make_window("%s_w999" % WORK, WINDOW_A_TEXT, 0))

        partial_doc = {
            "schema": "m3_boundary_recordings/1",
            "synthetic": True,
            "template_id": PROMPT_TEMPLATE_ID,
            "recordings": [
                {
                    "window_id": "%s_w001" % WORK,
                    "slot": "a",
                    "response": response_bytes(SEGMENTS_A, reason_prefix="a"),
                }
            ],
        }
        partial = ReplayProposer(
            load_recordings(json.dumps(partial_doc, ensure_ascii=False).encode("utf-8"))
        )
        self.assertTrue(partial.propose(slot="a", window=make_window_a()))
        with self.assertRaises(RecordingMiss):
            partial.propose(slot="b", window=make_window_a())


class TestLiveProposerDisabled(unittest.TestCase):
    """第 88 条护栏：LiveProposer 恒禁用，且模块内不含任何网络/模型调用代码。"""

    def test_live_proposer_strictly_disabled_with_or_without_env(self):
        """未设环境变量抛 ModelCallDisabled；设了构造成功但 propose 仍抛 ModelCallDisabled。"""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(LIVE_PROPOSER_ENV_FLAG, None)
            self.assertIsNone(os.environ.get(LIVE_PROPOSER_ENV_FLAG))
            with self.assertRaises(ModelCallDisabled):
                LiveProposer()

        with mock.patch.dict(os.environ, {LIVE_PROPOSER_ENV_FLAG: "1"}):
            proposer = LiveProposer()
            with self.assertRaises(ModelCallDisabled):
                proposer.propose(slot="a", window=make_window_a())
            with self.assertRaises(ModelCallDisabled):
                proposer.propose(slot="b", window=make_window_b())

        # 桩内不得含真实调用代码：源码层面禁止任何网络库 import（非空转证据）
        source = (Path(__file__).resolve().parents[1] / "proposer.py").read_text(
            encoding="utf-8"
        )
        for banned in ("socket", "urllib", "requests", "httpx", "http.client"):
            self.assertNotIn("import %s" % banned, source)
            self.assertNotIn("from %s" % banned, source)


class TestZeroNetwork(unittest.TestCase):
    """第 88 条护栏：整条回放链路在网络拦截下网络调用次数严格为 0（P6）。"""

    def test_proposer_zero_network_via_socket_monkeypatch(self):
        """拦截 socket.socket 与 socket.create_connection，回放全流程不得触发任何网络调用。"""
        network_calls = []

        def blocked(*args, **kwargs):
            network_calls.append((args, kwargs))
            raise AssertionError("P6: 首纵切零网络，回放流程不得建立任何连接")

        recorded = load_recordings(recordings_bytes())
        with mock.patch.object(socket, "socket", blocked), mock.patch.object(
            socket, "create_connection", blocked
        ):
            proposers = {"a": ReplayProposer(recorded), "b": ReplayProposer(recorded)}
            for slot in ("a", "b"):
                for window in (make_window_a(), make_window_b()):
                    request = build_request(slot=slot, model=MODEL, window=window)
                    self.assertIsInstance(request, bytes)
                    response = proposers[slot].propose(slot=slot, window=window)
                    parsed = parse_proposal(response, window["text"])
                    self.assertTrue(parsed["valid"], parsed["error"])

        self.assertEqual(network_calls, [], "P6 违例：回放流程发起了网络调用")


class TestPromptAssetRegistry(unittest.TestCase):
    """Prompt 资产化与解耦校验（Prompt as Artifact）。"""

    def test_default_registry_loads_v1_asset(self):
        reg = get_default_registry()
        profile = reg.require("m3_boundary_v1")
        self.assertEqual(profile.prompt_id, "m3_boundary")
        self.assertEqual(profile.version, "1.0.0")
        self.assertEqual(profile.sha256, PROMPT_TEMPLATE_SHA256)
        self.assertEqual(
            hashlib.sha256(profile.template.encode("utf-8")).hexdigest(),
            profile.sha256,
        )

    def test_profile_self_consistency_rejects_hash_mismatch(self):
        with self.assertRaises(ValueError):
            PromptProfile.from_dict({
                "template_id": "bad_hash_profile",
                "template": "some text",
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
            })

    def test_dynamic_registration_and_usage(self):
        custom_template = "新版古籍分词提示词模板。"
        custom_sha = hashlib.sha256(custom_template.encode("utf-8")).hexdigest()
        custom_profile = PromptProfile.from_dict({
            "prompt_id": "m3_boundary_experimental",
            "version": "2.0.0",
            "template_id": "m3_boundary_v2_test",
            "description": "实验版切分提示词",
            "template": custom_template,
            "sha256": custom_sha,
        })
        reg = PromptRegistry(prompts_dir=Path("/nonexistent"))
        reg.register(custom_profile)

        # 1. 注册表中查询
        self.assertTrue(reg.contains("m3_boundary_v2_test"))
        self.assertEqual(reg.require("m3_boundary_v2_test").sha256, custom_sha)

        # 2. 构造请求体携带资产信息
        req_bytes = build_request(
            slot="a",
            model=MODEL,
            window=make_window_a(),
            template_id="m3_boundary_v2_test",
            registry=reg,
        )
        req_doc = json.loads(req_bytes.decode("utf-8"))
        self.assertEqual(req_doc["template_id"], "m3_boundary_v2_test")
        self.assertEqual(req_doc["prompt_id"], "m3_boundary_experimental")
        self.assertEqual(req_doc["prompt_version"], "2.0.0")
        self.assertEqual(req_doc["prompt_sha256"], custom_sha)
        self.assertEqual(req_doc["template"], custom_template)

        # 3. 录制文档回放支持动态模板
        rec_doc = recordings_doc(template_id="m3_boundary_v2_test")
        loaded = load_recordings(
            json.dumps(rec_doc, ensure_ascii=False).encode("utf-8"),
            registry=reg,
        )
        self.assertEqual(loaded["template_id"], "m3_boundary_v2_test")


if __name__ == "__main__":
    unittest.main()
