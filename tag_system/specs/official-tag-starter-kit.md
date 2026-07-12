# Official Tag Starter Kit v0.1

> 状态：第一版规格，2026-07-11。
> 目标读者：官方软件开发者、设计师、AI agents、submodule 负责人。
> 范围：官方基础 Tag 图标包、官方预设样式包、TechniqueProfile、预览目录和 AI 设计生产流程。
> 非目标：用户 Tag 编辑器、Marketplace、用户上传 Lottie、用户 Dart/Flutter 插件、任意 Widget DSL。

## 1. 定位

`Official Tag Starter Kit` 是官方开发团队生产第一批可用 Tag 的内部规格。它解决一个非常具体的问题：

```text
没有 TagStyleEditor 时，
项目仍然必须拥有一整套官方可用 Tag，
并允许奇门、八字、六爻等 submodule 做小范围差异化。
```

本规格是 **v0.1 / 第一版**。第一版优先追求完整、清晰、可验证和可复用，不追求风格数量、复杂动效或商业化外观。

## 2. 第一版目标

第一版必须交付：

1. 一个默认官方基础包：`official_starter_clear`；
2. 十类 Mark/Tag 的基础视觉矩阵；
3. 至少三个 `TechniqueProfile`：`qimen`、`bazi`、`liuyao`；
4. 一个开发/设计内部预览目录；
5. 官方受控动效政策；
6. 给 AI agents 使用 UIUX Pro Max 产出设计的标准流程；
7. 后续 `TagStyleEngine Compiler MVP` 的 golden input。

第一版不允许把“官方包生产能力”误写成“用户编辑能力”。用户仍只会看到官方样式选择或 submodule 默认样式，不会看到完整编辑器。

## 3. 包结构

第一版官方包目录建议为：

```text
tag_system/official_starter_kit/
  official_starter_clear/
    manifest.yaml
    tokens.yaml
    motion_policy.yaml
    technique_profiles/
      qimen.yaml
      bazi.yaml
      liuyao.yaml
    species/
      symbol_annotation.yaml
      corner_mark.yaml
      insignia.yaml
      relation_mark.yaml
      omen_indicator.yaml
      vessel.yaml
      counter.yaml
      shen_sha_symbol.yaml
      star_body_item.yaml
      configuration.yaml
    assets/
      svg_static/
      png/
      lottie_official/
    previews/
      catalog.md
      matrices/
```

`official_starter_clear` 是第一版唯一必须完成的包。`official_dark` 和 `official_traditional` 等后续包必须复用同一结构，不能另建一套规则。

## 4. 十类基础视觉矩阵

| 物种 | 第一版目标 | 必备槽 | 基础资产形态 | 动效建议 |
|---|---|---|---|---|
| `SymbolAnnotation` | 正文内术语和注脚标记 | `label`、`icon` | 静态 SVG glyph + text style | 无或 appear fade |
| `CornerMark` | 角色角标与状态修饰角标 | `role` 或 `state_modifier` | 小 badge SVG | appear scale |
| `Insignia` | 旺衰、强弱、状态徽标 | `state`、`value` | Flutter shape + 灰度能量条 | value change fade |
| `RelationMark` | 生克合冲关系线 | `source`、`target`、`relation` | Flutter line + endpoint SVG | line reveal |
| `OmenIndicator` | 吉凶属性与条件入口 | `omen`、`condition_affordance` | token/seal SVG + text | appear only |
| `Vessel` | 非语义容器和背景装饰 | `decoration` | PNG/SVG background | ambient allowed |
| `Counter` | 数量角标 | `count`、`overflow` | text/digit atlas | number transition |
| `ShenShaSymbol` | 神煞标记 | `identity`、`dispute_state` | symbol token SVG | no loop |
| `StarBodyItem` | 星、门、神、干支等本体项 | `identity`、`state` | body glyph + state slot | state fade |
| `Configuration` | 格局、时干克应、印章 | `pattern`、`label`、`status` | banner/seal/grid_seal | stamp appear |

第一版每个物种至少要有：

- full / mid / minimal 三档；
- light / dark 两种显示条件；
- normal / reduced_motion 两种状态；
- official fallback；
- required slots 可达验证；
- 至少一个 qimen 样例；
- bazi 和 liuyao 的最小 profile 覆盖。

## 5. TechniqueProfile

`TechniqueProfile` 是 submodule 小范围定制的唯一入口。submodule 不应该复制整套资产，也不应该各自定义新的视觉语法。

```yaml
technique_profile:
  technique: qimen
  base_package: official_starter_clear
  default_density: mid
  allowed_species:
    - Insignia
    - RelationMark
    - OmenIndicator
    - ShenShaSymbol
    - Configuration
  overrides:
    Configuration:
      default_template: grid_seal
      density: full
      motion_allowed: appear_only
    RelationMark:
      density: on_demand
    ShenShaSymbol:
      required_slots:
        - identity
        - dispute_state
```

第一版允许 submodule 覆盖：

- 默认可见物种；
- 默认 density；
- 物种的默认 template；
- `required_slots` 的增补要求；
- motion policy 的收紧；
- technique 专属文案、短标签和预览样例；
- full / mid / minimal 的显示优先级。

第一版不允许 submodule 覆盖：

- MarkSpecies 的根本含义；
- 吉凶红线；
- 语义通道锁定规则；
- official reserved capability；
- 用户输入边界；
- Host Geometry 归属；
- `interaction_overlay`。

## 6. 三个第一版 profile

### 6.1 `qimen`

奇门第一版重点：

- `Configuration`：格局、时干克应、四字印章；
- `OmenIndicator`：吉凶属性必须绑定条件入口；
- `ShenShaSymbol`：争议状态必须可见；
- `RelationMark`：默认按需展示，不全盘铺满；
- `StarBodyItem`：门、星、神、干支只做最小状态位。

### 6.2 `bazi`

八字第一版重点：

- `Insignia`：旺衰、十二长生、空亡等状态；
- `RelationMark`：生克合冲刑害关系按需展开；
- `CornerMark`：十神、用忌、状态修饰；
- `Counter`：数量事实不得映射为吉凶；
- `Configuration`：格局候选只在详情或教学卡中展示。

### 6.3 `liuyao`

六爻第一版重点：

- `CornerMark`：世应、动爻、变爻、有变提示；
- `RelationMark`：爻间关系默认详情卡展开；
- `Insignia`：旺衰、空亡、月破等状态；
- `StarBodyItem`：本态/变态必须区分；
- `Configuration`：只保留候选接口，不作为盘面主视觉。

## 7. 官方受控动效

第一版允许官方包包含少量动效，但动效必须是官方受控能力，不是用户自由上传能力。

动效优先级：

1. Flutter 白名单动效：`opacity`、`scale`、`translate_x`、`translate_y`、`rotation`、`color`；
2. 官方 Lottie：只用于复杂但非语义判定的装饰或品牌化微动效；
3. 静态 fallback：每个动效必须提供。

第一版不把 animated SVG 作为运行时格式。设计师若提供 animated SVG，官方构建流程应转换成 Flutter 白名单动效或官方 Lottie。

```yaml
motion:
  mode: flutter_track
  trigger: appear
  properties: [opacity, translate_y]
  duration_ms: 180
  repeat: false
  reduced_motion_fallback: static
```

```yaml
motion:
  mode: official_lottie
  asset: assets/lottie_official/cloud_loop.json
  trigger: ambient
  repeat: host_budgeted
  max_duration_ms: 2400
  reduced_motion_fallback: assets/svg_static/cloud.svg
```

硬规则：

- 动效不得改变语义值、吉凶、关系方向、计数；
- 动效不得改变 layout 尺寸；
- 学习、测试和分享场景默认静态或 reduced motion；
- 凶类、争议状态、条件入口不得使用恐吓式循环动画；
- 同屏动画数量由 Host 控制；
- Lottie 只允许官方包使用；
- 用户包第一版不允许 Lottie 或 animated SVG。

## 8. 预览目录

第一版必须有一个内部 `Preview Catalog`，不等同于用户编辑器。

预览矩阵至少覆盖：

- 十类物种；
- full / mid / minimal；
- light / dark；
- qimen / bazi / liuyao；
- normal / reduced_motion；
- normal / fallback；
- 长标签、短标签、繁体、动态字号；
- required slots 缺失或 fallback 后的表现。

预览目录要回答三个问题：

1. 产品能否判断“第一版用户看起来已经完整”；
2. 设计能否判断“十类语法是否一致、清晰、不过度神秘化”；
3. 工程能否把它作为 compiler golden input。

## 9. AI agents 使用 UIUX Pro Max 的工作方式

AI agents 可以参与官方包设计，但必须按固定输入、固定产物和固定验收工作。不能让 AI agents 自由生成一堆风格图后直接进项目。

### 9.1 给 AI agent 的输入

每次派发设计任务时，必须提供：

```text
1. 本规格：tag_system/specs/official-tag-starter-kit.md
2. 主视觉语法：tag_system/TAG_SYSTEM_DESIGN.md §3
3. 对象模型：tag_system/specs/mark-taxonomy-and-registry-split.md
4. 样式约束：tag_system/specs/tag-style-system-design.md
5. 目标 technique profile：qimen / bazi / liuyao
6. 目标物种：十类中的一个或一组
7. 输出格式：SVG/PNG/Lottie/YAML/preview
```

### 9.2 必须使用的专业视角

AI agent 必须显式启用或模拟以下角色：

- UIUX Pro Max：可读性、可达性、动效、密度、跨平台；
- Marks 语义守门：断象不断事、吉凶三件套、required slots；
- Flutter 工程守门：Host Geometry、性能预算、reduced motion；
- Product 守门：第一版完整性，不追求编辑器。

### 9.3 单个 AI agent 的标准任务模板

```text
任务：为 official_starter_clear 设计 <species> 第一版视觉方案

输入：
- technique: qimen
- species: Configuration
- density: full/mid/minimal
- motion: appear_only
- required_slots: pattern,label,status

必须产出：
1. 视觉说明：形状、层级、颜色、文字、安全区；
2. full/mid/minimal 三档；
3. light/dark 适配；
4. reduced_motion fallback；
5. YAML 片段；
6. SVG/PNG/Lottie 资产清单；
7. 预览矩阵；
8. 自检：是否违反吉凶红线、required_slots、layout 稳定和无障碍。
```

### 9.4 设计结果进入项目的门槛

AI agent 的输出只有在通过以下检查后才能进入官方包：

- 不使用颜色单独承载语义；
- 不把旺衰映射成吉凶；
- 不使用恐吓式凶象动效；
- 不伪造 official reserved capability；
- required slots 全部可达；
- reduced motion 有静态 fallback；
- long label 和 dynamic type 不撑大 Host；
- submodule 覆盖只发生在 TechniqueProfile，不复制整包。

## 10. 开发顺序

第一版推荐顺序：

```text
A-6 Official Tag Starter Kit Spec
A-7 official_starter_clear 资产矩阵
A-8 TechniqueProfile for qimen/bazi/liuyao
A-9 Preview Catalog
T1-3 TagStyleCompiler MVP
T1-4 official_dark / official_traditional
```

不要先做完整编辑器。不要先做 Marketplace。不要先做十套风格。第一版只证明：官方包可以生产、可以预览、可以按 technique 覆盖、可以成为 compiler golden input。

## 11. 第一版验收

第一版通过条件：

- 十类物种均有 full / mid / minimal；
- qimen / bazi / liuyao 均有 TechniqueProfile；
- `official_starter_clear` 可作为唯一默认包；
- 动效全部有 reduced motion fallback；
- required slots 通过人工检查表；
- Preview Catalog 覆盖 §8 矩阵；
- 没有 TagStyleEditor 依赖；
- 没有 Marketplace 依赖；
- 没有用户 Lottie / animated SVG 输入；
- 产物可作为 TagStyleCompiler MVP 的 golden input。

## 12. 后续扩展

通过第一版后，才进入：

1. `official_dark`；
2. `official_traditional`；
3. 更多 technique profiles；
4. TagStyleCompiler MVP；
5. submodule 接入；
6. 经过数据验证后，再复审 TagStyleEditor。
