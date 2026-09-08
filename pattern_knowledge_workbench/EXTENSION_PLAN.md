# 多术数扩展计划

## 统一扩展缝：TechniqueProfile

每个 `Technique` 以一个 `TechniqueProfile` 接入工作台。profile 声明该术数的事实语义、格局识别输入、条件表达、导入边界、校验契约、fixture 和客户端投影；共享审核、证据、版本、发布与注解模型。它不是复制一套 Flutter 页面，更不是把别的术数强塞进七政字段。

| Profile 部件 | 责任 |
| --- | --- |
| `FactSchema` | 定义该术数的输入事实、枚举、单位与有效组合。 |
| `Condition DSL` | 表示 Assertion 的前提、例外、优先级与可解释匹配。 |
| `ImportAdapter` | 把来源、旧库或结构化导入转换成候选，保留来源身份。 |
| validator | 验证事实、条件、引用、证据与发布资格，失败即阻断。 |
| fixture | 覆盖典型、例外、冲突与无匹配的确定性测试数据。 |
| client projection | 将获批 ReleaseBundle 投影为 School 主视图和不同观点，不能写回知识源。 |

## 接入范围

| Technique | FactSchema 焦点 | Condition DSL 焦点 | ImportAdapter / validator / fixture / client projection |
| --- | --- | --- |
| 七政四余 | 星体、宫位、相位、强弱、时地与坐标体系 | 星体关系、宫位、时间/地点、例外与优先级 | 迁移现有格局库；验证遗留条件和来源补齐；fixture 覆盖同形异派；投影现有首个 profile。 |
| 八字 | 四柱、干支、十神、藏干、旺衰、节令与用神上下文 | 日主、月令、组合、调候、从格及例外 | 导入经版本化的书目材料；验证节令与关系一致性；fixture 覆盖“丙日干 + 亥月”；按 School 展示论断差异。 |
| 紫微斗数 | 命盘宫位、星曜、四化、三方四正、限运 | 宫位组合、四化触发、限运、流派差异 | 导入星曜/宫位资料；验证宫位与四化引用；fixture 覆盖同盘不同派；投影关键分歧。 |
| 大六壬 | 月将、日干支、四课、三传、天将、地分 | 起课条件、课传关系、涉害/贼克等分支 | 导入课例和法则；验证起课事实与分支可重放；fixture 覆盖多分支；投影判断依据与异议。 |
| 奇门遁甲 | 阴阳遁、局数、九宫、九星、八门、八神、干支 | 局、宫、门星神、格局、时空与例外 | 导入局例和原典；验证局数、宫位与条件 DSL；fixture 覆盖不同排局；投影主派与相冲意见。 |

## 分期

### P0：共同可信内核

建立 TechniqueProfile 契约、跨术数的 Work/Edition/SourceSpan/Evidence/Assertion/ApplicabilityRule/ReviewDecision/ReleaseBundle 模型和 fail-closed validator。先让七政四余成为首个完整 profile，并给八字建立最小纵切 fixture；客户端只读编译产物。

### P1：新增术数 profile

在共同内核稳定后，逐个加入八字、紫微、大六壬、奇门 profile。每个新增术数必须先交付 `FactSchema`、Condition DSL、ImportAdapter、validator 与 fixture，最后才增加 client projection；复用审核、证据、注解和冲突呈现壳层。

### P2：跨 profile 产品能力

补充受控公开 Annotation、讨论与离线同步，支持跨术数检索和比较。Embedding 仅在来源、版本、审核和确定性召回已稳定后再评估，不能替代精确规则匹配或证据链。
