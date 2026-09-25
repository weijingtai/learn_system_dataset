"""登记表装载与一致性检查（规格 §5/§19 L2'）。

职责：

- ``load_registry`` / ``Registry``：把声明式 YAML 装载为内存对象；
- ``check_registry``：按「结构 → Schema → 行名 → Module → 端口」逐条给出问题码；
- ``interface_fingerprint``：相邻 Module Interface 指纹（替换判定用，见 §20 第 10 条）。

本模块不做任何写入、不 import 加工 Module 包；``entry`` 只在 ``resolve_entries=True``
时经 ``importlib`` 解析。
"""

import hashlib
import importlib
import json
import re
from collections import Counter
from pathlib import Path

import yaml

from pipeline.ledger.ids import STAGES

from . import DEFAULT_REGISTRY_PATH, REPO_ROOT
from .errors import RegistryInvalid

# 规格 §19 第一列逐字（:875–882）
STAGE_ROWS_EXPECTED = {
    "m1": "M1 Source Intake",
    "m2": "M2 Digitization & Correction",
    "m3": "M3 Corpus Compilation",
    "m4": "M4 Knowledge Extraction",
    "m5": "M5 Automatic Validation",
    "m6": "M6 Review Workbench",
    "m7": "M7 Incremental Assembly",
    "m8": "M8 Dataset Compilation",
}

# 规格 §5 五个专用队列逐字（:120–124）
HUMAN_QUEUES_EXPECTED = {
    "m2": "M2 异常页与低置信字",
    "m3": "M3 边界分歧",
    "m4": "M4 类别分歧",
    "m6": "M6 待签发",
    "m7": "M7 待裁决",
}

# L0 四份 Schema（按 id 排序固定）
L0_SCHEMA_IDS = ("artifact_ref", "stage_package", "step_request", "step_result")

# Module 种类、绑定与端口闭集
MODULE_KINDS = ("production", "thin_import", "stub")
BINDINGS = ("step_request", "legacy_self_driving", "imported")
PORT_IDS = ("ocr", "model", "index", "storage")

# 顶层必填键
_REQUIRED_TOP_KEYS = (
    "registry_version",
    "schemas",
    "stage_rows",
    "human_queues",
    "modules",
    "ports",
)

_MODULE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.]*$")
_ENTRY_RE = re.compile(r"^[a-z_][a-z0-9_.]*:[A-Za-z_][A-Za-z0-9_]*$")
_ARTIFACT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _normalize_schemas(raw):
    """把 ``schemas``（列表或映射）规范为 ``{schema_id: dict}``。"""
    if isinstance(raw, dict):
        entries = list(raw.values())
    else:
        entries = list(raw)
    normalized = {}
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("schema_id"):
            raise RegistryInvalid("schema 条目缺少 schema_id", code="SCH_001")
        normalized[entry["schema_id"]] = dict(entry)
    return normalized


def _normalize_ports(raw):
    """把 ``ports``（列表或映射）规范为 ``{port_id: dict}``。"""
    if isinstance(raw, dict):
        entries = list(raw.values())
    else:
        entries = list(raw)
    normalized = {}
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("port_id"):
            raise RegistryInvalid("port 条目缺少 port_id", code="SCH_001")
        normalized[entry["port_id"]] = dict(entry)
    return normalized


class Registry:
    """声明式登记表的内存表示。"""

    def __init__(
        self,
        *,
        registry_version,
        schemas,
        stage_rows,
        human_queues,
        modules,
        ports,
        repo_root,
        allow_stub=False,
    ):
        self.registry_version = registry_version
        self.schemas = schemas
        self.stage_rows = stage_rows
        self.human_queues = human_queues
        self.modules = modules
        self.ports = ports
        self.repo_root = Path(repo_root)
        self.allow_stub = allow_stub

    @classmethod
    def from_dict(cls, doc, *, repo_root=REPO_ROOT, allow_stub=False):
        """结构装载：只检查顶层必填键（``SCH_001``），语义规则归 ``check_registry``。"""
        if not isinstance(doc, dict):
            raise RegistryInvalid("登记表根节点必须是映射", code="SCH_001")
        for key in _REQUIRED_TOP_KEYS:
            if key not in doc:
                raise RegistryInvalid("登记表缺少顶层键: %s" % key, code="SCH_001")
        return cls(
            registry_version=doc["registry_version"],
            schemas=_normalize_schemas(doc["schemas"]),
            stage_rows=dict(doc["stage_rows"]),
            human_queues=dict(doc["human_queues"]),
            modules=list(doc["modules"]),
            ports=_normalize_ports(doc["ports"]),
            repo_root=repo_root,
            allow_stub=allow_stub,
        )

    def module_for(self, stage):
        """返回该 stage 的唯一 Module 描述符；0 个 → ``None``；多个 → ``ID_002``。

        ``allow_stub=False`` 时桩不计入（生产表不得有桩）。
        """
        matches = [
            module
            for module in self.modules
            if module.get("stage") == stage
            and (self.allow_stub or module.get("kind") != "stub")
        ]
        if not matches:
            return None
        if len(matches) > 1:
            raise RegistryInvalid(
                "阶段 %s 登记了 %d 个 Module" % (stage, len(matches)), code="ID_002"
            )
        return matches[0]

    def modules_by_id(self):
        """返回 ``{module_id: descriptor}``。"""
        return {module.get("module_id"): module for module in self.modules}


def load_registry(path=DEFAULT_REGISTRY_PATH, *, repo_root=REPO_ROOT):
    """读取 YAML 并装载为 ``Registry``（``allow_stub=False``）。"""
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Registry.from_dict(doc, repo_root=repo_root, allow_stub=False)


def _entry_unresolvable(entry):
    """尝试解析 ``"模块:属性"``；成功返回 ``None``，失败返回问题 detail。"""
    module_path, _, attr = entry.partition(":")
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # noqa: BLE001 - 报告问题而非中断
        return "%s 无法导入（%s: %s）" % (entry, type(exc).__name__, exc)
    if not hasattr(module, attr):
        return "%s 缺少属性 %s" % (entry, attr)
    return None


def check_registry(registry, *, resolve_entries=False):
    """逐条检查登记表；返回 ``[{"code", "detail"}]``，空表示一致。"""
    problems = []

    def add(code, detail):
        problems.append({"code": code, "detail": detail})

    # R1：L0 Schema 登记
    schemas = registry.schemas or {}
    for schema_id in L0_SCHEMA_IDS:
        if schema_id not in schemas:
            add("schema_missing", "L0 Schema 未登记: %s" % schema_id)
    for schema_id, entry in schemas.items():
        if schema_id not in L0_SCHEMA_IDS:
            continue
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            add("schema_path_missing", "%s 未登记 path" % schema_id)
            continue
        full = Path(registry.repo_root) / path
        if not full.is_file():
            add("schema_path_missing", "%s 路径不存在: %s" % (schema_id, path))
            continue
        actual = hashlib.sha256(full.read_bytes()).hexdigest()
        if entry.get("sha256") != actual:
            add(
                "schema_sha256_mismatch",
                "%s sha256 不一致（登记 %s，实算 %s）"
                % (schema_id, entry.get("sha256"), actual),
            )
        if entry.get("schema_version") != "1.0.0":
            add(
                "schema_version_invalid",
                "%s schema_version 必须为 1.0.0: %r"
                % (schema_id, entry.get("schema_version")),
            )

    # R2：行名与队列名逐字
    if dict(registry.stage_rows or {}) != STAGE_ROWS_EXPECTED:
        add("stage_rows_mismatch", "stage_rows 与规格 §19 第一列不一致")
    if dict(registry.human_queues or {}) != HUMAN_QUEUES_EXPECTED:
        add("human_queues_mismatch", "human_queues 与规格 §5 不一致")

    # R3/R4：Module 描述符
    seen_ids = set()
    for module in registry.modules:
        module_id = module.get("module_id")
        if not isinstance(module_id, str) or not _MODULE_ID_RE.match(module_id):
            add("module_id_invalid", "module_id 非法: %r" % (module_id,))
        elif module_id in seen_ids:
            add("module_id_duplicate", "module_id 重复: %s" % module_id)
        seen_ids.add(module_id)

        stage = module.get("stage")
        if stage not in STAGES:
            add("stage_invalid", "%s stage 不在闭集 m1–m8: %r" % (module_id, stage))
        kind = module.get("kind")
        if kind not in MODULE_KINDS:
            add("kind_invalid", "%s kind 非法: %r" % (module_id, kind))
        binding = module.get("binding")
        if binding not in BINDINGS:
            add("binding_invalid", "%s binding 非法: %r" % (module_id, binding))

        entry = module.get("entry")
        if binding == "imported":
            if entry is not None:
                add("entry_forbidden", "%s 为 imported 却带 entry: %r" % (module_id, entry))
        else:
            if not isinstance(entry, str) or not _ENTRY_RE.match(entry):
                add("entry_required", "%s 的 entry 非法: %r" % (module_id, entry))
            elif resolve_entries:
                detail = _entry_unresolvable(entry)
                if detail is not None:
                    add("entry_unresolvable", detail)

        if "entry_kwargs" in module and not isinstance(module["entry_kwargs"], dict):
            add(
                "entry_kwargs_invalid",
                "%s entry_kwargs 必须是 dict: %r" % (module_id, module["entry_kwargs"]),
            )
        if "owns_processing_run" in module and not isinstance(
            module["owns_processing_run"], bool
        ):
            add(
                "owns_processing_run_invalid",
                "%s owns_processing_run 必须是 bool: %r"
                % (module_id, module["owns_processing_run"]),
            )

        # R4'：人工输入件声明（裁决 Q2）：必须是非空字符串，且只许人工队列模块声明
        if "human_input_artifact" in module:
            human_input_artifact = module["human_input_artifact"]
            if not isinstance(human_input_artifact, str) or not human_input_artifact:
                add(
                    "human_input_artifact_invalid",
                    "%s human_input_artifact 必须是非空字符串: %r"
                    % (module_id, human_input_artifact),
                )
            elif module.get("human_queue") is not True:
                add(
                    "human_input_artifact_forbidden",
                    "%s 非 human_queue: true 却声明 human_input_artifact: %r"
                    % (module_id, human_input_artifact),
                )

        # R4：consumes 顺序与 artifact_type 形态
        for item in module.get("consumes") or []:
            if not isinstance(item, dict):
                continue
            artifact_type = item.get("artifact_type")
            if not isinstance(artifact_type, str) or not _ARTIFACT_TYPE_RE.match(
                artifact_type
            ):
                add(
                    "artifact_type_invalid",
                    "%s consumes.artifact_type 非法: %r"
                    % (module_id, artifact_type),
                )
            from_stage = item.get("from_stage")
            if stage in STAGES and from_stage in STAGES:
                if STAGES.index(from_stage) >= STAGES.index(stage):
                    add(
                        "consumes_stage_order",
                        "%s 的 from_stage %s 不早于本 stage %s"
                        % (module_id, from_stage, stage),
                    )
        for item in module.get("produces") or []:
            artifact_type = item.get("artifact_type") if isinstance(item, dict) else None
            if not isinstance(artifact_type, str) or not _ARTIFACT_TYPE_RE.match(
                artifact_type
            ):
                add(
                    "artifact_type_invalid",
                    "%s produces.artifact_type 非法: %r"
                    % (module_id, artifact_type),
                )

    # R5：桩隔离与同 stage 重复
    if not registry.allow_stub:
        for module in registry.modules:
            if module.get("kind") == "stub":
                add(
                    "stub_in_production",
                    "生产登记表出现桩 Module: %s" % module.get("module_id"),
                )
    non_stub_by_stage = Counter(
        module.get("stage")
        for module in registry.modules
        if module.get("kind") != "stub"
    )
    for stage, count in non_stub_by_stage.items():
        if count > 1:
            add(
                "stage_module_duplicate",
                "阶段 %s 登记了 %d 个非桩 Module" % (stage, count),
            )

    # R6：端口闭集与 Adapter
    ports = registry.ports or {}
    for port_id in PORT_IDS:
        if port_id not in ports:
            add("port_invalid", "端口闭集缺 %s" % port_id)
    for port_id in ports:
        if port_id not in PORT_IDS:
            add("port_invalid", "端口不在闭集: %s" % port_id)
    adapter_ids = []
    for port_id, port in ports.items():
        for adapter in port.get("adapters") or []:
            adapter_id = adapter.get("adapter_id")
            if adapter_id in adapter_ids:
                add("adapter_id_duplicate", "adapter_id 重复: %s" % adapter_id)
            adapter_ids.append(adapter_id)
        for schema_id in port.get("adjacent_interface") or []:
            if schema_id not in schemas:
                add(
                    "adjacent_interface_unknown",
                    "端口 %s 引用未登记 schema_id: %s" % (port_id, schema_id),
                )

    return problems


def interface_fingerprint(registry, module_id):
    """相邻 Module Interface 指纹（不含 version / entry / kind，含 L0 Schema 哈希）。"""
    module = registry.modules_by_id().get(module_id)
    if module is None:
        raise RegistryInvalid("登记表无此 module_id: %s" % module_id, code="REF_001")
    l0 = {
        schema_id: registry.schemas.get(schema_id, {}).get("sha256")
        for schema_id in L0_SCHEMA_IDS
    }
    payload = {
        "stage": module.get("stage"),
        "binding": module.get("binding"),
        "consumes": module.get("consumes"),
        "produces": module.get("produces"),
        "l0": l0,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
