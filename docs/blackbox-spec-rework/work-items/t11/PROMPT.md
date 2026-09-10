# T-11 Executor Prompt

你是 T-11 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t11/README.md`
- `docs/blackbox-spec-rework/work-items/t11/BDD.md`
- `docs/blackbox-spec-rework/work-items/t11/TDD.md`
- `docs/blackbox-spec-rework/work-items/t11/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 3 FAIL，T-11 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` 的 `## 19. 当前实现映射与差距` 表格中做以下修改：
   - **修正三行低估**：
     - `M1 Source Intake` 行：当前实现补充 `pipeline/registry/works/`、`tools/ingest_epub.py`；当前差距补充「转录不可由记录的 raw+tool 重放」；
     - `M6 Review Workbench` 行：当前差距明确补充实测数据体全空状态：`496 rules，original_text 非空 0，is_verified=1 为 0，ge_ju_versions 0 行，conditions 404，chapter 486`；
     - `M8 Dataset Compilation` 行：把原「零命中假绿」修正为「span→mentions 映射键碰撞：`148` span 塌缩为 18 键、6 组碰撞，修好解析后将链到错误页」；
   - **补充新增遗漏行（附判据命令）**：
     1. `工作台唯一键限制` ｜ `{patternId, schoolId}` 复合唯一键 ｜ 禁止多书多主张（`grep -n "uniqueKeys" -A3 pattern_knowledge_workbench/lib/database/tables.dart` 必 FAIL）
     2. `流派与书目混部` ｜ `ge_ju_schools` 表 ｜ 将 book(1) 与 school(2) 混存同表（`sqlite3 <db> "select type,count(*) from ge_ju_schools group by type"` 必 FAIL）
     3. `构建环境私有依赖` ｜ `pubspec.yaml` ｜ 依赖 192.168 内网包，干净环境不可构建（`grep -c "192.168" pattern_knowledge_workbench/pubspec.yaml` 现已在 R0 排期消除）
     4. `数据状态管理缺陷` ｜ `drift_database.dart` 与 `rule_list_page.dart` ｜ 启动覆盖本地库 + 保存即 verified（现已在 R0 排期消除）
     5. `测试宿主匮乏` ｜ 仓库测试套件 ｜ 全仓非 OCR 部分仅 1 个 748B 脚手架（`find . -name "test_*.py" -o -name "*_test.dart" | grep -v ocr/ | wc -l` 必 FAIL）
     6. `测试 Golden 不足` ｜ `pipeline/validators/goldens` ｜ 仅有 bazi/qtbj，无非八字 fixture（`find pipeline/validators/goldens -type f` 必 FAIL）
     7. `OCR 横排切分轴` ｜ `ocr/` 引擎 ｜ R7 横排分支取轴错误（见 `ocr/HANDOFF_OCR_FIXES.md:181-185`）
     8. `语义分层阻塞` ｜ `pipeline/TODO.md:12-14` ｜ 三项 P0 语义阻断：忠实性门禁缺失、命例/注文/通则分层未实现、条件例外未结构化
   - **注意铁律**：`pipeline/requirements.txt` 已存在且含环境自检，PLAN.md 中「pipeline 无依赖声明」的旧表述已不成立，**严禁计入遗漏**。
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t11/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 3 严格减少至 2，且 T-11 为 PASS）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: correct gap table with measured metrics and missing items`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、实测数字及全局 T 结果。
