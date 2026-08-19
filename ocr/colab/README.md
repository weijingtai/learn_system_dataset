# ocr/colab — 古籍 OCR 识别（本地开发，Colab 运行）

本目录是 **gujiorc** 项目的 Colab 端入口。全部功能代码在顶层 `src/gujiorc/`（本地开发，本地/Colab 通用），此处提供 Colab 专属封装与一键脚本。

## 架构总览

```
ocr/
├── src/gujiorc/         # 全部功能代码（本地开发，通用）
│   ├── core/            # paths(路径) / models(层级框) / storage(双轨) / progress(进度) / config
│   ├── ocr/             # engine(PaddleOCR封装) / pipeline(识别→PageResult)
│   ├── index/           # fulltext(全字全文索引 M5)
│   └── rare/            # detector(生僻字判定 M4) / crop(截图) / groups(分组归并 M12) / dictionary(查询拆解)
├── scripts/ocr_workbench.py  # 本地 CLI（run/rare/index/query/dups/groups）
├── colab/               # ← 本目录：Colab 一键入口
│   ├── run_colab.py     # Colab 全流程（识别+圈划+索引+进度+清单）
│   ├── ocr_pipeline.ipynb   # (视需要) Colab notebook
│   └── requirements.txt     # 依赖
├── local/               # (本地 Web UI，后续)
├── tests/               # 核心逻辑测试
└── data/                # 常用字表/Unihan 数据说明
```

## 本地如何运行

```bash
# 1. 建 venv 装依赖（开发测试用轻量，识别需 paddleocr）
uv venv .venv --python 3.11
uv pip install --python .venv numpy pytest Pillow

# 2. 跑核心逻辑测试（不需 paddleocr）
cd ocr && PYTHONPATH=src .venv/bin/python -m pytest tests/ -v

# 3. CLI（识别需先装 paddleocr: uv pip install --python .venv paddleocr paddlepaddle）
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py run <图片或目录>
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py rare <图片或目录>
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py query <字>
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py dups
```

数据根 `data_work/`（默认）或设 `OCR_ROOT`。

## Colab 如何运行（Google Drive 持久化）

```python
# 记住两条铁律：
# 1. OCR_ROOT 指向 Google Drive 持久盘 → 会话关闭数据不丢、断点续传
# 2. 用 run_colab.py 一键跑完 识别+圈划+索引+清单+进度

from google.colab import drive
drive.mount('/content/drive')            # 挂载持久盘

import os
os.environ['OCR_ROOT'] = '/content/drive/MyDrive/ocr_work'

# 上传本目录后运行全流程（books_dir 是原图目录）
import sys; sys.path.insert(0, '/content/ocr/src')
from colab.run_colab import full_pipeline
full_pipeline('/content/drive/MyDrive/ocr_work/books')
```

Colab 端生成的**进度心跳** `logs/progress.json`（每 ≥5% 更新 百分比/当前页/错误），本地可读来监控远端识别进度（PLANS M9_）。

## 存储位置（本地 vs Colab）

| 数据 | 本地默认 | Colab（OCR_ROOT=/content/drive/MyDrive/ocr_work） |
|---|---|---|
| 原图 books/ | data_work/books/ | .../books/ |
| 每页识别 JSON | data_work/data/page_001.json | .../data/page_001.json |
| 全字索引 index.db | data_work/index.db | .../index.db |
| 生僻字清单 | data_work/rare/rare_characters.json | .../rare/rare_characters.json |
| 生僻字截图 | data_work/glyph_samples/ | .../glyph_samples/ |
| 进度心跳 | data_work/logs/progress.json | .../logs/progress.json |

> 同一套代码、同一结构，仅 `OCR_ROOT` 不同。本地开发数据在 `data_work/`（已 gitignore），Colab 数据在 Google Drive 持久化。

## 当前实现进度（2026-08-05 已验证）

**M 系列里程碑全部完成（M1-M7，见 docs/PLANS.md）。**

| 功能 | 状态 | 验证 |
|---|---|---|
| PaddleOCR 识别（竖排+区块切分+排序） | ✅ M1 | 琴堂五星多页 6-35s/页 |
| 单字切分（一字一框） | ✅ M2 | 152-286 字/页，细框合并 |
| 本地 Web UI（查看/编辑/旋转/框选补标） | ✅ M3/M4 | FastAPI+前端，改字保留orig |
| 生僻字圈划/检索/查询/拆解 | ✅ M5 | red框+SQL查全位+读音部首 |
| 质量报告+导出+进度汇报+schema校验 | ✅ M6 | report.md + JSON/TXT/TSV/transcript |
| 原始识别保留(orig_char)+映射记录 | ✅ | 异体字凢→凡可追溯 |
| 端到端全流程 | ✅ M7 | 识别→切字→圈划→索引→检索→改字→报告 |
| Colab 一键 full_pipeline | ✅ | OCR_ROOT 通用，进度心跳 |

**可用 CLI 命令清单：**
```bash
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py run --segment <图或目录>   # 识别+单字切分+索引
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py rare <图或目录>             # 生僻字圈框+清单
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py query <字>                    # 查某字全书位置
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py index                        # 重建索引
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py dups                          # 重复字统计
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py dict <字>                     # 生僻字查询/拆解
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py fix <page> <id|all> <新字>   # 改字(保留orig_char)
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py show <page> --from-char 字   # 查看原始识别/映射
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py report --book 书名            # 质量报告
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py export --book 前缀            # 导出(JSON/TXT/TSV/transcript)
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py groups list                   # 分组清单
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py groups create --name "生僻A" --samples id1 id2
PYTHONPATH=src .venv/bin/python scripts/ocr_workbench.py groups define --id grp_01 --char 機

# Web UI（编辑/查看/旋转调正/框选补标）
OCR_ROOT=xxx PYTHONPATH=src .venv/bin/python local/app.py   # 打开 http://localhost:8000
```

## 常用字表（生僻字判定）

- **重要：内置兜底常用字集较小**（只够演示页如扉页）。正文生僻字判定会因缺少常见字（如"妾/路/限/則/帶"）而误判为生僻。
- **生产必须放置完整《通用规范汉字表》(8105字)** 为 `data/common_hanzi.txt`（本机/Colab 均可），程序优先加载它。
- 缺省时程序用内置常用字集 + 术数白名单兜底（含 孛/炁/罗/计 等）。
- 生成完整字表方法见下方 `gen_common_hanzi.py` 脚本。
- 见 `data/README.md`。