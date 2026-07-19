# 数据格式说明 v0.2（M1 最小集 + 工位10 预留）

对应 v1.1.1 §5–§6 的知识对象模型，只保留 M1 需要的字段。字段增删须更新本文件并升版本号。

> **v0.2（2026-07-16）**：为工位10 跨技法连接预留——`relation` 枚举增 `corresponds`/`equivalent`，主张增可选字段 `canon_refs`。两者可选、不强制，向后兼容存量数据。

## 1. 来源登记 corpus/<technique>/<work>/manifest.yaml

```yaml
source_id: src_yanbo_ed01          # 格式 src_<work>_ed<NN>
work_title: 煙波釣叟歌
edition_note: 通行本文字，占位底本；正式底本确认后升版
technique_id: qimen
rights_status: public_domain       # 枚举: public_domain / licensed / unknown(阻断)
files:
  - path: source/transcript_v1.md
    role: transcript               # 枚举: transcript / page_image / raw
    sha256: <文件哈希，由工具填写>
```

## 2. 原文证据片段 provenance.yaml（在 unit 目录内）

```yaml
source_spans:
  - source_span_id: ss_yanbo_ed01_p0001_s01   # 格式 ss_<work>_ed<NN>_p<NNNN>_s<NN>
    source_id: src_yanbo_ed01
    file: source/transcript_v1.md
    quote: 陰陽順逆妙難窮                      # 必须与转录文件逐字一致（校验强制）
    location: 第1页 第1句                      # 人类可读位置
```

## 3. 知识单元 unit.yaml

```yaml
unit_id: ku_qimen_000001           # 格式 ku_<technique>_<6位数字>
technique_id: qimen
source_id: src_yanbo_ed01
title: 阴阳顺逆与二至换局
span_ids: [ss_yanbo_ed01_p0001_s01]   # 本单元覆盖的全部原文片段
status: source_verified            # 枚举见 §5
created: "2026-07-10"
```

## 4. 主张 assertions.yaml

```yaml
assertions:
  - assertion_id: as_qimen_000001  # 格式 as_<technique>_<6位数字>
    proposition: 冬至后用阳遁、夏至后用阴遁，起局宫数以一、九为始
    proposition_id: pr_qimen_000001
    relation: supports             # 枚举: supports / qualifies / opposes / corresponds / equivalent
    evidence:
      - source_span_id: ss_yanbo_ed01_p0001_s02
        support_type: interpreted  # 枚举: direct(原文明说) / interpreted(通行解读)
    conditions: []                 # 适用条件，宁多勿漏
    exceptions: []
    school_ids: []                 # 流派归属，空 = 未标注
    canon_refs: []                 # 可选(工位10 预留): 本主张所踩的 canon 基元 concept_id，
                                   #   如 [co_shared_wuxing_01, co_shared_wuxing_02]（木、火）。
                                   #   空 = 未标注；工位10 立项前不强制，存量无需回填。
    status: machine_extracted      # 枚举见 §5
```

> **关于 `corresponds` / `equivalent` 与 `canon_refs`（工位10 跨技法连接预留）**
> 二者为工位10「跨技法连接」预留，见 `pipeline/HANDBOOK.md` 工位10 方案④。
> - `corresponds` / `equivalent`：跨技法对应关系升格为一等主张时使用（如"七政四余暖照 ≈ 八字调候"），走同套双模型复核与状态升级。
> - `canon_refs`：标注主张所踩的技法无关基元，使共享同一组基元的跨技法主张关联可涌现。
> 两者当前均为**可选、不强制**：校验器接受但不要求，存量 1317+ 条主张无需回填。工位10 正式立项后再决定是否强制。

## 5. 状态枚举（v1.1.1 §9.4）

```
source_verified / machine_extracted / cross_model_reviewed /
disputed / needs_expert / expert_verified / deprecated
```

## 6. 错误码（校验程序输出，v1.1.1 §9.7 子集）

```
SRC_001 来源文件缺失        SRC_003 哈希不匹配
TXT_001 引用与原文不一致    ID_001  编号格式错误
ID_002  编号重复            REF_001 引用的对象不存在
SCH_001 缺少必填字段        SCH_002 非法枚举值
SEM_001 主张没有任何证据
```
