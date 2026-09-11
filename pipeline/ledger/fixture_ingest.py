"""把 ``pipeline/corpus/_fixture/mini_ed01/`` 经真实 Ledger 写路径灌入（ACT impl-01/05）。

用法::

    python -m pipeline.ledger.fixture_ingest --fixture <dir> --root <ledger_root> [--asset-root]

- 只读 fixture：不写、不改 fixture 目录任何文件；
- 用 ``LedgerService``（直连模式）真实写路径灌入：ProcessingRun → 配置修订 → 每个 stage
  一个 StepRun → 任务级产物与每 task 一个 StageCheckpoint → stage 输出修订 → 校验报告与
  日志 → Transformation → StagePackage → ``finish_step_run``；
- 全部 ID 取 fixture 常量（``manifest.yaml`` 与 ``expected/*.yaml``）；
- 末行打印 ``INGEST OK <processing_run_id> step_runs=3 checkpoints=9 transformations=3``。

第二次对同一 root 灌入会在第一个显式 ID 冲突处 ``DuplicateIdentifier(ID_002)``；
写路径全在事务内，不留半成品。

实现登记（ACT 未逐字规定）：

1. ``StepResult.status_version`` 取「完成该次迁移后的版本」（当前 status_version + 1），
   因为 ``step_result.schema.json`` 要求 ``minimum: 1``，而新建 StepRun 的
   ``status_version`` 为 0（act/03.yaml）；
2. 三个 stage 的输出 ``artifact_type`` 以 fixture ``expected`` 包
   ``manifest.output_artifacts[0].artifact_type`` 为准（裁定 2026-09-11：m3 为
   ``corpus_package``），并在 ``STAGE_OUTPUT_TYPES`` 里钉死同值，防 fixture 静默漂移；
3. ``--asset-root`` 仅为接口兼容保留：本切片不读页图（§22.1 页图只登记在本地 Object
   Store，不进 Git），宿主素材缺失由 fixture 自己的 ``verify.sh`` 报
   ``BLOCKED_SOURCE_ASSET_MISSING``。
"""

import argparse
import json
from pathlib import Path

import yaml

from .errors import SchemaViolation
from .service import LedgerService

# 本切片灌入的 stage（§22.1 首纵切为 m1–m3）
STAGES = ("m1", "m2", "m3")

# 三个 stage 的输出 artifact_type：与 fixture expected 包声明逐字一致（裁定 2026-09-11）
STAGE_OUTPUT_TYPES = {
    "m1": "source_manifest",
    "m2": "ocr_page_set",
    "m3": "corpus_package",
}

# fixture 的产出工具（同时写入 Transformation 与各修订的 producer 字段）
FIXTURE_TOOL = "tools/build_fixture.py"
FIXTURE_TOOL_VERSION = "mini_ed01"

# m1 的任务清单（§11：来源登记）
M1_TASKS = ("ingest_source",)

# page_002 的异常终态承载页
M2_ANOMALY_PAGE = "page_002"

# 末行摘要常量（与 ACT 05 约定逐字一致）
EXIT_OK = 0


class Fixture:
    """``mini_ed01`` 的只读视图（manifest、expected 三包、pages、anomalies、spans）。"""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.manifest = self._load_yaml("manifest.yaml")
        self.packages = {
            stage: self._load_yaml("expected/%s.stage_package.yaml" % stage)
            for stage in STAGES
        }
        self.anomalies = self._load_yaml("anomalies.yaml")
        self.spans_document = self._load_yaml("spans.yaml")
        self.spans = self.spans_document["spans"]
        self.pages = list(self.manifest["edition_part"]["pages"])
        self.batches = self._batch_ids()

    def _load_yaml(self, relative):
        path = self.directory / relative
        if not path.is_file():
            raise FileNotFoundError("fixture 文件缺失: %s" % path)
        with open(path, encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def _batch_ids(self):
        """按 spans.yaml 中的出现顺序返回 batch_id 列表。"""
        ordered = []
        for span in self.spans:
            if span["batch_id"] not in ordered:
                ordered.append(span["batch_id"])
        return ordered

    # ------------------------------------------------------------ 只读访问
    @property
    def technique_id(self):
        return self.manifest["technique_id"]

    @property
    def edition_part_id(self):
        return self.manifest["edition_part"]["artifact_id"]

    def bytes_of(self, relative):
        """按相对路径读取 fixture 文件字节（只读）。"""
        return (self.directory / relative).read_bytes()

    def anomaly_entry(self, page):
        """返回某页的异常登记（``anomalies.yaml``），没有则 ``None``。"""
        for entry in self.anomalies.get("entries", []):
            if entry.get("page") == page:
                return entry
        return None

    def stage_constants(self, stage):
        """从 expected 包抽取该 stage 的全部常量（ID、operation、输出类型）。"""
        package = self.packages[stage]
        output = package["manifest"]["output_artifacts"][0]
        transformation = package["lineage"]["transformations"][0]
        declared_type = output["artifact_type"]
        if declared_type != STAGE_OUTPUT_TYPES[stage]:
            raise SchemaViolation(
                "fixture expected/%s 声明的输出 artifact_type %r 与裁定值 %r 不一致"
                % (stage, declared_type, STAGE_OUTPUT_TYPES[stage]),
                code="SCH_002",
            )
        return {
            "processing_run_id": package["manifest"]["processing_run_id"],
            "step_run_id": package["manifest"]["step_run_id"],
            "stage_package_id": package["stage_package_id"],
            "package_revision_id": package["artifact_revision_id"],
            "output_artifact_id": output["artifact_id"],
            "output_revision_id": output["artifact_revision_id"],
            "input_revision_ids": [
                item["artifact_revision_id"]
                for item in package["manifest"]["input_artifacts"]
            ],
            "configuration_revision_id": transformation[
                "configuration_artifact_revision_id"
            ],
            "operation": transformation["operation"],
            "artifact_type": declared_type,
        }


def _put_sealed(
    service,
    step_run_id,
    artifact_type,
    data,
    artifact_id=None,
    artifact_revision_id=None,
):
    """写入并封存一个修订，返回 ``(artifact_id, revision_id)``；可给显式 fixture 常量 ID。"""
    artifact_id, revision_id = service.put_artifact(
        step_run_id,
        artifact_type,
        data,
        artifact_id=artifact_id,
        artifact_revision_id=artifact_revision_id,
        producer_module=FIXTURE_TOOL,
        producer_version=FIXTURE_TOOL_VERSION,
    )
    service.seal_revision(revision_id)
    return artifact_id, revision_id


def _stage_tasks(fixture, stage):
    """返回该 stage 的任务清单：``task_id`` / ``artifact_type`` / ``data`` / 终态。"""
    if stage == "m1":
        return [
            {
                "task_id": M1_TASKS[0],
                "artifact_type": "source_manifest",
                "data": fixture.bytes_of("manifest.yaml"),
                "terminal_state": None,
                "human_event": None,
            }
        ]
    if stage == "m2":
        anomaly = fixture.anomaly_entry(M2_ANOMALY_PAGE)
        tasks = []
        for page in fixture.pages:
            terminal_state = None
            human_event = None
            if anomaly is not None and anomaly.get("page") == page:
                terminal_state = anomaly["terminal_state"]
                human_event = json.dumps(
                    anomaly, sort_keys=True, ensure_ascii=False
                ).encode("utf-8")
            tasks.append(
                {
                    "task_id": page,
                    "artifact_type": "ocr_page",
                    "data": fixture.bytes_of("pages/%s.json" % page),
                    "terminal_state": terminal_state,
                    "human_event": human_event,
                }
            )
        return tasks
    tasks = []
    for batch in fixture.batches:
        batch_spans = [span for span in fixture.spans if span["batch_id"] == batch]
        tasks.append(
            {
                "task_id": batch,
                "artifact_type": "corpus_batch",
                "data": json.dumps(
                    batch_spans, sort_keys=True, ensure_ascii=False
                ).encode("utf-8"),
                "terminal_state": None,
                "human_event": None,
            }
        )
    return tasks


def _write_task_checkpoints(fixture, service, stage, step_run_id):
    """每完成一个 task 落盘一个 StageCheckpoint（§17.1），返回 ``(Checkpoint 号列表, 人工事件修订列表)``。"""
    tasks = _stage_tasks(fixture, stage)
    checkpoints = []
    human_event_revision_ids = []
    for index, task in enumerate(tasks):
        _, revision_id = _put_sealed(
            service, step_run_id, task["artifact_type"], task["data"]
        )
        if task["human_event"] is not None:
            _, event_revision_id = _put_sealed(
                service, step_run_id, "human_event", task["human_event"]
            )
            human_event_revision_ids.append(event_revision_id)
        remaining = [
            {"task_id": later["task_id"]} for later in tasks[index + 1 :]
        ]
        checkpoints.append(
            service.write_checkpoint(
                step_run_id,
                edition_part_id=fixture.edition_part_id,
                stage=stage,
                completed_tasks=[
                    {
                        "task_id": task["task_id"],
                        "artifact_revision_id": revision_id,
                        "status": "succeeded",
                        "terminal_state": task["terminal_state"],
                    }
                ],
                human_decisions=list(human_event_revision_ids),
                pending_queue=remaining,
                next_pointer=remaining[0] if remaining else None,
            )
        )
    return checkpoints, human_event_revision_ids


def ingest(fixture_dir, service, asset_root=None):
    """用给定 ``LedgerService`` 把 fixture 灌入 Ledger，返回灌入摘要。

    ``fixture_dir`` 可以是路径或 ``Fixture`` 实例；``service`` 由调用方持有与关闭。
    """
    fixture = fixture_dir if isinstance(fixture_dir, Fixture) else Fixture(fixture_dir)
    constants = {stage: fixture.stage_constants(stage) for stage in STAGES}
    processing_run_id = constants["m1"]["processing_run_id"]

    # 1) ProcessingRun（显式常量 ID，导入路径）
    service.create_processing_run(
        "edition_run",
        fixture.edition_part_id,
        fixture.technique_id,
        processing_run_id=processing_run_id,
    )

    # 2) 配置修订：不挂 StepRun（put_run_artifact），写入即 sealed
    for stage in STAGES:
        service.put_run_artifact(
            processing_run_id,
            "configuration",
            json.dumps(
                {
                    "stage": stage,
                    "tool": FIXTURE_TOOL,
                    "tool_version": FIXTURE_TOOL_VERSION,
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8"),
            artifact_revision_id=constants[stage]["configuration_revision_id"],
            producer_module=FIXTURE_TOOL,
            producer_version=FIXTURE_TOOL_VERSION,
        )

    summary = {
        "processing_run_id": processing_run_id,
        "edition_part_id": fixture.edition_part_id,
        "technique_id": fixture.technique_id,
        "asset_root": str(asset_root) if asset_root else None,
        "stage_packages": {},
    }

    for stage in STAGES:
        constant = constants[stage]
        package = fixture.packages[stage]

        # 3) StepRun（显式常量 ID；输入取上一 stage 的输出）
        step_run_id = service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "processing_run_id": processing_run_id,
                "step_run_id": constant["step_run_id"],
                "input_artifact_ids": list(constant["input_revision_ids"]),
                "technique_profile_id": fixture.technique_id,
                "configuration_artifact_id": constant["configuration_revision_id"],
            }
        )

        # 4) 任务级产物 + 每 task 一个 Checkpoint
        checkpoints, human_event_revision_ids = _write_task_checkpoints(
            fixture, service, stage, step_run_id
        )

        # 5) stage 输出修订（显式 fixture 常量 ID）
        _, output_revision_id = _put_sealed(
            service,
            step_run_id,
            constant["artifact_type"],
            json.dumps(
                package["payload"], sort_keys=True, ensure_ascii=False
            ).encode("utf-8"),
            artifact_id=constant["output_artifact_id"],
            artifact_revision_id=constant["output_revision_id"],
        )

        # 6) 校验报告 + 执行日志
        _, report_revision_id = _put_sealed(
            service,
            step_run_id,
            "validation_report",
            json.dumps(
                package["validation"], sort_keys=True, ensure_ascii=False
            ).encode("utf-8"),
        )
        _, log_revision_id = _put_sealed(
            service, step_run_id, "step_log", b"ingest from mini_ed01"
        )

        # 7) Transformation（输入/输出/工具/配置/校验/人工决定）
        transformation_id = service.record_transformation(
            step_run_id,
            operation=constant["operation"],
            tool=FIXTURE_TOOL,
            tool_version=FIXTURE_TOOL_VERSION,
            configuration_revision_id=constant["configuration_revision_id"],
            input_revision_ids=list(constant["input_revision_ids"]),
            output_revision_ids=[output_revision_id],
            validation_report_revision_id=report_revision_id,
            human_event_revision_ids=human_event_revision_ids,
        )

        # 8) StagePackage（调用方随后 seal）
        stage_package_id, package_revision_id = service.register_stage_package(
            step_run_id,
            package,
            fixture.bytes_of("expected/%s.stage_package.yaml" % stage),
            stage_package_id=constant["stage_package_id"],
            artifact_revision_id=constant["package_revision_id"],
        )
        service.seal_revision(package_revision_id)

        # 9) finish_step_run（StepResult 过 Schema，并封存 StepManifest）
        current_version = service.get_step_run(step_run_id)["status_version"]
        manifest_revision_id = service.finish_step_run(
            step_run_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": processing_run_id,
                "step_run_id": step_run_id,
                "status_version": current_version + 1,
                "status": "succeeded",
                "output_artifact_ids": [output_revision_id, package_revision_id],
                "validation_report_ids": [report_revision_id],
                "log_artifact_ids": [log_revision_id],
                "failure_artifact_ids": [],
            },
        )

        summary["stage_packages"][stage] = {
            "stage_package_id": stage_package_id,
            "artifact_revision_id": package_revision_id,
            "step_run_id": step_run_id,
            "output_artifact_id": constant["output_artifact_id"],
            "output_revision_id": output_revision_id,
            "configuration_revision_id": constant["configuration_revision_id"],
            "input_revision_ids": list(constant["input_revision_ids"]),
            "manifest_revision_id": manifest_revision_id,
            "transformation_id": transformation_id,
            "checkpoints": checkpoints,
        }

    summary["step_runs"] = [
        summary["stage_packages"][stage]["step_run_id"] for stage in STAGES
    ]
    summary["checkpoint_count"] = sum(
        len(summary["stage_packages"][stage]["checkpoints"]) for stage in STAGES
    )
    return summary


def main(argv=None):
    """``python -m pipeline.ledger.fixture_ingest`` 入口。"""
    parser = argparse.ArgumentParser(
        prog="pipeline.ledger.fixture_ingest",
        description="把 mini_ed01 经真实 Ledger 写路径灌入（规格 §17/§22.1）",
    )
    parser.add_argument("--fixture", required=True, help="fixture 根目录")
    parser.add_argument("--root", required=True, help="Ledger 根目录")
    parser.add_argument(
        "--asset-root",
        default=None,
        help="页图素材根目录（本切片不读页图，仅保留接口）",
    )
    args = parser.parse_args(argv)

    service = LedgerService(args.root)
    try:
        summary = ingest(args.fixture, service, asset_root=args.asset_root)
    finally:
        service.close()

    print(
        "INGEST OK %s step_runs=%d checkpoints=%d transformations=%d"
        % (
            summary["processing_run_id"],
            len(summary["step_runs"]),
            summary["checkpoint_count"],
            len(summary["stage_packages"]),
        )
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
