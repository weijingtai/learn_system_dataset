# Learn System Web 控制台：PRD、技术架构与分期实施规划

## 1. 产品需求文档（PRD）

### 1.1 项目愿景
将当前依托终端命令行、tmux 与离线 YAML 交互的古籍知识编译黑箱流水线（M1～M8），封装为面向最终用户的现代化、开箱即用的 Web 控制台。用户只需在浏览器中上传一本未标点的古籍电子文本（TXT/EPUB/Markdown），系统即可自动完成从文献清洗、断句分词、AI 知识抽取、双路比对、人机协同审核到最终一键下载/分发发布数据集的全生命周期。

### 1.2 核心用户旅程（User Flow）
1. **新建任务（Upload & Config）**：
   - 拖拽或选择上传书籍文本；
   - 选择流派与技术档案（TechniqueProfile，如七政/八字）；
   - 选择运行模式：`全自动快速模式（AI 代审）` 或 `专业审校模式（人工抽检/全审）`。
2. **流水线实时看板（Pipeline Visualizer）**：
   - 清晰的 8 步进度流水线（M1 到 M8 动态步骤条）；
   - WebSocket 实时下发阶段执行耗时、发现指标（生僻字数、语义窗口数、提取候选数）；
   - 自动在 M4/M6 阻塞节点触发状态转换。
3. **协同审核面板（Dual-Track Reviewer）**：
   - **AI 初审过滤**：后台大模型针对候选命题进行一轮置信度初筛；
   - **高置信放行**：对确定性高的主张自动标绿通过；
   - **疑难分歧人审**：仅将“两路 AI 抽取分歧”或“AI 置信度低”的少数边缘案例呈现给人，左侧原文高亮对照，右侧一键 `[采纳 / 修改 / 驳回]`。
4. **成果发布与下发（Export & Distribute）**：
   - M8 完成后，提供一键下载标准 Release Bundle（含知识图谱三元组与七段绝对偏移证据链）；
   - 预留云端服务推送接口（Firebase Config / Hosting / 自有 API Gateway）。

---

## 2. 技术选型与系统架构设计

```
                    ┌──────────────────────────────────────────────┐
                    │            Vue 3 + Vite 单页应用 (SPA)        │
                    │   Ant Design Vue (开箱即用) + Pinia + VueUse  │
                    └──────────────────────┬───────────────────────┘
                                           │ WebSocket (长连接双向控制)
                                           │ HTTP REST (文件上传/下载)
                    ┌──────────────────────▼───────────────────────┐
                    │               FastAPI 异步网关                │
                    │     Router / Controllers / BackgroundTasks   │
                    └──────────────────────┬───────────────────────┘
                                           │
             ┌─────────────────────────────┼─────────────────────────────┬─────────────────────────────┐
             ▼                             ▼                             ▼                             ▼
┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐
│     流水线编排服务       │   │    仓储层 (Repository)  │   │    数据分发器 (Plugin)  │   │   OCR 引擎适配器 (Port) │
│ PipelineOrchestrator    │   │  SQLAlchemy 2.0 Async   │   │   DataDistributorPort   │   │     OcrEnginePort       │
│  M1 → M2 → ... → M8     │   │ Repository 接口模式解耦  │   │ ┌─────────────────────┐ │   │ ┌─────────────────────┐ │
│ ┌─────────────────────┐ │   │                         │   │ │ LocalZipDistributor │ │   │ │ MacLocalPaddleOcr   │ │
│ │ AI Auto-Reviewer    │ │   │ [存储适配]              │   │ ├─────────────────────┤ │   │ ├─────────────────────┤ │
│ │ (置信初筛/批量代审) │ │   │ • 单机: aiosqlite (本地)│   │ │ FirebaseDistributor │ │   │ │ ColabLinuxRemoteOcr │ │
│ └─────────────────────┘ │   │ • 云端: Turso (libsql)  │   │ │ (留桩, 待后续扩展)  │ │   │ ├─────────────────────┤ │
│                         │   │ • 企业: PostgreSQL/MySQL│   │ └─────────────────────┘ │   │ │ MultimodalLlmVlmOcr │ │
└─────────────────────────┘   └─────────────────────────┘   └─────────────────────────┘   │ └─────────────────────┘ │
                                                                                          └─────────────────────────┘
```

### 2.0 电子文本与 OCR 双模输入支持
- **模式 A（电子文本直通模式，当前基线）**：
  - 用户上传 TXT / EPUB / Markdown，流水线进入 M1 摄取与 M2 规范化清洗；
  - **M2 专属文本清洗工作台（Sanitization Workbench）**：
    - 前端集成 **`md-editor-v3`**（现代化 Vue3 Markdown 编辑与高亮预览器）作为主文本视窗；
    - 联动展示底层 M2 编译器已实现的 **十三项清洗发现报告（SanitizationReport）**；
    - 以可视化数据表格列出：网站水印（watermark）、乱码占位符（replacement_char）、页眉页脚（header_footer）、转义残留（escape_residue）、生僻字（PUA）、紧邻重复（duplicate）等；
    - **交互与修补**：用户在表格中点击某项，左侧 `md-editor-v3` 原文自动滚动并高亮定位对应字句，支持用户一键确认系统建议补丁（Patch）或手动剔除脏数据，生成确定的 `DeterministicPatchSet` 后放行进入 M3。
- **模式 B（图像/古籍扫描件 OCR 模式，复用已有工程）**：
  - 用户上传 PDF / 图像压缩包，流水线进入 M2 古籍 OCR 解析，生成 `evidence_level: glyphbox_level` 字框坐标与切片底图；
  - 遇到疑难异体字或漏字时，前端无缝唤起既有的 **OCR 校订画布**（原 `ocr/local/static/index.html` 的 Vue3 + Element Plus 画布），人工微调框选手柄与字形后继续放行。

### 2.1 前端技术栈与全阶段 UI 设计清单
- **核心框架**：Vue 3 (Composition API) + Vite + TypeScript
- **组件库选型**：
  - **Ant Design Vue (ant-design-vue)**：全局统一框架、8 步流水线步骤条（Steps）、通用表格与对话框；
  - **md-editor-v3**：专门负责所有阶段（M1/M2/M3/M4/M6/M8）的 Markdown 全文渲染、语法高亮与文本光标定位；
  - **既有 OCR 画布组件**：专门负责 M2 扫描件模式的古籍底图与字框交互。
- **全阶段 M1～M8 交互视图设计方案**：
  - **M1（来源摄取）**：文件拖拽上传区 + 原始元数据解析卡片；
  - **M2（规范清洗/OCR）**：
    - 文本线：`md-editor-v3` + 13项清洗发现表格（Sanitization Workbench，支持水印/脏数据定位与剔除）；
    - 扫描线：既有 OCR 底图与字框校订画布；
  - **M3（结构切分与断句）**：文本窗口切分树 + 双模型断句对比预览面板；
  - **M4（知识命题抽取）**：双路（lane a / lane b）抽取主张对比视图，高亮语义分歧；
  - **M5（自动门禁校验）**：Gate 校验仪表盘，展示引文哈希、因果闭包、编码对账的红绿状态；
  - **M6（审核控制台）**：双栏审核台，AI 初审折叠，低置信/分歧项人机交互卡片（接受/修改/驳回）；
  - **M7（创世汇编快照）**：版本快照对象浏览器，展示冻结的 Canonical Knowledge 节点；
  - **M8（发布数据集出包）**：知识图谱力导向图预览 + 七段证据链顺藤摸瓜检索器 + 一键下载/分发按钮。

### 2.2 后端技术栈
- **核心网关**：FastAPI + Uvicorn（全异步）
- **长连接协议**：原生 WebSocket 双向通信通道
- **分层模式**：经典 **Domain Service + Repository Pattern**（领域驱动与仓储解耦）
  - 领域业务只依赖 `LedgerRepositoryPort` 与 `TaskRepositoryPort` 抽象接口；
  - 彻底解耦业务逻辑与具体底层数据库。
- **数据库适配引擎**：
  - **默认实现**：SQLite (`sqlite+aiosqlite`)；
  - **并发高阶选型**：**Turso (libsql)** —— 基于 Rust 重写的高并发分布式 SQLite 方案，规避传统文件级写锁；
  - **通用关系型迁移**：未来仅需更换一行连接字符串即可直接迁往 MySQL / PostgreSQL。

### 2.3 OCR 跨设备与多环境解耦层（OcrEnginePort）
为解决此前“PaddleOCR 在 Linux Colab 与 Mac 本地环境差异导致的运行摩擦”，设计统一的 OCR 解耦标准协议：
```python
class OcrEnginePort(ABC):
    @abstractmethod
    async def recognize_page(self, page_image_bytes: bytes, profile: OCRProfile) -> PageRecognitionResult:
        """输入单页图像字节与配置参数，输出带字框坐标、置信度与字符切片的标准结构"""
        pass
```
- **支持三套即插即用后端驱动**：
  1. `MacLocalPaddleDriver`（当前可用）：针对 macOS Apple Silicon (MPS / CoreML) 本地运行的 PaddleOCR/PyTorch 封装；
  2. `ColabRemoteHttpDriver`（云端 GPU 模式）：针对 Google Colab / Linux GPU 服务器，启动一个轻量级的 FastAPI 包装器，主控制台通过 HTTP/RPC 将页面切片远程派发给 Colab GPU 处理，天然绕过 Linux 上的桌面依赖冲突；
  3. `VlmMultimodalDriver`（未来大模型视图模式）：直接调用 Claude 3.5 Sonnet / GPT-4o / Qwen-VL 等多模态视觉大模型 API 进行古籍版面解析和坐标定位。
- **环境迁移透明**：业务层完全不关心 OCR 是跑在本地 CPU/Mac 还是云端 Colab GPU 上，仅通过配置切换 `OCR_ENGINE_DRIVER=colab_remote` 或 `mac_local` 即可。

---

## 3. 分期实施计划（Plans）与任务分解（Tasks）

### 阶段一：Prompt 资产化改造（解除固定 SHA-256 限制）
*在独立 Worktree 中先行完成，保证底层血缘自洽的同时彻底解耦硬编码哈希。*
- [ ] **Task 1.1**：创建独立工作树 `worktree-prompt-asset`；
- [ ] **Task 1.2**：抽离 Prompt 文本为版本化 Profile（如 `prompts/semantic_split/v1.0.yaml`）；
- [ ] **Task 1.3**：实现 PromptRegistry 动态自洽性对账（替代硬编码常数校验）；
- [ ] **Task 1.4**：全量单元测试与 Stage Gate 回归验证，确认绿标后合并回主分支并清理该 Worktree。

### 阶段二：Web 控制台后端基础设施（FastAPI + Repository）
*开辟新 Worktree `worktree-web-console` 开始构建 Web 应用。*
- [ ] **Task 2.1**：搭设 FastAPI 工程骨架与 Clean Architecture 目录；
- [ ] **Task 2.2**：实现 Repository 仓储抽象与 SQLite / Turso 驱动适配器；
- [ ] **Task 2.3**：封装 M1～M8 后台异步任务管理器，支持状态挂起与恢复；
- [ ] **Task 2.4**：实现 WebSocket 长连接通道，定义流水线状态推送与控制事件帧；
- [ ] **Task 2.5**：封装 AI Auto-Reviewer 代理服务（支持置信度阈值过滤与自动签发）；
- [ ] **Task 2.6**：留桩 `DataDistributorPort`，实现本地 ZIP 下载分发器。

### 阶段三：Vue 3 前端应用交付（Ant Design Vue）
- [ ] **Task 3.1**：初始化 Vite + Vue 3 + Ant Design Vue 项目脚手架；
- [ ] **Task 3.2**：实现书籍上传与任务模式选择页；
- [ ] **Task 3.3**：实现 8 步流水线全景大屏看板（实时展示 M1～M8 动态进度与日志）；
- [ ] **Task 3.4**：实现交互式协同审核界面（AI 高置信已过审折叠，低置信分歧高亮审核）；
- [ ] **Task 3.5**：实现一键发布包下载及状态结算页。

### 阶段四：联调闭环与回归验收
- [ ] **Task 4.1**：端到端连通测试（全自动 AI 代审模式 10 分钟出包）；
- [ ] **Task 4.2**：端到端连通测试（人机协同半自动模式，人工交互过审）；
- [ ] **Task 4.3**：合并回主分支并形成交付验收文档。
