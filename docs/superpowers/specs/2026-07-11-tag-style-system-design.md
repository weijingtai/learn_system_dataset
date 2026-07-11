# 十种 Tag 样式、个人定制与未来 Marketplace 接口设计

> 状态：已完成头脑风暴，待用户审阅书面规格
>
> 日期：2026-07-11
>
> 范围：仅覆盖 `TAG_SYSTEM_DESIGN.md` 定义的十种 Tag 物种及其个人样式定制；不设计全 App Theme，不建设 Marketplace 交易系统，只保留宿主主题和未来 Marketplace 接口。

## 1. 决策摘要

采用“方案 C：限定模板 + 语义槽 + 可替换 Renderer”。

系统由官方 Flutter/Dart 实现有限、稳定、版本化的 Tag 布局模板。所有用户拥有同一套个人定制能力，可通过可视化编辑、Theme YAML 高级面板、PNG/SVG 资源管理、导入、导出、复制、回滚和实时预览修改十种 Tag 的外观。

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
- `glyph_atlas`；
- `digit_atlas`；
- `finite_asset_map`；
- `state_asset`；
- `seal_grid`；
- `meter`；
- `line`；
- `hybrid`。

### 6.2 Counter 示例

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
author:
  local_display_name: 用户
license:
  type: personal
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
marketplace:
  eligible: false
  metadata_version: 1
```

首期 `license.type` 为 `personal`，`marketplace.eligible` 为 `false`。未来上架不更换包格式，只增加审核、权利、价格和发布记录。

### 13.2 版本治理

分别维护：

- package version；
- schema version；
- TagStyleEngine version；
- template version；
- asset integrity version。

未知字段默认忽略并记录；未知必需能力、未知模板或不兼容主版本必须回退，不得猜测渲染。

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
保存、启用、导出或回滚
```

同一编辑器同时提供：

- 可视化操作；
- YAML 高级面板；
- 资源浏览器；
- 实时预览；
- 导入和导出；
- 历史版本与回滚。

YAML 不是高级用户特权，只是同一能力的另一种操作方式。

### 14.1 编辑器必须显示的三条边界

```text
图片原始画布
Tag 实际容器
内容安全区
```

用户必须能同时看到三者，避免把图片像素尺寸误认为 Widget 尺寸。

## 15. Marketplace 预留，不在当前实施范围

当前只预留：

- 稳定 `package_id`；
- package type；
- 作者元数据；
- 许可元数据；
- 资产完整性；
- 兼容性；
- capabilities；
- previews；
- 未来审核状态槽；
- 未来 Marketplace 商品引用槽。

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

## 16. 安全、性能与资源预算

### 16.1 安全

- 拒绝 Dart、JavaScript、脚本和可执行内容；
- SVG 禁止外部引用和事件；
- ZIP 解包防路径穿越和压缩炸弹；
- 所有路径必须位于包内；
- 编译后 Bundle 使用内容哈希；
- 原始包和编译包隔离保存。

### 16.2 性能

预算至少覆盖：

- 单资产文件大小；
- PNG 解码像素；
- SVG 节点和路径复杂度；
- 单 Tag 图层数；
- 同屏 Tag 数；
- 同屏动画数；
- 编译缓存大小；
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
- 预览覆盖长短文字、数字、密度、主题和大字；
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
- 未知或损坏内容逐层 fallback；
- 动画仅使用白名单属性；
- 相同输入和引擎版本产生稳定的编译 Bundle；
- 性能预算在目标低端设备上通过实测。

## 19. 分阶段建议

### Phase A：契约和原型

- 定义 `TagRenderModel`、`DisplayContract` 和 `TagStyleHostAdapter`；
- 定义 Package、模板、Slot 和 Renderer Schema；
- 用现有五个奇门 Widget 建立迁移样本；
- 原型验证 PNG/SVG、safe area、nine-slice 和 Counter digit atlas；
- 建立确定性编译和 fallback 报告。

### Phase B：个人定制基础

- 完成十种 Tag 的基础模板；
- 建立 `TagStyleEditor`；
- 支持导入、导出、复制和回滚；
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

## 21. 待用户书面审阅

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

用户审阅本文件并确认后，下一步才进入 OpenSpec capability 拆分和实施计划。
