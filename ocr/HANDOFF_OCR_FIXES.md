# OCR 交接文档 — 三辰通载前10页识别

**日期**：2025-08-22  
**任务**：《三辰通载三十卷》(影宋鈔本) 前10页 OCR 识别 + Web UI 调试  
**当前状态**：识别流程可跑通（10页约107秒），但存在3个**未修复**的识别质量问题，需接手人继续修复。

---

## 一、已完成工作

1. 清空旧数据（data_work/data, logs, rare, glyph_samples）
2. PDF → PNG：用 2x 分辨率（1203×1654px）切出前10页
3. OCR pipeline 固定 PaddleOCR PP-OCRv6_medium_det/rec
4. 三次调参尝试：
   - `gap_thresh` 改为 20（减少超高合框）
   - `y_min` 排序替代 `y_center`（修复竖排文字与框错位）
   - `symbol_gap_repair` 补扫（列投影找漏字，标记 STATUS_UNRECOGNIZED）
5. Web UI 改 flex 竖排 + 上下页按钮（UI层面的呈现样式已改好）

---

## 二、未修复问题（症状 + 根因）

### 问题1：竖排文字与框错位（反之亦然）
- **症状**：某列第N字的框位置正确，但框内识别出的是第N+1个字的内容；造成"字错位"或"后字顶掉前字"
- **根因**：PaddleOCR 竖排模式 `rec_texts` 与 `rec_polys` 索引对应关系混乱，已有的 `y_min` 重排不足以消除所有错位
- **受影响的页**：page_005、page_010 等密度不均的页
- **定位方式**：在 JSON 里检查 `page_0XX.json → chars → box['y']` 顺序与 `char` 内容是否匹配

### 问题2：多字一框（如"八一"合框，只认到"八"）
- **症状**："八一"被同一个检测框包住，segmentation 只切出有字的那一半，下字完全缺失
- **根因**：`segment_block` 沿 Y 投影切分时，第二段高度太小被 `_merge_thin_segments` 合并回上一段（阈值过宽）
- **典型位置**：page_005 左下角页码"481"的"八一"

### 问题3：假"口"字（连接笔画被当成独立字框）
- **症状**：两个字交界处的细微连接笔画被检测成独立框，rec 模型在那里只能识别出"口"或其他噪声字
- **根因**：PaddleOCR 检测器对竖排笔画的交界处敏感；`segment_block` 没有过滤这种极小框
- **当前状态**：尝试过滤 `w<8 && h<8` 仍不足以祛除，阈值需更仔细调节

### 问题4：文字分配循环取最后一个字（"琅玕"重叠）
- **症状**：某两个框的文字都显示"琅"，原真实的"玕"被覆盖成后面的字
- **根因**：旧版 `segment_page_chars` 代码有 `char = text_chars[-1]`（N+1个框拿到最后一个字）
- **当前状态**：已改成超出部分留空，但**尚未重跑验证**

### 问题5：竖排 Web UI 有框但无文字
- **症状**：右侧竖排译文面板空白（`columns` 有数据但前端不渲染）
- **根因**：疑似同一页面混入旧 book 的 cached data；前端 JS 画框/文字的绑定区域有 bug，空 char 的框不显示列
- **临时处理**：先重启 Web UI，若仍白页需看浏览器 console 报错

---

## 三、关键代码改动位置

```
src/gujiorc/ocr/pipeline.py
  - image_to_page() 函数中转：
      1. y_min（框顶边）重排 texts/polys/scores  ← 解决错位
      2. 调用 segment_page_chars(..., min_gap=args.gap)

src/gujiorc/ocr/segment.py
  - segment_block()：竖排路径 y 投影切分
      1. 加了 line_box["h"]>45 时动态降 min_gap 再切（page_005八一）
      2. 后置超 tall 框 1.8× median 自动一分为二（top/bot）
  - segment_page_chars()：
      1. 超出部分不再"挂最后"（修复琅玕重叠）
      2. 过滤极小框 w<8 && h<8 && 空 char
  - symbol_gap_repair()：列投影补漏字，标记 STATUS_UNRECOGNIZED
      1. col_tol=40 / min_gap=40 / density_thresh=0.03
      2. id 生成改用正则 `_last_num`（兼容 top/bot 后缀）

scripts/ocr_workbench.py
  - cmd_run() 中显式调用 symbol_gap_repair 并打印 added 数
```

---

## 四、接手人操作步骤

```bash
cd ~/Git/Public/xuan-migration/learn_system/ocr

# 一键重跑（清数据 + 识别 + 重启 Web UI）
./run_sanche10.sh
```

脚本动作：
1. 删除 `data_work/data`、`data_work/glyph_samples`、`data_work/logs`、`data_work/rare`
2. 调用 `scripts/ocr_workbench.py run data_work/sanche_pages --segment`
3. `pkill` 旧 Web UI → `local/app.py` 重启
4. 浏览器 `Cmd+Shift+R` 打开 http://127.0.0.1:8000

**验证点**：
- page_005"八一"是否拆成独立两个框（"八"+"一"都有 char）
- page_006"琅玕"是否不再两个框都是"琅"
- page_010 补扫框是否 ≤5 个
- 竖排译文面板是否显示文字

---

## 五、建议的修复顺序

1. **问题4（琅玕重叠）**：先确认重跑后是否解决，若未解决检查 `segment_page_chars` 内 text_chars 与 seg_boxes 的分配逻辑
2. **问题3（口字）**：在 `segment_block` 里加"极宽极窄框过滤"，或改 `_merge_thin_segments` 的 min_h_floor 为 6-8px
3. **问题2（八一合框）**：line_box["h"]>45 的 special case 可改为通用策略（所有超高框强制分 half）+ 密度判断下半是否真有文字
4. **问题1（错位）**：`y_min` 重排是第一次修复若仍有余错，改为"同列 y 连续同框只认一次"，或换 PP-OCRv4_det 模型
5. **问题5（Web UI 白页）**：打开 browser console 看报错，大概率是 `columns` 计算时 `char==''` 的框被过滤导致数组不一致

---

## 六、约束与偏好（来自历史 MEMORY）

- 用户偏好：`直接动手，不要反问`；观察效果后自行报告
- OCR 产物：所有数据在本地 `data_work/`，不强依赖 Google Drive
- 代码改动：只改这一项目的 `src/` 和 `scripts/`，不更新记忆库或 skill（避免污染）
- 如果需要换 PaddleOCR 模型（PP-OCRv4_det）或调参，先跑单页验证再批量
- 服务器不是在本地 Mac 上跑长期服务，Mac 只做开发测试