# HANDOFF — gujiorc 古籍 OCR 工作台 交接说明

> 日期：2026-08-18
> 位置：learn_system/ocr/
> 分支/工作区：learn_system 根仓库（ocr/ 为其子目录）
> 状态：功能全部实现，待 Colab 实测 + Web UI 人工验收

---

## 1. 这是什么

本地开发、Colab 可运行的**古籍 OCR 识别与生僻字校对工作台**（包名 gujiorc）。

核心能力：对传统古籍扫描图（如《新刻琴堂五星》《三辰通载》）做 OCR，竖排/图画式布局识别，**精确到一个字一个框**，自动圈出生僻字，支持全书检索、改字、异体字归并、质量报告、导出到 pipeline 知识编译。

## 2. 已完成（M1-M7 全部）

代码在 `ocr/src/gujiorc/`（约 20 个模块），`ocr/tests/` 37 个测试全过。

| 里程碑 | 内容 | 交付 |
|---|---|---|
| M1 | PaddleOCR 识别 + 竖排区块切分 + 排序 | `ocr/engine.py` `pipeline.py` |
| M2 | 单字切分（一字一框） | `ocr/segment.py`（投影法+细框合并） |
| M3/M4 | 本地 Web UI（查看/改字/框选补标/旋转预览） | `local/app.py` + `local/static/` |
| M5 | 生僻字圈划/检索/查询/拆解 | `rare/detector.py` `crop.py` `groups.py` `dictionary.py` |
| M6 | 质量报告 + 导出 + 进度 + schema 校验 | `core/report.py` `export.py` `progress.py` `schema.py` |
| M7 | 端到端全流程 | 琴堂五星 3 页跑通 |

**核心设计（数据铁律）：** 原始 OCR 识别 `orig_char` 永不覆盖；所有转化（改字/异体归一/分组映射）写 `char` + `mapping`，可追溯回退。

## 3. 关键文件地图

```
ocr/
├── src/gujiorc/
│   ├── core/        # paths(OCR_ROOT路径/本地Colab通用) models(层级框) storage(JSON+SQLite)
│   │                # config progress(进度心跳) schema(校验) report(质量) export(导出)
│   ├── ocr/         # engine(PaddleOCR封装) pipeline(识别→字段) segment(单字切分)
│   ├── index/       # fulltext(全字索引+检索+重复统计)
│   └── rare/        # detector(生僻判定/繁简归一) crop(截图) groups(分组归并) dictionary(查询拆解)
├── scripts/
│   ├── ocr_workbench.py    # 主 CLI（所有命令入口）
│   ├── gen_common_hanzi.py # 生成完整常用字表
├── colab/
│   ├── run_colab.py        # Colab 一键全流程（OCR_ROOT 指向 Google Drive）
│   ├── requirements.txt
│   └── README.md
├── local/           # app.py + static/（Web UI）
├── tests/           # 37 测试
├── data/            # common_hanzi.txt(3913字) + README
└── docs/            # PRD.md / PLANS.md / HANDOFF.md(本文件)
```

## 4. 关键用法

```bash
cd ocr && source .venv/bin/activate

# 识别整本书（Colab/本地通用，设 OCR_ROOT 控制数据位置）
OCR_ROOT=数据目录 PYTHONPATH=src python scripts/ocr_workbench.py run --segment <图片或目录>
# 生僻字圈划+清单
OCR_ROOT=... PYTHONPATH=src python scripts/ocr_workbench.py rare <图片或目录>
# 查某字全书位置
OCR_ROOT=... PYTHONPATH=src python scripts/ocr_workbench.py query 孛
# 改字（保留orig_char+记录mapping）
OCR_ROOT=... PYTHONPATH=src python scripts/ocr_workbench.py fix page_003 all 凡 --from-char 凢
# 质量报告 / 导出
OCR_ROOT=... PYTHONPATH=src python scripts/ocr_workbench.py report --book 书名
OCR_ROOT=... PYTHONPATH=src python scripts/ocr_workbench.py export --book 前缀
# Web UI（编辑/旋转/框选补标）
OCR_ROOT=... PYTHONPATH=src python local/app.py   # 打开 http://localhost:8000

# Colab 一键
from colab.run_colab import full_pipeline
full_pipeline('/content/drive/MyDrive/ocr_work/books')
```

依赖：paddleocr/paddlepaddle/opencv/numpy/Pillow/opencc（见 pyproject.toml）。venv 在 `ocr/.venv/`（已装 paddleocr+pymupdf+fastapi+opencc）。

## 5. 未完成 / 待办

### 5.1 未完成（功能层面）
1. **图画式星盘图的曲线排布字**仍识别为乱码——PaddleOCR 检测框是矩形，贴合不了弧线排字的单字。这是算法固有难点（PLANS M2 备注）。
2. **Web UI 前端**实际视觉/交互未人工验收（后端 API 已测，前端 JS 未在浏览器实机走查）。可能有坐标缩放、框选交互小 bug。
3. **Colab 实机未跑**——只在本地用 OCR_ROOT 模拟，未真正在 Google Colab 挂载 Drive 跑过。
4. Unihan 离线库未下载（如要更全的生僻字读音/释义，放 `data/unihan/unihan.json`）。当前用内置术数字典兜底。

### 5.2 未完成（工程层面）
5. **book.json 元数据**未真正打通——导出 transcript 时未写 manifest.yaml（pipeline 衔接 PLANS §6 的 manifest 部分待做）。
6. **审计(audit)完整历史**——目前用 orig_char+mapping 记录单字改动，但没做跨页的全局审计日志文件。

## 6. 实现方向 / 计划

### 短期（建议优先）
1. **Colab 实机跑通**：上传 `colab/` 到 Drive，用 `full_pipeline` 跑一本真实古籍，验证进度心跳、Drive 持久化、断点。
2. **Web UI 人工验收**：`local/app.py` 打开浏览器，走查改字/框选/旋转，修前端 bug。

### 中期
3. **曲线字单字切分**：若遇星盘图，开发弧线段切分（沿圆弧投影）——单独算法任务。
4. **manifest.yaml 生成**：导出时对齐 pipeline `corpus/{tech}/{book}_edNN/` 结构 + manifest，真正打通知识编译链路。
5. **全局审计日志**：把每次 fix/groups 写进 `logs/audit.jsonl`，跨页可追溯。

### 长期
6. 满书批量测试（用整本《三辰通载》PDF 提图），调单字切分阈值、低置信反馈。
7. 把生僻字分组归并接到 pipeline 的异体字处理。

## 7. 已知坑 / 注意事项

- **OCR_ROOT 决定数据位置**：本地默认 `data_work/`，Colab 必须设 `/content/drive/MyDrive/ocr_work`，否则会话结束数据丢失。
- **常用字表** `data/common_hanzi.txt`（3913字，GB2312一级+繁体+术数）是生僻判定的关键。若换大表，重跑 `scripts/gen_common_hanzi.py` 或放完整《通用规范汉字表》。
- **繁简归一用 OpenCC**（`opencc-python-reimplemented`），别删依赖——否则繁体字会误判生僻。
- **单字切分质量**：常规竖排列好，曲线/极密小字会切过度或误并，需人工（Web UI 可补）。`--segment` 开关可关。
- .venv/ 和 data_work/ 已 gitignore，别提交。

## 8. 最后状态

- 全部代码已提交到 learn_system 根仓库（ocr/ 子目录），工作区干净。
- 测试 37 全过。
- 下一步从"Colab 实机跑通"或"Web UI 验收"开始。