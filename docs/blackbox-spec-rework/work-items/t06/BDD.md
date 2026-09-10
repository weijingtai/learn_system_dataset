# T-06 BDD 验收场景

## B1 EvidenceMapPack 完整证据链路声明

Given 权威源 `LEARN_SYSTEM_TARGET.md §6` 确立了无损证据链的反向追溯模型，
When 执行者查看架构规格 §16 M8 Dataset Compilation 中关于 `EvidenceMapPack` 的定义，
Then 规格逐段明确写出完整证据链：`EvidenceLink → Assertion → SourceSpan → SourceAnchor → OcrPage / 字框坐标 → SourceAsset 页标识`，
And 规格明确声明：SourceAnchor 作为发布期证据锚点必须随包发布，严禁留在 M3 内部而不进发布包。

## B2 坐标系同源可换算强约束

Given 客户端最终需要打开原始扫描底本并精准高亮命中的字框区域，
When 执行者查看架构规格 §16 关于 `EvidenceMapPack` 的说明，
Then 规格明确写入硬约束：字框坐标系必须与 `SourceAssetPack` 中对应页图的像素尺寸同源可换算，防止因缩放、旋转或不同切片导致无法渲染。

## B3 发布期 fail-closed 门禁绑定

Given 任何证据断裂都会破坏系统的可解释性与学术严谨性，
When 执行者查看架构规格 §16 关于 `EvidenceMapPack` 的校验要求，
Then 规格明确声明：该链路的完整性是 `ValidationReport` 的 fail-closed 检查项，任一证据链断裂直接阻断 PublicationPackage 签发。
