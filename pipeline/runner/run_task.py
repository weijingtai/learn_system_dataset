#!/usr/bin/env python3
"""调度脚本：读任务包、调模型（或 mock）、落盘输出。"""

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

RUNNER_DIR = Path(__file__).resolve().parent
CONFIG_PATH = RUNNER_DIR / "config.yaml"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def sha256_hex(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def build_prompt(task_dir):
    instructions_path = task_dir / "INSTRUCTIONS.md"
    if not instructions_path.is_file():
        raise SystemExit("缺少文件: INSTRUCTIONS.md")
    with open(instructions_path, encoding="utf-8") as f:
        instructions = f.read()

    input_dir = task_dir / "input"
    if not input_dir.is_dir():
        raise SystemExit("缺少目录: input/")

    input_files = sorted(input_dir.iterdir())
    if not input_files:
        raise SystemExit("input/ 目录下无文件")

    parts = [instructions, "---"]
    for fp in input_files:
        parts.append(f"{fp.name}:")
        with open(fp, encoding="utf-8") as f:
            parts.append(f.read())
    return "\n".join(parts)


def call_model(prompt, model_cfg):
    """真实 API 调用。import requests 放在函数内部，保证 mock 模式不装 requests 也能跑。"""
    import requests  # noqa: E402

    url = model_cfg["endpoint"]
    api_key = os.environ.get(model_cfg.get("api_key_env", ""))
    if not api_key:
        raise SystemExit(f"环境变量 {model_cfg['api_key_env']} 未设置")
    payload = {
        "model": model_cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": model_cfg.get("temperature", 0),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise SystemExit(f"API 调用失败: {e}")


def call_mock(task_dir):
    mock_file = task_dir / "mock_output.yaml"
    if not mock_file.is_file():
        raise SystemExit("缺少文件: mock_output.yaml")
    with open(mock_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_output(task_dir, model_name, response_data, model_cfg, input_sha_map,
                 prompt="", task_meta=None):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = task_dir / "output" / f"{model_name}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    resp_path = out_dir / "response.yaml"
    with open(resp_path, "w", encoding="utf-8") as f:
        yaml.dump(response_data, f, allow_unicode=True, sort_keys=False)

    resp_sha = sha256_hex(resp_path)

    # 审计：完整提示词存档（v1.1.1 §7.1——聊天记录不能是唯一凭据）
    prompt_path = out_dir / "prompt.txt"
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    endpoint = model_cfg.get("endpoint", "") if "endpoint" in model_cfg else ""
    task_meta = task_meta or {}

    run_data = {
        "task_id": task_meta.get("task_id", ""),
        "stage": task_meta.get("stage", ""),
        "instruction_version": task_meta.get("instruction_version", ""),
        "model": model_name,
        "model_id": model_cfg.get("model", ""),
        "endpoint": endpoint,
        "time": datetime.now(timezone.utc).isoformat(),
        "input_files": {rel: input_sha_map.get(rel, "") for rel in input_sha_map},
        "prompt_sha256": sha256_hex(prompt_path),
        "response_sha256": resp_sha,
        # 成本记录（章程 G6）：manual/mock 模式填不了 token，留占位由账本回填；
        # API 模式下由 call_model 的响应 usage 字段回填（见 write_output 调用处）。
        "cost": {
            "tokens_in": (response_data.get("usage", {}) or {}).get("prompt_tokens")
            if isinstance(response_data, dict) else None,
            "tokens_out": (response_data.get("usage", {}) or {}).get("completion_tokens")
            if isinstance(response_data, dict) else None,
            "human_minutes": None,   # 你验收时回填到 batches.yaml
            "rework_rounds": None,   # 派发者按返工次数回填
        },
    }

    run_path = out_dir / "run.yaml"
    with open(run_path, "w", encoding="utf-8") as f:
        yaml.dump(run_data, f, allow_unicode=True, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(
        description="调度脚本：读任务包、调模型、落盘到 output/"
    )
    parser.add_argument("task_dir", nargs="?", help="任务包目录路径")
    parser.add_argument(
        "--model",
        required=True,
        choices=["production", "reviewer", "mock", "manual"],
        help="production/reviewer 走 API；mock 用 mock_output.yaml；manual 归档现成结果文件",
    )
    parser.add_argument("--from", dest="from_file", default=None,
                        help="manual 模式必填：模型产出的 YAML 结果文件路径")
    parser.add_argument("--by", dest="by_name", default="opencode",
                        help="manual 模式：执行者名字（默认 opencode），写入审计记录")
    args = parser.parse_args()

    if args.task_dir is None:
        parser.print_help()
        sys.exit(1)

    task_dir = Path(args.task_dir).resolve()
    if not task_dir.is_dir():
        raise SystemExit(f"任务包目录不存在: {args.task_dir}")

    try:
        config = load_config()
        if args.model == "manual":
            model_cfg = {"provider": "manual", "model": args.by_name}
        else:
            model_cfg = config["models"][args.model]
        prompt = build_prompt(task_dir)

        if args.model == "mock":
            response = call_mock(task_dir)
        elif args.model == "manual":
            if not args.from_file:
                raise SystemExit("manual 模式必须用 --from 指定结果文件")
            src = Path(args.from_file)
            if not src.is_file():
                raise SystemExit(f"结果文件不存在: {args.from_file}")
            with open(src, encoding="utf-8") as f:
                response = yaml.safe_load(f)
        else:
            response = call_model(prompt, model_cfg)

        input_dir = task_dir / "input"
        input_sha_map = {}
        if input_dir.is_dir():
            for fp in sorted(input_dir.iterdir()):
                rel = f"input/{fp.name}"
                input_sha_map[rel] = sha256_hex(fp)

        task_meta = {}
        task_yaml = task_dir / "task.yaml"
        if task_yaml.is_file():
            with open(task_yaml, encoding="utf-8") as f:
                task_meta = yaml.safe_load(f) or {}

        model_label = args.by_name if args.model == "manual" else args.model
        write_output(task_dir, model_label, response, model_cfg, input_sha_map,
                     prompt=prompt, task_meta=task_meta)

        # 自动生成 result.yaml 骨架（不覆盖已有文件）
        result_path = task_dir / "output" / "result.yaml"
        if not result_path.exists():
            result_skel = {
                "task_id": task_meta.get("task_id", task_dir.name),
                "result": "completed",
                "uncertainties": [],
                "lesson_candidates": [],
                "needs_escalation": False,
            }
            with open(result_path, "w", encoding="utf-8") as f:
                yaml.dump(result_skel, f, allow_unicode=True, sort_keys=False)

        print(f"完成: {task_dir.name}  --model {args.model}（执行者: {model_label}）")

    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    main()
