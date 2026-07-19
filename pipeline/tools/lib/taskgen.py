#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskgen.py —— 下游任务包生成器公共骨架（工位4/5/6 共用）

工位4(concepts)/5(assertions)/6(paraphrase) 的任务包生成流程 95% 同构：
读 corpus/spans.yaml 建 (batch_id,seg_id)→span_id 映射 → 遍历 batch 从切分
draft 取 segments → 组装 → 落 segments.yaml(+可选 spans.yaml) → copy 模板+glossary
→ 写 task.yaml。差异全部收进 DownstreamTaskSpec，由各 gen 工具填好后调用 build()。

技法/书目/源ID 不再写死：从 corpus 的 manifest.yaml 读取（消 G1 硬编码）。
segment 字段的组成与顺序因工位而异（byte 敏感），故由各工具提供 seg_builder 全权控制。
确定性：同输入同输出，无时间戳。
"""
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import yaml

PIPELINE = Path(__file__).resolve().parent.parent.parent


def load_manifest(corpus: Path) -> dict:
    """读 corpus/manifest.yaml，取 technique_id / source_id 等书目无关配置。"""
    return yaml.safe_load((corpus / "manifest.yaml").read_text())


def _dump(obj, path: Path):
    yaml.dump(obj, open(path, "w"), allow_unicode=True, sort_keys=False)


@dataclass
class DownstreamTaskSpec:
    """一个下游任务包的全部可变参数。"""
    corpus: Path                      # corpus/<technique>/<edition>
    round_name: str                   # 轮次名（如 r1 / s1），进 task_id 尾部
    batch_ids: list                   # 覆盖的切分批次
    stage: str                        # SCHEMA stage 名（concept_candidates/assertions/paraphrase）
    task_suffix: str                  # task_id 尾缀（concepts/assert/para）
    template: Path                    # INSTRUCTIONS.md 模板绝对路径
    glossary: Path                    # glossary_v0.yaml 绝对路径
    instruction_version: str          # 指令版本号
    # 组装单个 segment：签名 (bid, span_id, seg_local, raw_seg) -> (seg_dict, sp_dict|None)
    # 字段顺序即 YAML 输出顺序，byte 敏感，由各工位精确控制。
    seg_builder: Callable = None
    emit_spans: bool = True           # 是否额外产 input/spans.yaml
    extra_task_meta: dict = field(default_factory=dict)  # 追加到 task.yaml 的字段
    # 完成语钩子：签名 (n_segs, n_batches, task_dir_rel) -> str
    done_note: Optional[Callable] = None


def build(spec: DownstreamTaskSpec) -> Path:
    """执行公共骨架，返回任务目录。"""
    manifest = load_manifest(spec.corpus)
    technique_id = manifest["technique_id"]
    source_id = manifest["source_id"]
    # 书目短名：edition 目录名前缀（qtbj_ed01 → qtbj）
    book = spec.corpus.name.split("_")[0]

    spans_all = yaml.safe_load((spec.corpus / "spans.yaml").read_text())["spans"]
    span_by = {(x["batch_id"], x["seg_id"]): x["span_id"] for x in spans_all}

    segs, sp = [], []
    for bid in spec.batch_ids:
        draft = PIPELINE / f"TASKS/task_{technique_id}_{bid}_seg/output/draft_opencode.yaml"
        data = yaml.safe_load(draft.read_text())
        for s in data["segments"]:
            span_id = span_by[(bid, s["seg_id"])]
            seg_local = span_id.split("_")[-1]
            seg, sp_rec = spec.seg_builder(bid, span_id, seg_local, s)
            segs.append(seg)
            if sp_rec is not None:
                sp.append(sp_rec)

    task_id = f"task_{technique_id}_{book}_{spec.task_suffix}_{spec.round_name}"
    td = PIPELINE / f"TASKS/{task_id}"
    (td / "input").mkdir(parents=True, exist_ok=True)
    _dump({"segments": segs}, td / "input/segments.yaml")
    if spec.emit_spans:
        _dump({"spans": sp}, td / "input/spans.yaml")
    shutil.copy(spec.template, td / "INSTRUCTIONS.md")
    shutil.copy(spec.glossary, td / "input/glossary_v0.yaml")

    task_meta = {"task_id": task_id, "stage": spec.stage,
                 "technique_id": technique_id, "source_id": source_id,
                 "instruction_version": spec.instruction_version,
                 "covers_batches": spec.batch_ids}
    task_meta.update(spec.extra_task_meta)
    _dump(task_meta, td / "task.yaml")

    td_rel = td.relative_to(PIPELINE)
    if spec.done_note:
        print(spec.done_note(len(segs), len(spec.batch_ids), td_rel))
    else:
        print(f"完成：{td_rel}  （{len(segs)} 段，{len(spec.batch_ids)} 批）")
    return td
