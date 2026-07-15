#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_spans.py —— 为全书所有切分段生成全局唯一 span_id 索引
（SCHEMA §2 source_span_id 的确定性落地；工位 4/5 与注解系统的寻址基础）

背景问题：41 批切分各自从 s01 编号，全书"s01"出现 41 次，跨批无法寻址。
        本工具用 batch→node→page 链条，为每段生成全局唯一 span：
        ss_<work>_ed01_p<页4位>_<seg_id>，如 ss_qtbj_ed01_p0005_s01。
        这既是工位 4 术语表 seg_ids 的正确写法，也是评论/注解系统定位每句话的 ID。

用法：
    python3 tools/gen_spans.py corpus/bazi/qtbj_ed01
产出 corpus/bazi/qtbj_ed01/spans.yaml：全书 span 总表（span_id ↔ batch/page/path/text 预览）。
确定性：同输入同输出，无时间戳。
"""
import sys
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parent.parent
WORK_TAG = "qtbj_ed01"  # 与 source_id src_qtbj_ed01 对应


def main():
    corpus = Path(sys.argv[1])
    outline = {o["node_id"]: o
               for o in yaml.safe_load((corpus / "outline.yaml").read_text())["outline"]}
    batches = yaml.safe_load((corpus / "batches.yaml").read_text())["batches"]

    spans = []
    for b in batches:
        node = outline[b["node_id"]]
        page = node["page"]
        draft = PIPELINE / b["task_dir"] / "output/draft_opencode.yaml"
        if not draft.exists():
            continue
        data = yaml.safe_load(draft.read_text())
        for s in data["segments"]:
            span_id = f"ss_{WORK_TAG}_p{page:04d}_{s['seg_id']}"
            spans.append({
                "span_id": span_id,
                "batch_id": b["batch_id"],
                "seg_id": s["seg_id"],
                "page": page,
                "path": s.get("path", node["path"]),
                "entry_title": s.get("entry_title", ""),
                "case_candidate": bool(s.get("case_candidate")),
                "text_preview": s["text"].replace("\n", " ")[:40],
            })

    # 唯一性自检——这正是本工具要解决的问题，必须 0 冲突
    ids = [x["span_id"] for x in spans]
    dup = [i for i in set(ids) if ids.count(i) > 1]
    (corpus / "spans.yaml").write_text(
        yaml.dump({"work": "窮通寶鑑", "source_id": f"src_{WORK_TAG}",
                   "span_count": len(spans), "spans": spans},
                  allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"生成 {len(spans)} 个全局 span，唯一冲突 {len(dup)} 个"
          f"{'（★仍有冲突需查★: ' + str(dup) + '）' if dup else '（全局唯一 ✓）'}")
    print(f"输出：{corpus}/spans.yaml")


if __name__ == "__main__":
    main()
