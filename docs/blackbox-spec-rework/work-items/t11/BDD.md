# T-11 BDD 验收场景

## B1 修正三行低估与实测数字写入

Given 权威源 `docs/blackbox-spec-rework/T-transcribe.md` 复核了 M1/M6/M8 的实测差距数字，
When 执行者查看架构规格 §19 表格，
Then 规格明确修正：
- M1：补 `pipeline/registry/works/`、`tools/ingest_epub.py`，差距补「转录不可由记录的 raw+tool 重放」；
- M6：补数据体全空：`496 rules`，`original_text` 非空 0，`is_verified=1` 为 0，`ge_ju_versions` 0 行，`conditions` 404，`chapter` 486；
- M8：将零命中假绿修正为「span→mentions 映射键碰撞：`148` span 塌缩为 18 键、6 组碰撞，修好解析后将链到错误页」。

## B2 遗漏项与判据命令补齐

Given 工程事实审查发现了 8 项严重阻断与遗漏，
When 执行者查看架构规格 §19 表格，
Then 表格补充对应行，且每行附可验证的判据命令，表格行数扩充至 21 行以上。

## B3 避免失效假设

Given `pipeline/requirements.txt` 已经存在，
When 执行者审查遗漏项列表，
Then 规格不得将「pipeline 无依赖声明」作为遗漏项写入。
