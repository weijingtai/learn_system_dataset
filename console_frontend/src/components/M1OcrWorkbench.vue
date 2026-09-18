<template>
  <div class="m1-container">
    <!-- 顶部工具栏 -->
    <a-card :bordered="false" class="toolbar-card" :body-style="{ padding: '12px 20px' }">
      <a-row justify="space-between" align="middle">
        <a-col>
          <a-space size="middle">
            <a-radio-group v-model:value="mode" button-style="solid" size="small">
              <a-radio-button value="select">
                <template #icon><SelectOutlined /></template> 选择模式
              </a-radio-button>
              <a-radio-button value="create">
                <template #icon><BorderOutlined /></template> 补标新框(N)
              </a-radio-button>
              <a-radio-button value="split">
                <template #icon><ScissorOutlined /></template> 拆分行(S)
              </a-radio-button>
            </a-radio-group>

            <a-divider type="vertical" />

            <a-switch v-model:checked="showBoxes" checked-children="显示字框" un-checked-children="隐藏字框" size="small" />

            <a-divider type="vertical" />

            <a-button size="small" :disabled="selectedIds.length < 2" @click="handleMergeBoxes">
              <template #icon><MergeCellsOutlined /></template> 合并选框 ({{ selectedIds.length }})
            </a-button>

            <a-dropdown :disabled="selectedIds.length !== 1">
              <a-button size="small">
                等分拆分 <DownOutlined />
              </a-button>
              <template #overlay>
                <a-menu @click="handleSplitN">
                  <a-menu-item key="2">等分 2 份</a-menu-item>
                  <a-menu-item key="3">等分 3 份</a-menu-item>
                  <a-menu-item key="4">等分 4 份</a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>

            <a-button size="small" danger :disabled="selectedIds.length === 0" @click="handleDeleteBoxes">
              <template #icon><DeleteOutlined /></template> 删除框
            </a-button>

            <a-divider type="vertical" />

            <!-- 缩放控制 -->
            <a-space size="small">
              <a-button size="small" shape="circle" @click="zoomOut">-</a-button>
              <span class="scale-label">{{ Math.round(scale * 100) }}%</span>
              <a-button size="small" shape="circle" @click="zoomIn">+</a-button>
              <a-button size="small" @click="resetZoom">适应视窗</a-button>
            </a-space>
          </a-space>
        </a-col>

        <a-col>
          <a-space size="middle" class="legend-bar">
            <span class="legend-item"><i class="dot normal"></i>正常字</span>
            <span class="legend-item"><i class="dot lowconf"></i>低置信</span>
            <span class="legend-item"><i class="dot rare"></i>生僻/异体</span>
            <span class="legend-item"><i class="dot fix"></i>人工已校</span>
            <span class="legend-item"><i class="dot selected"></i>当前选中</span>
            <a-button type="primary" size="small" :loading="saving" @click="handleSavePage">
              保存校正
            </a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 主工作区：左侧 OCR 画布，右侧字框检查侧边栏 -->
    <div class="workbench-body">
      <!-- 画布视窗 -->
      <div class="canvas-viewport" ref="viewportRef" @mousemove="onViewportMouseMove">
        <div
          class="stage-container"
          :class="[`mode-${mode}`]"
          :style="{ transform: `scale(${scale})`, transformOrigin: 'top left' }"
          @mousedown="onStageMouseDown"
        >
          <!-- 古籍背景底图 -->
          <img
            ref="bgImgRef"
            :src="pageData.imageUrl"
            alt="古籍底图"
            class="bg-image"
            draggable="false"
            @load="onImageLoaded"
          />

          <!-- 双栏中缝与行切线 (CutLines) -->
          <div
            v-for="(cutX, idx) in pageData.cutLines"
            :key="`cut_${idx}`"
            class="cut-line"
            :style="{ left: `${cutX}px` }"
            title="双栏中缝/切线"
          >
            <span class="cut-tag">中缝切线 {{ cutX }}px</span>
          </div>

          <!-- 单字外接矩形框 CharBoxes -->
          <template v-if="showBoxes">
            <div
              v-for="item in pageData.charBoxes"
              :key="item.id"
              :class="[
                'char-box',
                item.isRare ? (item.rareReason === 'low_conf' ? 'lowconf' : 'rare') : '',
                item.status === 'corrected' ? 'fix' : '',
                selectedIds.includes(item.id!) ? 'is-selected' : '',
              ]"
              :style="{
                left: `${item.bbox.x}px`,
                top: `${item.bbox.y}px`,
                width: `${item.bbox.width}px`,
                height: `${item.bbox.height}px`,
              }"
              @mousedown.stop="selectBox(item, $event)"
            >
              <span class="char-label">{{ item.char }}</span>

              <!-- 选中的单框微调手柄 -->
              <template v-if="selectedIds.length === 1 && selectedIds[0] === item.id">
                <span
                  v-for="h in ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']"
                  :key="h"
                  :class="['resize-handle', `h-${h}`]"
                  @mousedown.stop.prevent="startResize(item, h, $event)"
                ></span>
              </template>
            </div>
          </template>

          <!-- 框选橡皮筋指示 -->
          <div v-if="rubberBand" class="rubber-band" :style="rubberBandStyle"></div>
        </div>
      </div>

      <!-- 右侧侧边栏：选框属性检查与微调 -->
      <div class="sidebar-panel">
        <a-tabs default-active-key="detail" size="small">
          <a-tab-pane key="detail" tab="单字检测详情">
            <template v-if="currentSelectedBox">
              <a-card :bordered="false" size="small" class="property-card">
                <div class="box-preview-header">
                  <div class="char-avatar">{{ currentSelectedBox.char }}</div>
                  <div class="char-meta">
                    <div class="char-title">字符 ID: {{ currentSelectedBox.id }}</div>
                    <div class="char-sub">
                      置信度:
                      <a-tag :color="(currentSelectedBox.confidence || 0.95) > 0.85 ? 'green' : 'orange'">
                        {{ Math.round((currentSelectedBox.confidence || 0.95) * 100) }}%
                      </a-tag>
                    </div>
                  </div>
                </div>

                <a-divider style="margin: 12px 0" />

                <!-- 改字与灌字表单 -->
                <a-form layout="vertical" size="small">
                  <a-form-item label="修正识别字 (Char Text)">
                    <a-input-group compact>
                      <a-input
                        v-model:value="editCharInput"
                        placeholder="输入正确文字"
                        style="width: calc(100% - 70px)"
                        @pressEnter="applyCharEdit"
                      />
                      <a-button type="primary" @click="applyCharEdit">应用</a-button>
                    </a-input-group>
                  </a-form-item>

                  <a-form-item label="外接边界坐标 (BBox: X, Y, W, H)">
                    <a-row :gutter="8">
                      <a-col :span="12">
                        <a-input-number v-model:value="currentSelectedBox.bbox.x" prefix="X:" style="width: 100%" />
                      </a-col>
                      <a-col :span="12">
                        <a-input-number v-model:value="currentSelectedBox.bbox.y" prefix="Y:" style="width: 100%" />
                      </a-col>
                    </a-row>
                    <a-row :gutter="8" style="margin-top: 8px">
                      <a-col :span="12">
                        <a-input-number v-model:value="currentSelectedBox.bbox.width" prefix="W:" style="width: 100%" />
                      </a-col>
                      <a-col :span="12">
                        <a-input-number v-model:value="currentSelectedBox.bbox.height" prefix="H:" style="width: 100%" />
                      </a-col>
                    </a-row>
                  </a-form-item>

                  <a-form-item label="版面行列层级 (Line / Char Index)">
                    <a-row :gutter="8">
                      <a-col :span="12">
                        <a-input-number v-model:value="currentSelectedBox.lineIndex" prefix="行:" style="width: 100%" />
                      </a-col>
                      <a-col :span="12">
                        <a-input-number v-model:value="currentSelectedBox.charIndex" prefix="序:" style="width: 100%" />
                      </a-col>
                    </a-row>
                  </a-form-item>
                </a-form>
              </a-card>
            </template>
            <a-empty v-else description="在画布中点击文字框以查看与编辑单字" style="margin-top: 60px" />
          </a-tab-pane>

          <!-- 竖排古籍文字复核 -->
          <a-tab-pane key="vertical" tab="古籍竖排检视">
            <div class="vertical-preview-box">
              <div class="vpage">
                <div class="vcol" v-for="lineIdx in 3" :key="lineIdx">
                  <span
                    v-for="item in pageData.charBoxes.slice((lineIdx - 1) * 5, lineIdx * 5)"
                    :key="item.id"
                    :class="['vchar', selectedIds.includes(item.id!) ? 'active' : '', item.isRare ? 'rare' : '']"
                    @click="selectBox(item, $event)"
                  >
                    {{ item.char }}
                  </span>
                </div>
              </div>
            </div>
          </a-tab-pane>

          <!-- 疑似错位与低置信度诊断 -->
          <a-tab-pane key="diagnose" tab="异常诊断 (2)">
            <a-list size="small" :data-source="diagnosticIssues">
              <template #renderItem="{ item }">
                <a-list-item class="issue-item" @click="focusBoxById(item.boxId)">
                  <a-list-item-meta :title="item.title" :description="item.desc">
                    <template #avatar>
                      <a-tag :color="item.severity === 'error' ? 'red' : 'gold'">
                        {{ item.type }}
                      </a-tag>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
          </a-tab-pane>
        </a-tabs>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import {
  SelectOutlined,
  BorderOutlined,
  ScissorOutlined,
  MergeCellsOutlined,
  DeleteOutlined,
  DownOutlined,
} from '@ant-design/icons-vue';
import type { CharBoxItem, PageScanData } from '../types';
import { getM1PageScan, rectifyM1Ocr } from '../api';
import { usePipelineStore } from '../stores/pipeline';

const pipelineStore = usePipelineStore();

const mode = ref<'select' | 'create' | 'split'>('select');
const showBoxes = ref<boolean>(true);
const scale = ref<number>(0.9);
const saving = ref<boolean>(false);

const selectedIds = ref<string[]>([]);
const editCharInput = ref<string>('');

const viewportRef = ref<HTMLElement | null>(null);
const bgImgRef = ref<HTMLImageElement | null>(null);

const pageData = ref<PageScanData>({
  pageIndex: 1,
  imageUrl: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=900&auto=format&fit=crop&q=80',
  width: 760,
  height: 1080,
  charBoxes: [],
  cutLines: [380],
});

const currentSelectedBox = computed(() => {
  if (selectedIds.value.length === 0) return null;
  return pageData.value.charBoxes.find((b) => b.id === selectedIds.value[0]) || null;
});

const rubberBand = ref<{ x0: number; y0: number; x1: number; y1: number } | null>(null);

const rubberBandStyle = computed(() => {
  if (!rubberBand.value) return {};
  const d = rubberBand.value;
  const left = Math.min(d.x0, d.x1);
  const top = Math.min(d.y0, d.y1);
  const width = Math.abs(d.x1 - d.x0);
  const height = Math.abs(d.y1 - d.y0);
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
  };
});

const diagnosticIssues = ref([
  {
    boxId: 'c_1_8',
    type: '低置信度',
    severity: 'warning',
    title: '识别字「宗」置信度 72%',
    desc: '原字墨迹略有洇化，建议人工核验字形',
  },
  {
    boxId: 'c_1_13',
    type: '异体字',
    severity: 'error',
    title: '生僻字检出「传」',
    desc: '底图刻印使用繁体異體「傳」，已自动标记 PUA 转换桩',
  },
]);

onMounted(async () => {
  await loadPageScan();
});

async function loadPageScan() {
  try {
    const data = await getM1PageScan(pipelineStore.currentRunId, 1);
    pageData.value = data;
    if (data.charBoxes.length > 0) {
      selectedIds.value = [data.charBoxes[0].id!];
      editCharInput.value = data.charBoxes[0].char;
    }
  } catch (e) {
    console.error(e);
  }
}

function onImageLoaded() {
  // auto scale
  if (viewportRef.value) {
    const vpH = viewportRef.value.clientHeight;
    if (vpH > 200 && pageData.value.height > 0) {
      scale.value = Math.min(1.2, Math.max(0.6, (vpH - 40) / pageData.value.height));
    }
  }
}

function zoomIn() {
  scale.value = Math.min(2.0, +(scale.value + 0.1).toFixed(2));
}

function zoomOut() {
  scale.value = Math.max(0.4, +(scale.value - 0.1).toFixed(2));
}

function resetZoom() {
  scale.value = 0.9;
}

function selectBox(item: CharBoxItem, evt: MouseEvent) {
  if (evt.shiftKey || evt.metaKey) {
    // Multi-select
    if (selectedIds.value.includes(item.id!)) {
      selectedIds.value = selectedIds.value.filter((id) => id !== item.id);
    } else {
      selectedIds.value.push(item.id!);
    }
  } else {
    selectedIds.value = [item.id!];
    editCharInput.value = item.char;
  }
}

function focusBoxById(id: string) {
  selectedIds.value = [id];
  const target = pageData.value.charBoxes.find((b) => b.id === id);
  if (target) {
    editCharInput.value = target.char;
  }
}

function applyCharEdit() {
  if (!currentSelectedBox.value || !editCharInput.value) return;
  currentSelectedBox.value.char = editCharInput.value;
  currentSelectedBox.value.status = 'corrected';
  message.success(`已校订单字为「${editCharInput.value}」`);
}

function handleMergeBoxes() {
  if (selectedIds.value.length < 2) return;
  const boxes = pageData.value.charBoxes.filter((b) => selectedIds.value.includes(b.id!));
  const minX = Math.min(...boxes.map((b) => b.bbox.x));
  const minY = Math.min(...boxes.map((b) => b.bbox.y));
  const maxX = Math.max(...boxes.map((b) => b.bbox.x + b.bbox.width));
  const maxY = Math.max(...boxes.map((b) => b.bbox.y + b.bbox.height));
  const mergedChar = boxes.map((b) => b.char).join('');

  const newBox: CharBoxItem = {
    id: `c_merged_${Date.now()}`,
    char: mergedChar,
    lineIndex: boxes[0].lineIndex,
    charIndex: boxes[0].charIndex,
    bbox: {
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY,
    },
    status: 'corrected',
  };

  pageData.value.charBoxes = [
    ...pageData.value.charBoxes.filter((b) => !selectedIds.value.includes(b.id!)),
    newBox,
  ];
  selectedIds.value = [newBox.id!];
  editCharInput.value = mergedChar;
  message.success(`成功合并 ${boxes.length} 个字框`);
}

function handleSplitN({ key }: { key: string }) {
  if (selectedIds.value.length !== 1 || !currentSelectedBox.value) return;
  const n = parseInt(key, 10);
  const cur = currentSelectedBox.value;
  const isVertical = cur.bbox.height >= cur.bbox.width;
  const count = n;
  const newBoxes: CharBoxItem[] = [];

  for (let i = 0; i < count; i++) {
    if (isVertical) {
      const stepH = Math.floor(cur.bbox.height / count);
      newBoxes.push({
        id: `c_split_${Date.now()}_${i}`,
        char: cur.char[i] || '□',
        lineIndex: cur.lineIndex,
        charIndex: cur.charIndex + i,
        bbox: {
          x: cur.bbox.x,
          y: cur.bbox.y + i * stepH,
          width: cur.bbox.width,
          height: stepH - 2,
        },
        status: 'corrected',
      });
    } else {
      const stepW = Math.floor(cur.bbox.width / count);
      newBoxes.push({
        id: `c_split_${Date.now()}_${i}`,
        char: cur.char[i] || '□',
        lineIndex: cur.lineIndex,
        charIndex: cur.charIndex + i,
        bbox: {
          x: cur.bbox.x + i * stepW,
          y: cur.bbox.y,
          width: stepW - 2,
          height: cur.bbox.height,
        },
        status: 'corrected',
      });
    }
  }

  pageData.value.charBoxes = [
    ...pageData.value.charBoxes.filter((b) => b.id !== cur.id),
    ...newBoxes,
  ];
  selectedIds.value = newBoxes.map((b) => b.id!);
  message.success(`单框已拆分为 ${n} 份`);
}

function handleDeleteBoxes() {
  if (selectedIds.value.length === 0) return;
  pageData.value.charBoxes = pageData.value.charBoxes.filter(
    (b) => !selectedIds.value.includes(b.id!)
  );
  message.info(`已删除 ${selectedIds.value.length} 个字框`);
  selectedIds.value = [];
}

async function handleSavePage() {
  saving.value = true;
  try {
    await rectifyM1Ocr({
      run_id: pipelineStore.currentRunId,
      page_index: pageData.value.pageIndex,
      action: 'save_all',
      payload_json: JSON.stringify(pageData.value),
    });
    message.success('M1 古籍字框校订结果已保存入库');
  } finally {
    saving.value = false;
  }
}

function onStageMouseDown(e: MouseEvent) {
  if (mode.value === 'create') {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const x = Math.round((e.clientX - rect.left) / scale.value);
    const y = Math.round((e.clientY - rect.top) / scale.value);
    rubberBand.value = { x0: x, y0: y, x1: x + 10, y1: y + 10 };

    const onMouseMove = (moveEvt: MouseEvent) => {
      if (!rubberBand.value) return;
      rubberBand.value.x1 = Math.round((moveEvt.clientX - rect.left) / scale.value);
      rubberBand.value.y1 = Math.round((moveEvt.clientY - rect.top) / scale.value);
    };

    const onMouseUp = () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      if (rubberBand.value) {
        const w = Math.abs(rubberBand.value.x1 - rubberBand.value.x0);
        const h = Math.abs(rubberBand.value.y1 - rubberBand.value.y0);
        if (w > 10 && h > 10) {
          const newBox: CharBoxItem = {
            id: `c_new_${Date.now()}`,
            char: '？',
            lineIndex: 0,
            charIndex: pageData.value.charBoxes.length,
            bbox: {
              x: Math.min(rubberBand.value.x0, rubberBand.value.x1),
              y: Math.min(rubberBand.value.y0, rubberBand.value.y1),
              width: w,
              height: h,
            },
            status: 'corrected',
          };
          pageData.value.charBoxes.push(newBox);
          selectedIds.value = [newBox.id!];
          editCharInput.value = '？';
          message.success('已补标新字框');
        }
        rubberBand.value = null;
      }
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }
}

function startResize(item: CharBoxItem, handle: string, e: MouseEvent) {
  const orig = { ...item.bbox };
  const startX = e.clientX;
  const startY = e.clientY;

  const onMouseMove = (moveEvt: MouseEvent) => {
    const dx = Math.round((moveEvt.clientX - startX) / scale.value);
    const dy = Math.round((moveEvt.clientY - startY) / scale.value);

    let { x, y, width, height } = orig;

    if (handle.includes('e')) width = Math.max(10, orig.width + dx);
    if (handle.includes('w')) {
      const nw = Math.max(10, orig.width - dx);
      x = orig.x + (orig.width - nw);
      width = nw;
    }
    if (handle.includes('s')) height = Math.max(10, orig.height + dy);
    if (handle.includes('n')) {
      const nh = Math.max(10, orig.height - dy);
      y = orig.y + (orig.height - nh);
      height = nh;
    }

    item.bbox = { x, y, width, height };
  };

  const onMouseUp = () => {
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
  };

  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
}

function onViewportMouseMove() {
  // Can be used for hover or magnifier coordinate tracking
}
</script>

<style scoped>
.m1-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 190px);
  background: #f0f2f5;
}

.toolbar-card {
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  z-index: 10;
}

.scale-label {
  display: inline-block;
  min-width: 48px;
  text-align: center;
  font-family: monospace;
  font-size: 13px;
  color: #555;
}

.legend-bar {
  font-size: 12px;
  color: #666;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.legend-item .dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  border: 1.5px solid #1677ff;
}

.legend-item .dot.normal {
  border-color: #1677ff;
}
.legend-item .dot.lowconf {
  border-color: #faad14;
  background: rgba(250, 173, 20, 0.2);
}
.legend-item .dot.rare {
  border-color: #ff4d4f;
  background: rgba(255, 77, 79, 0.2);
}
.legend-item .dot.fix {
  border-color: #52c41a;
  background: rgba(82, 196, 26, 0.2);
}
.legend-item .dot.selected {
  border-color: #fa8c16;
  background: rgba(250, 140, 22, 0.4);
}

.workbench-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.canvas-viewport {
  flex: 1;
  background: #2a2a2c;
  overflow: auto;
  position: relative;
  display: flex;
  padding: 24px;
}

.stage-container {
  position: relative;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  background: #111;
  user-select: none;
  display: inline-block;
}

.stage-container.mode-create {
  cursor: crosshair;
}

.stage-container.mode-split {
  cursor: row-resize;
}

.bg-image {
  display: block;
  width: 760px;
  height: auto;
  pointer-events: none;
}

.cut-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ff4d4f;
  box-shadow: 0 0 6px rgba(255, 77, 79, 0.8);
  z-index: 4;
}

.cut-tag {
  position: absolute;
  top: 8px;
  left: 6px;
  background: rgba(255, 77, 79, 0.9);
  color: #fff;
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 2px;
  white-space: nowrap;
}

.char-box {
  position: absolute;
  border: 1.5px solid #1677ff;
  background: rgba(22, 119, 255, 0.05);
  cursor: pointer;
  z-index: 5;
  transition: border-color 0.15s, background-color 0.15s;
}

.char-box.lowconf {
  border-color: #faad14;
  background: rgba(250, 173, 20, 0.12);
}

.char-box.rare {
  border-color: #ff4d4f;
  background: rgba(255, 77, 79, 0.15);
}

.char-box.fix {
  border-color: #52c41a;
  background: rgba(82, 196, 26, 0.12);
}

.char-box.is-selected {
  border: 2px solid #fa8c16 !important;
  background: rgba(250, 140, 22, 0.25) !important;
  z-index: 10;
  box-shadow: 0 0 0 2px rgba(250, 140, 22, 0.4);
}

.char-label {
  position: absolute;
  top: -18px;
  left: -2px;
  background: rgba(22, 119, 255, 0.85);
  color: #fff;
  font-size: 11px;
  line-height: 14px;
  padding: 1px 3px;
  border-radius: 2px;
  white-space: nowrap;
  pointer-events: none;
}

.char-box.is-selected .char-label {
  background: #fa8c16;
}

.resize-handle {
  position: absolute;
  width: 8px;
  height: 8px;
  background: #fa8c16;
  border: 1px solid #fff;
  border-radius: 1px;
  z-index: 12;
}

.resize-handle.h-nw { top: -4px; left: -4px; cursor: nwse-resize; }
.resize-handle.h-n  { top: -4px; left: calc(50% - 4px); cursor: ns-resize; }
.resize-handle.h-ne { top: -4px; right: -4px; cursor: nesw-resize; }
.resize-handle.h-e  { top: calc(50% - 4px); right: -4px; cursor: ew-resize; }
.resize-handle.h-se { bottom: -4px; right: -4px; cursor: nwse-resize; }
.resize-handle.h-s  { bottom: -4px; left: calc(50% - 4px); cursor: ns-resize; }
.resize-handle.h-sw { bottom: -4px; left: -4px; cursor: nesw-resize; }
.resize-handle.h-w  { top: calc(50% - 4px); left: -4px; cursor: ew-resize; }

.rubber-band {
  position: absolute;
  border: 1.5px dashed #fa8c16;
  background: rgba(250, 140, 22, 0.15);
  z-index: 20;
  pointer-events: none;
}

.sidebar-panel {
  width: 360px;
  background: #fff;
  border-left: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow-y: auto;
}

.box-preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.char-avatar {
  width: 48px;
  height: 48px;
  background: #fafafa;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 26px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1d1d1f;
}

.char-meta {
  flex: 1;
}

.char-title {
  font-weight: 600;
  font-size: 13px;
  color: #333;
}

.char-sub {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

.vertical-preview-box {
  background: #fcf9f2;
  border: 1px solid #e8e2d2;
  border-radius: 6px;
  padding: 16px;
  min-height: 280px;
}

.vpage {
  display: flex;
  flex-direction: row-reverse;
  gap: 16px;
  justify-content: center;
}

.vcol {
  writing-mode: vertical-rl;
  font-size: 17px;
  line-height: 2;
  letter-spacing: 4px;
  color: #2c2416;
}

.vchar {
  cursor: pointer;
  padding: 2px;
  border-radius: 3px;
  transition: all 0.2s;
}

.vchar:hover {
  background: rgba(22, 119, 255, 0.15);
}

.vchar.active {
  background: #fa8c16;
  color: #fff;
}

.vchar.rare {
  color: #ff4d4f;
  font-weight: bold;
}

.issue-item {
  cursor: pointer;
  border-radius: 4px;
  padding: 8px 6px;
  transition: background 0.2s;
}

.issue-item:hover {
  background: #fafafa;
}
</style>
