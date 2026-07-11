# 十种 Tag 样式、个人定制与未来 Marketplace 接口设计

> 状态：已完成头脑风暴，待用户审阅书面规格
>
> 日期：2026-07-11
>
> 范围：仅覆盖 `TAG_SYSTEM_DESIGN.md` 定义的十种 Tag 物种及其个人样式定制；不设计全 App Theme，不建设 Marketplace 交易系统，只保留宿主主题和未来 Marketplace 接口。

## 1. 决策摘要

采用“方案 C：限定模板 + 语义槽 + 可替换 Renderer”。

系统由官方 Flutter/Dart 实现有限、稳定、版本化的 Tag 布局模板。所有用户拥有同一套个人定制能力，可通过可视化编辑、Tag Style YAML 面板、PNG/SVG 资源管理、导入、导出、复制、回滚和实时预览修改十种 Tag 的外观。

用户不能上传或执行 Dart/Flutter 代码。用户输入仅限：

- Tag Style YAML；
- PNG；
- 受限 SVG。

首期只做个人定制。包格式从第一天预留未来分享、上架和销售所需的稳定 ID、版本、作者、许可、兼容性和预览元数据，但不提前建设 Marketplace 的账户、审核、支付、结算、退款或推荐系统。

## 2. 命名与边界

为了避免与其他 Agent 建设的全 App Theme 混淆，本规格不使用无前缀的 `ThemePackage`、`ThemeEngine` 或 `ThemeEditor`。

正式命名：

| 名称 | 职责 | 不负责 |
|---|---|---|
| `TagStylePackage` | 十种 Tag 的 YAML、资产、预览和元数据 | 页面、导航、按钮等 App UI |
| `TagStyleEngine` | 校验、编译、缓存和解析 Tag 样式 | 业务计算、知识判断和 Marketplace |
| `TagRenderer` | 将运行时语义值渲染为 Flutter Widget | 修改业务值 |
| `TagStyleEditor` | 编辑、预览、导入、导出和回滚个人样式 | 用户分级和交易 |
| `TagStyleHostAdapter` | 读取宿主亮暗模式、字体等有限 token | 控制 App Theme |
| `MarketplaceMetadata` | 预留未来商品识别字段 | 当前交易能力 |

### 2.1 与 App Theme 的唯一接口

`TagStyleHostAdapter` 可以读取：

- brightness；
- default font family；
- text scale；
- locale；
- reduced motion；
- high contrast；
- 少量经过命名空间隔离的宿主语义 token。

Tag Style 不得修改宿主 Theme。宿主 token 缺失时，Tag 必须使用包内默认值或官方 fallback。

## 3. 五条系统约束

### 3.1 四条硬约束

1. Tag Style 只能改变表现，不能修改知识对象、计算事实、业务逻辑或 Concept/Mark 绑定。
2. Tag Style 不能执行代码、访问网络或读取用户数据。
3. Tag Style 不能破坏基本可操作性；资产损坏、字段缺失或超出预算时必须安全回退。
4. Host 决定 Tag 容器尺寸，Style 只能在容器内渲染；用户图片的原始像素尺寸不得反向撑大 Widget。

### 3.2 一条显示契约规则

5. Style 可以自由选择允许的视觉 Renderer，但不能篡改绑定的语义值；是否允许模糊表达由 Host 的 `DisplayContract` 决定。

例如，未读消息数可以使用状态图案代替精确数字，但金额、验证码或宿主明确要求精确展示的值不能这样处理。即使视觉采用模糊状态，读屏和可达详情是否必须提供精确值仍由 `DisplayContract` 决定。

## 4. 核心架构

```text
Knowledge / Runtime System
        │
        │ TagRenderModel：只读语义值
        ▼
DisplayContract
        │ 允许的 Renderer、精度、溢出和可达性
        ▼
TagTemplate
        │ banner / seal / counter_badge / relation_line ...
        ▼
TagStyleVariant
        │ YAML + PNG + 受限 SVG
        ▼
TagStyleCompiler
        │ 校验、清理、优化、索引、生成报告
        ▼
CompiledTagStyleBundle
        │
        ▼
Flutter TagRenderer
        │
        ├── TagStyleHostAdapter → 外部 App Theme
        └── OfficialFallback    → 安全回退
```

### 4.1 对象职责

#### `TagRenderModel`

由业务层创建，只读，示例字段包括：

- `species`；
- `label`；
- `shortLabel`；
- `count`；
- `state`；
- `omen`；
- `sourceEntityId`；
- `targetEntityId`；
- `relationDirection`；
- `strength`；
- `disputeState`；
- `density`。

Style 无权改写这些字段。

#### `DisplayContract`

由宿主业务声明：

```yaml
display_contract:
  value_semantics: unread_count
  exact_visual_required: false
  exact_accessible_required: true
  allowed_renderers:
    - text
    - digit_atlas
    - state_asset
    - hybrid
  overflow:
    mode: cap
    max_value: 99
```

#### `TagTemplate`

由官方 Flutter/Dart 实现，定义有限且稳定的布局能力，不允许 YAML 任意创建 Flutter Widget 树。

首批模板：

- `inline_label`；
- `corner_badge`；
- `symbol_token`；
- `token`；
- `meter`；
- `relation_line`；
- `seal`；
- `grid_seal`；
- `banner`；
- `counter_badge`；
- `body_item`；
- `freeform_layered`。

`freeform_layered` 仍受图层数、anchor、offset、缩放、混合模式和动画白名单约束，不是任意布局语言。

### 4.2 Host Geometry

“Host 决定尺寸”同时覆盖矩形、路径和锚点三类几何契约：

```text
BoxHostGeometry
  constraints + resolvedSize + clipBounds

PathHostGeometry
  path + tangent + endpoints + clipBounds

AnchorHostGeometry
  anchor + allowedRadius + clipBounds
```

- `BoxHostGeometry` 用于令牌、印章、角标和面板；
- `PathHostGeometry` 用于 `RelationMark`，Style 只能修改 stroke、dash、端点图形和沿路径装饰，不能反转或重算关系路径；
- `AnchorHostGeometry` 用于附着于单点的 CornerMark 或装饰物。

Style 不能声明自身 Host Geometry，只能消费宿主提供的几何信息。

## 5. 分层合成模型

每个模板最多使用六层，不要求全部存在：

```text
Layer 5  interaction_overlay   宿主控制，主题不可修改
Layer 4  foreground            高光、前景纹理、覆盖装饰
Layer 3  semantic_slots        数字、名称、状态、图标
Layer 2  adornments            角标、祥云、灯笼、圆点
Layer 1  background            PNG、SVG、Shape、nine-slice
Layer 0  fallback_surface      官方安全回退
```

`interaction_overlay` 始终位于主题图层之上，保证用户图片不能遮挡点击、焦点或读屏语义。

Host 对 focus、selected、pressed、disabled、error 和 loading 保留最终状态可见性保障。Style 可以提供状态外观建议，但复杂图片不得让这些状态完全不可辨；Host 必要时叠加不可覆盖的轮廓、遮罩或语义提示。

### 5.1 Background

支持：

- 原生 Shape；
- PNG；
- 受限 SVG；
- nine-slice；
- 多个受限 layer 组成的背景。

### 5.2 Foreground

用于高光、纹理、覆盖装饰和非交互图案。必须 `pointer_events: none`，不得抢占宿主手势。

### 5.3 Content Safe Area

文字或语义图形不必以整张图片的数学中心对齐。每个背景可以声明内容安全区：

```yaml
background:
  asset: assets/token.png
  content_insets:
    left: 18%
    top: 12%
    right: 10%
    bottom: 12%
```

编辑器允许用户拖动、缩放安全区，并预览短文字、长文字、繁体和动态字号。

### 5.4 坐标空间与变换顺序

所有持久化位置、insets、anchor、offset 和切片范围默认使用 0–1 的 `normalized_space`，不得依赖源图片像素。

系统定义三个坐标空间：

- `asset_space`：原始文件像素或 SVG viewBox；
- `normalized_space`：经过方向和裁切归一化后的 0–1 画布；
- `container_space`：Flutter 逻辑像素中的最终 Host 区域。

渲染顺序固定为：

```text
decode original asset
  → normalize orientation and color profile
  → determine visible bounds
  → apply approved import crop
  → create normalized_space
  → calculate contain/cover/fill transform
  → transform safe area into container_space
  → apply nine-slice when supported
  → place semantic slots
  → place adornments and foreground
  → apply host state overlay
  → clip to host bounds
```

`cover` 裁切必须同步变换 safe area；nine-slice 的 center slice 必须在 `normalized_space` 内合法且具有非零中心区域，否则以 `ASSET_SLICE_INVALID` 进入 fallback。

## 6. 语义槽与可替换 Renderer

Slot 承载的是语义值，不规定必须用文字显示。

```text
业务事实 count=7
       │
       ├─ text             显示“7”
       ├─ digit_atlas      使用数字图片字形
       ├─ finite_asset_map 使用 7.png
       ├─ state_asset      使用“少量未读”图案
       └─ hybrid           图案 + 数字
```

### 6.1 Renderer 白名单

视觉 Renderer：

- `native_shape`；
- `png`；
- `svg`；
- `nine_slice`；
- `layer_group`。

语义 Renderer：

- `text`；
- `asset`；
- `asset_with_text`；
- `glyph`；
- `glyph_atlas`；
- `digit_atlas`；
- `finite_asset_map`；
- `state_asset`；
- `seal_grid`；
- `meter`；
- `line`；
- `endpoint_asset`；
- `hybrid`。

### 6.2 Capability Registry

模板、Renderer、物种和允许组合必须来自同一份版本化 `CapabilityRegistry`。文档矩阵、Schema、Editor 和 Engine 不得各自维护枚举。

```yaml
capability_registry:
  version: 1.0.0
  templates:
    symbol_token:
      since: 1.0.0
      supported_species: [ShenShaSymbol]
  renderers:
    glyph:
      since: 1.0.0
      input: single_asset
    glyph_atlas:
      since: 1.0.0
      input: asset_map
    endpoint_asset:
      since: 1.0.0
      supported_templates: [relation_line]
```

Package 编译时记录所用 Registry 版本。矩阵中出现而 Registry 未声明的 ID 一律报 `CAP_UNKNOWN`，不得猜测执行。

### 6.3 Counter 示例

数字图片字形包：

```text
digits/
├─ 0.svg
├─ 1.svg
├─ ...
├─ 9.svg
├─ plus.svg
└─ overflow.svg
```

```yaml
slots:
  value:
    bind: counter.count
    renderer: digit_atlas
    assets:
      "0": digits/0.svg
      "1": digits/1.svg
      "9": digits/9.svg
      plus: digits/plus.svg
    overflow:
      max_value: 99
      display: "99+"
```

状态图片映射：

```yaml
slots:
  value:
    bind: counter.count
    renderer: state_asset
    mapping:
      zero: assets/none.svg
      range_1_9: assets/few.svg
      range_10_99: assets/many.svg
      range_100_plus: assets/burst.svg
```

### 6.4 Counter 数值域

`Counter` 不能只假设正整数。每个 `DisplayContract` 必须声明是否支持：

- zero 的显示、隐藏或状态映射；
- positive integer；
- negative；
- decimal；
- unknown；
- overflow；
- compact notation，例如 `1.2K`；
- locale digits 和文字方向。

若使用 `digit_atlas`，能力声明必须覆盖该契约所需的 `0–9`、minus、decimal、plus、separator、overflow 和 unknown。缺失必需字形时必须 fallback，不能漏位、错位或改变数值。

## 7. 十种 Tag 能力矩阵

| Tag 物种 | 推荐模板 | 语义槽 | 允许的 Renderer | 容器约束 |
|---|---|---|---|---|
| `SymbolAnnotation` | `inline_label` | `label`、`icon` | text、asset、hybrid、glyph | 服从正文行高，不得撑高段落 |
| `CornerMark` | `corner_badge` | `role`、`icon` | text、asset、state_asset、hybrid | 由宿主角落区域决定 |
| `Insignia` | `token` / `meter` | `state`、`value`、`icon` | text、asset、meter、glyph_atlas、hybrid | full/mid/minimal 三档 |
| `RelationMark` | `relation_line` | `source`、`target`、`relation`、`strength` | line、glyph、endpoint_asset、hybrid | 宿主决定路径和端点，主题不能改关系方向 |
| `OmenIndicator` | `token` / `seal` | `omen`、`label`、`icon` | text、asset、state_asset、seal_grid、hybrid | Host 决定是否允许模糊表达 |
| `Vessel` | `freeform_layered` | `decoration` | asset、native_shape、layer_group | 不绑定业务文字，不扩大宿主布局 |
| `Counter` | `counter_badge` | `count`、`state` | text、digit_atlas、finite_asset_map、state_asset、hybrid | Host 定义精确值和溢出策略 |
| `ShenShaSymbol` | `symbol_token` | `identity`、`label`、`dispute_state` | text、asset、state_asset、hybrid | 争议状态是独立槽 |
| `StarBodyItem` | `body_item` | `identity`、`label`、`state` | text、asset、hybrid | 不改变盘中业务位置 |
| `Configuration` | `banner` / `seal` / `grid_seal` | `pattern`、`omen`、`label`、`status` | text、asset、seal_grid、state_asset、hybrid | 支持长短名称和四字印章 |

## 8. 图片尺寸、裁切与布局稳定性

### 8.1 容器优先

```text
Host 页面布局决定可用尺寸
          ↓
Tag Species 选择 full/mid/minimal
          ↓
Style 将图片适配到容器
          ↓
语义内容在 safe area 内排版
          ↓
不兼容时降级或 fallback
```

禁止使用 PNG/SVG 原始尺寸直接决定 Flutter Widget 尺寸。

### 8.2 导入预处理

PNG 检查：

- 像素宽高和宽高比；
- 文件大小；
- 解码内存预算；
- 透明边距；
- 实际可见边界；
- 是否需要多倍率缓存；
- 是否适合放大。

SVG 检查：

- 有效 `viewBox`；
- 实际可见边界；
- 节点数、路径复杂度和嵌套深度；
- 禁止脚本、事件处理器、外部 URL、远程字体和 `foreignObject`；
- 限制昂贵滤镜和异常画布。

导入时可以生成优化副本，但必须保留原始资产供重新编辑。

### 8.3 Fit 模式

| 模式 | 行为 | 典型用途 |
|---|---|---|
| `contain` | 完整显示，允许留白 | 令牌、印章 |
| `cover` | 填满容器，允许裁切 | 纹理背景 |
| `fill` | 强制拉伸 | 可变形背景 |
| `scale_down` | 只缩小不放大 | 低清图片 |
| `nine_slice` | 四角固定，中部拉伸 | 令牌、边框、面板 |
| `tile` | 平铺 | 纸张、纹理 |

### 8.4 文字或语义内容溢出

统一降级顺序：

1. 正常字号；
2. 缩小至模板允许的最小字号；
3. 在允许范围内换行；
4. 使用 `shortLabel`；
5. 使用 Host 允许的图形 Renderer；
6. 完整值进入详情和无障碍通道；
7. 回退官方 Tag。

不能无限缩小文字，也不能为了容纳文字让图片撑大页面。

## 9. 密度、尺寸和清晰度

必须分别建模：

- `density`：显示多少信息；
- `scale`：Tag 整体视觉尺寸；
- `text_scale`：系统动态字号；
- `asset_pixel_ratio`：图片清晰度。

```yaml
density_variants:
  full:
    show: [background, label, icon, adornments]
  mid:
    show: [background, short_label, icon]
  minimal:
    show: [icon]
```

不同物种可以拥有不同的实际尺寸，但使用相同的密度枚举。

## 10. 受限动画

允许属性：

- opacity；
- scale；
- translate_x；
- translate_y；
- rotation；
- color。

约束：

- 默认只允许单次出现动画；
- 循环动画必须由 Host 明确允许；
- 动画不能改变布局尺寸；
- 动画不能改变关系方向、计数或吉凶值；
- 支持 reduced motion；
- 每个动画必须提供静态终态；
- 图片加载完成不能导致 Tag 改变尺寸；
- 同屏动画数量和时间由 Host 预算控制。

现有 `ge_ju_template_small` 的祥云缩放与横移可以直接映射为白名单动画轨道。

## 11. 现有奇门 Widget 迁移映射

### 11.1 `GeJuPanelTemplateJi1`

映射为 `Configuration.banner`：多层背景、左右圆点、格局名称槽、吉章槽和三处祥云前景。

### 11.2 `GeJuPanelTemplateXiong1`

映射为 `Configuration.banner` 或 `OmenIndicator.token`：阶梯背景、灯笼 leading slot、格局名 slot 和“凶”状态 slot。支持原生 Shape 或完整 PNG/SVG 背景两种变体。

### 11.3 `ge_ju_template_small`

映射为 `Configuration.banner.minimal`：固定容器、多层装饰和受限 appear animation。

### 11.4 `TenGanKeYingGeJuDetail`

它是复合详情组件，不是纯 Tag。Tag Style 只控制其中的 Tag、印章和相关 token；详情卡页面布局归 App Theme 和业务组件。

### 11.5 `TenGanKeYingYinZhang`

映射为 `Configuration.grid_seal`。现有代码隐含“名称正好四字”的前提，新模板必须显式定义：

- 少于四字的 fallback；
- 正好四字的 2×2 竖排；
- 多于四字的 shortLabel 或其他模板 fallback；
- 书写顺序。

## 12. Fallback 与错误处理

每个语义槽采用统一回退链：

```yaml
fallback_chain:
  - user_variant
  - package_default
  - species_default
  - official_fallback
```

模板可以声明两种 fallback 粒度：

- `slot_fallback`：单个独立槽失败时只替换该槽；
- `variant_atomic_fallback`：关键槽任一失败时，整组回退到同一来源，避免用户背景、官方文字和另一套前景混成不可控样式。

```yaml
fallback_policy:
  mode: variant_atomic_fallback
  atomic_groups:
    - [background, label_style, foreground]
```

编译报告必须列出实际回退来源；用户启用前能够预览回退后的最终结果。

导入结果：

- `ACCEPT`：完整启用；
- `ACCEPT_WITH_FALLBACK`：不兼容字段或资产回退，其余定制保留；
- `WARN`：允许使用，但报告清晰度、对比度或表达偏差；
- `REJECT`：存在代码执行、外部访问、语义篡改或无法安全解析。

个人审美和颜色映射不属于硬拒绝范围。用户可以把旺设为绿色、衰设为红色，也可以使用暗黑、古风、骷髅、火焰等视觉表达；系统可以给出表达或无障碍建议，但不能替用户决定个人审美。

## 13. TagStylePackage

```text
my-tag-style/
├─ manifest.yaml
├─ tokens.yaml
├─ assets.sha256
├─ species/
│  ├─ symbol_annotation.yaml
│  ├─ corner_mark.yaml
│  ├─ insignia.yaml
│  ├─ relation_mark.yaml
│  ├─ omen_indicator.yaml
│  ├─ vessel.yaml
│  ├─ counter.yaml
│  ├─ shen_sha_symbol.yaml
│  ├─ star_body_item.yaml
│  └─ configuration.yaml
├─ assets/
│  ├─ png/
│  └─ svg/
└─ previews/
```

### 13.1 Manifest

```yaml
package_id: tagstyle.example.my_style
package_type: tag_style
name: 我的 Tag 样式
version: 1.0.0
schema_version: 1
engine_compatibility:
  min: 1.0.0
  max_exclusive: 2.0.0
publisher_claim:
  display_name: 用户
  claimed_license: personal
capabilities:
  species:
    - Counter
    - Configuration
  renderers:
    - png
    - svg
    - digit_atlas
assets:
  integrity_manifest: assets.sha256
distribution_hints:
  package_type: tag_style
  metadata_version: 1
```

`publisher_claim` 只是用户自述，不是平台背书。首期包只用于个人定制，不包含平台权威的 eligibility、审核、商品或许可结论。

未来 Marketplace 必须把权威状态放在包外：

```text
TagStylePackageManifest
  用户可编辑的内容和作者自述

MarketplaceListing
  平台数据库中的商品、价格、发布和下架状态

MarketplaceAttestation
  平台签名的包哈希、审核版本、权利声明和兼容结果
```

Package 内的任何自报字段都不能直接提升为审核通过、可销售或权利已验证。

### 13.2 版本治理

分别维护：

- package version；
- schema version；
- TagStyleEngine version；
- template version；
- asset integrity version。

未知字段默认忽略并记录；未知必需能力、未知模板或不兼容主版本必须回退，不得猜测渲染。

确定性承诺分为两级：

1. `Deterministic compilation`：相同源包、Compiler、Capability Registry 和配置生成相同 Bundle 哈希；
2. `Rendering conformance`：在声明的平台矩阵内满足布局、语义和性能不变量，不承诺不同 Flutter、Skia/Impeller、字体、GPU 和 device pixel ratio 下逐像素相同。

视觉回归使用分平台 golden 和允许误差的感知 diff。

### 13.3 字体政策

首期不接受用户字体文件。Style 只能引用 Host 或官方字体稳定 ID，并必须提供系统 fallback：

```yaml
font_family: $host.default
font_family_fallback:
  - official.cjk_serif
  - system
```

自定义字体涉及版权、再分发许可、文件体积、生僻字覆盖和跨平台 shaping，未来如需支持必须另立 capability 和权利审核，不通过 PNG/SVG 旁路嵌入。

## 14. TagStyleEditor 用户流程

所有用户拥有相同能力，不区分普通和高级用户。

```text
新建或复制样式
      ↓
选择 Tag 物种和模板
      ↓
修改颜色 / 上传 PNG 或 SVG
      ↓
设置 fit、safe area、slot renderer
      ↓
预览短字、长字、数字、深浅模式和密度档
      ↓
查看兼容性与性能报告
      ↓
保存草稿、预览、启用、导出或回滚
```

同一编辑器同时提供：

- 可视化操作；
- YAML 高级面板；
- 资源浏览器；
- 实时预览；
- 导入和导出；
- 历史版本与回滚。

YAML 不是高级用户特权，只是同一能力的另一种操作方式。

复杂选项采用渐进披露，而不是用户身份分级：

```text
第一层：选择样式、换图和颜色
第二层：调整 fit、safe area 和尺寸档
第三层：调整语义槽 Renderer 和 fallback
第四层：YAML、动画和兼容性细节
```

### 14.1 编辑器必须显示的三条边界

```text
图片原始画布
Tag 实际容器
内容安全区
```

用户必须能同时看到三者，避免把图片像素尺寸误认为 Widget 尺寸。

拖动不是唯一操作方式。safe area、anchor 和 offset 同时提供数值输入、方向按钮微调、重置居中、键盘/开关控制和读屏播报；触控手柄命中区域不得小于 44×44pt。

编辑器提供“官方样式 / 当前启用 / 编辑草稿”快速比较，并生成 `StyleHealthReport`：

```text
安全：通过
兼容性：通过
性能：2 项警告
缺失状态：pressed、disabled
大字模式：文字溢出
部分回退：Counter 100+ 使用官方样式
未来上架材料：缺少图片权利说明
```

报告中的安全与兼容性结论来自校验器；审美、对比度和表达倾向属于建议，不作为个人主题的硬拒绝理由，除非已经破坏 Host 的基本可操作性。

### 14.2 Draft、Preview 与 Active 生命周期

编辑永远修改 Draft，不能直接修改当前启用 Bundle：

```text
DRAFT
  ↓ validate
VALIDATED
  ↓ compile in isolated preview
PREVIEWABLE
  ↓ atomic activate
ACTIVE
  ↓ runtime health failure or user rollback
ROLLED_BACK
```

- Draft 自动保存；
- 编辑器支持多步 undo/redo；
- 导入覆盖前自动备份；
- 只有完整编译成功的 Bundle 才能启用；
- 激活使用原子指针切换；
- 始终保留 last-known-good Bundle；
- App 异常退出后恢复 Draft 和上一个 ACTIVE，而不是半编译状态；
- 启用前展示最终 fallback 结果和差异摘要。

### 14.3 可视化编辑与 YAML 的唯一数据源

规范化 AST 是唯一 source of truth；可视化编辑器和 YAML 都操作同一个 Draft AST：

```text
YAML text
  → parse to Draft AST
  → schema validation
  → normalized AST
  → visual editor
  → canonical YAML export
```

YAML 有语法错误时保留最后一个有效 AST，并在原字段附近显示错误。Canonical export 不保证保留注释和原字段顺序，编辑器必须在用户首次切换到 YAML 时说明这一点。

### 14.4 作用域与覆盖优先级

Style 激活作用域至少区分 account、device、technique、scene、species、density 和 accessibility。首期可以只开放 account/device + species，但 Schema 必须保留稳定字段。

覆盖顺序由低到高固定为：

```text
official species fallback
  < package species default
  < technique override
  < scene override
  < density override
  < accessibility adaptation
  < host safety override
```

无障碍和 Host 安全层不可被 YAML 反向覆盖。部分 Package 的编辑源可以是 delta，但运行时 `CompiledTagStyleBundle` 必须 self-contained，不能依赖设备中另一个任意用户包。

## 15. Marketplace 预留，不在当前实施范围

当前只预留：

- 稳定 `package_id`；
- package type；
- 作者与许可的自述元数据；
- 资产完整性；
- 兼容性；
- capabilities；
- previews；
- 与包内容无关的未来 listing 引用槽。

当前明确不做：

- 公开分享；
- 上架；
- 搜索和推荐；
- 审核后台；
- 支付、抽成和结算；
- 退款；
- DRM；
- 创作者等级；
- 商品评价。

未来 Marketplace 是多业务平台，Tag Style 只是 `package_type: tag_style` 的一种商品，不为 Tag 建立独立商城协议。

平台审核、权利确认、可销售性、价格和下架状态不得写回用户可编辑 manifest；未来由 MarketplaceListing 和平台签名 Attestation 管理。

用户现在可以选择记录图片来源、许可名称、许可文件、是否允许再分发和是否允许商业销售，便于未来申请上架，但这些字段仍只是待审核材料。

## 16. 安全、性能与资源预算

### 16.1 安全

- 拒绝 Dart、JavaScript、脚本和可执行内容；
- SVG 禁止外部引用和事件；
- ZIP 解包防路径穿越、压缩炸弹、绝对路径、Windows 盘符、symlink、hardlink、重复 entry 和递归目录过深；
- 限制文件数量、单文件大小、总解压大小和压缩比；
- 文件名执行 Unicode 归一化并拒绝大小写碰撞；
- YAML 禁止无界 alias 展开；
- 依据文件内容检测 MIME，不信任扩展名；
- PNG 导出净化副本，移除非必要文本和隐私元数据，明确拒绝未支持的动画 PNG；
- 所有路径必须位于包内；
- 编译后 Bundle 使用内容哈希；
- 原始包和编译包隔离保存。

SVG sanitizer 采用允许列表，不采用只删除已知危险节点的 denylist。无法完整解析或超出复杂度预算时直接回退，不尝试容错执行。

### 16.2 性能

预算至少覆盖：

- 单资产文件大小；
- PNG 解码像素；
- SVG 节点和路径复杂度；
- 单 Tag 图层数；
- 同屏 Tag 数；
- 同屏动画数；
- 编译缓存大小；
- 本地原始包、Draft、历史和编译 Bundle 的总存储配额；
- 未引用资产的垃圾回收；
- 低端 Android 内存与帧时间。

具体数值由原型基准测试校准，不在未测试前伪造阈值。

## 17. 测试矩阵

### 17.1 功能

- 十种物种；
- 所有模板；
- 所有 Renderer；
- full/mid/minimal；
- 短字、长字、零值、极大计数；
- PNG、SVG、nine-slice；
- 缺失资产、损坏资产和未知字段；
- 导入、导出、复制和回滚。

### 17.2 视觉与无障碍

- 亮色和暗色；
- 最大动态字号；
- reduced motion；
- high contrast；
- 读屏精确值；
- 小手机、平板和横屏；
- 低清图片、异常透明边和错误 viewBox；
- Host 容器变化时不得溢出或撑大布局。

### 17.3 兼容性

- 新引擎读取旧包；
- 旧引擎遇到新模板；
- 缺失 Host token；
- Package Schema 主版本不兼容；
- 部分物种样式损坏时其他物种继续可用。

### 17.4 生命周期与安全

- Draft 自动保存和崩溃恢复；
- YAML 错误不污染最后有效 AST；
- Preview 与 ACTIVE 隔离；
- Bundle 原子激活和 last-known-good 回滚；
- slot 与 variant atomic fallback；
- 路径穿越、symlink、重复 entry、大小写碰撞和 YAML alias bomb；
- Package 自报 Marketplace 字段不得改变平台权威状态。

## 18. gStack 三角色验收

### 18.1 CEO Gate

- 当前只解决个人定制，不提前建设 Marketplace；
- Package 无需迁移即可在未来成为通用 Marketplace 的 `tag_style` 商品；
- 用户能够保存多个样式并在真实页面使用；
- 样式能力不侵入业务语义和 App Theme；
- 收集个人定制、复用和导出意愿，为未来增长判断提供证据。

### 18.2 Design Gate

- 用户理解图片画布、Tag 容器和内容安全区的区别；
- 用户能仅凭 PNG/SVG 创建可用 Tag；
- 用户能用图片代替 Counter 精确数字；
- 同一用户无需理解全部高级字段即可完成换图和调整；
- 预览覆盖长短文字、数字、密度、主题和大字；
- safe area 可用拖动、数值输入和无障碍控制完成；
- 编辑过程支持自动保存、undo/redo、退出恢复和启用前对比；
- 错误信息说明原因、影响和修复方法；
- 视觉自由不被错误地限制为官方颜色语法；
- fallback 发生时用户能够知道哪部分被替换。

### 18.3 Engineering Gate

- Host 控制尺寸；
- Style 不能修改 `TagRenderModel`；
- 用户输入不能执行代码或访问网络；
- PNG/SVG 经过确定性预处理；
- Slot 有明确类型和绑定；
- 模板、Schema、Engine 分别版本化；
- Capability Registry 是所有枚举的唯一来源；
- 坐标空间和变换顺序确定；
- Draft、Preview、Active 和回滚是原子状态转换；
- 未知或损坏内容逐层 fallback；
- 动画仅使用白名单属性；
- 相同输入、Compiler、Registry 和配置产生相同 Bundle 哈希；
- 分平台渲染满足 conformance，不要求跨平台逐像素一致；
- 性能预算在目标低端设备上通过实测。

## 19. 分阶段建议

### Phase A：契约和原型

- 定义 `TagRenderModel`、`DisplayContract` 和 `TagStyleHostAdapter`；
- 定义 Package、模板、Slot 和 Renderer Schema；
- 定义 Capability Registry、Host Geometry、坐标空间和变换顺序；
- 定义 Draft/Preview/Active 生命周期和作用域覆盖；
- 用现有五个奇门 Widget 建立迁移样本；
- 原型验证 PNG/SVG、safe area、nine-slice 和 Counter digit atlas；
- 建立确定性编译和 fallback 报告。

### Phase B：个人定制基础

- 完成十种 Tag 的基础模板；
- 建立 `TagStyleEditor`；
- 支持自动保存、undo/redo、导入、导出、复制、原子启用和回滚；
- 支持 full/mid/minimal 和宿主适配；
- 建立视觉、兼容性、安全和性能测试矩阵。

### Phase C：增长证据，不建设交易

- 观察创建、启用、复用、导出和多样式保存行为；
- 研究用户是否主动分享预览；
- 验证创作者供给和付费意愿；
- 证据成立后，再由独立 Marketplace 项目接入 `MarketplaceMetadata`。

## 20. 明确非目标

- 全 App Theme；
- 用户 Dart/Flutter 插件；
- 任意 Widget 树 DSL；
- 当前阶段 Marketplace；
- 用 Theme 修改业务数据；
- 用图片原始尺寸控制页面布局；
- 强制用户遵循官方旺衰颜色；
- 按用户身份区分编辑能力。

## 21. OpenSpec capability 拆分与验收纪律

本设计不能作为一个单体 capability 直接实施，至少拆为：

1. `tag-style-package-format`；
2. `tag-style-compilation-and-activation`；
3. `tag-style-rendering-contract`；
4. `tag-style-asset-safety`；
5. `tag-style-editor`；
6. `tag-style-host-integration`。

Marketplace 当前只保留接口 requirement，不建立 Marketplace capability。

每项 requirement 至少包含：

- REQ-ID 和 Decision ID；
- SHALL；
- 适用平台、版本、用户和作用域；
- Given/When/Then；
- 稳定错误码；
- 机器可判定谓词；
- 测试数据集；
- 证据产物；
- 回滚条件。

“足够的图层数”“受限 offset”“异常画布”“昂贵滤镜”“目标低端设备”“用户能够理解”和“稳定渲染”不得作为单独验收标准。它们必须在 Phase A 转成命名预算、设备档、任务成功率、错误率或布尔不变量。

## 22. 待用户书面审阅

本设计已经确认的产品决策：

- 十种 Tag 全部纳入；
- 采用方案 C；
- 用户只上传 YAML、PNG 和受限 SVG；
- 所有用户能力相同；
- 当前只做个人定制；
- 未来接入多业务 Marketplace；
- 支持 background、foreground、safe area 和完整图片载体；
- 支持图片代替 Counter 数字；
- 接受四条硬约束和一条 DisplayContract 规则；
- 与 App Theme 只通过 Host Adapter 接入。

本轮评审后补充并已给出解决方案：

- Capability Registry 消除模板和 Renderer 枚举漂移；
- 三类 Host Geometry 覆盖矩形、路径和锚点；
- normalized 坐标和固定变换顺序消除 safe area 歧义；
- Draft/Preview/Active 和 last-known-good 闭合启用生命周期；
- 规范化 AST 统一 YAML 与可视化编辑；
- 固定作用域和覆盖优先级；
- Marketplace 权威状态移出用户包；
- atomic fallback 避免混搭失真；
- 补齐字体、Counter 数值域、资源供应链和编辑器无障碍；
- 明确确定性编译与跨平台渲染 conformance 的差异；
- 拆分六项 OpenSpec capability。

用户审阅本文件并确认后，下一步才进入 OpenSpec capability 拆分和实施计划。
