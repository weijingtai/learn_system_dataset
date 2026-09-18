<template>
  <div class="m2-container">
    <!-- 顶部状态栏与操作 -->
    <a-card :bordered="false" class="m2-header-card" :body-style="{ padding: '12px 20px' }">
      <a-row justify="space-between" align="middle">
        <a-col>
          <a-space size="middle">
            <span class="panel-title">十三项清洗规则检出工作台</span>
            <a-tag color="blue">全书文本量 24,180 字</a-tag>
            <a-tag color="orange">共触发 {{ data.totalFindings }} 项异动</a-tag>
            <a-tag color="green">已确定清洗 {{ cleanedCount }} 项</a-tag>
            <a-tag color="red" v-if="deferredCount > 0">待裁决 {{ deferredCount }} 项</a-tag>
          </a-space>
        </a-col>

        <a-col>
          <a-space size="middle">
            <a-radio-group v-model:value="viewMode" size="small" button-style="solid">
              <a-radio-button value="cleaned">清洗后正文</a-radio-button>
              <a-radio-button value="raw">原始底稿</a-radio-button>
              <a-radio-button value="split">对照视图</a-radio-button>
            </a-radio-group>

            <a-button type="primary" :loading="cleaning" @click="handleRunFullCleaning">
              <template #icon><ReloadOutlined /></template>
              一键重洗 (Apply All)
            </a-button>

            <a-button @click="handleExportPatch">
              <template #icon><DownloadOutlined /></template>
              导出 Patch
            </a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 工作区主体：左侧/上侧 Markdown 视窗，右侧/下侧脏数据规则发现表 -->
    <div class="m2-layout">
      <!-- Markdown 视图区（使用 md-editor-v3） -->
      <div class="editor-section">
        <template v-if="viewMode === 'split'">
          <div class="split-view">
            <div class="split-pane">
              <div class="pane-header">【原始底本】未清洗含水印与生僻字</div>
              <MdEditor
                v-model="data.rawText"
                :preview-only="true"
                class="md-box"
                :theme="editorTheme"
              />
            </div>
            <div class="split-pane">
              <div class="pane-header">【规范清洗本】已去除水印/补齐PUA字形</div>
              <MdEditor
                ref="cleanedEditorRef"
                v-model="data.cleanedText"
                class="md-box"
                :theme="editorTheme"
              />
            </div>
          </div>
        </template>
        <template v-else-if="viewMode === 'raw'">
          <MdEditor
            v-model="data.rawText"
            class="md-box"
            :theme="editorTheme"
          />
        </template>
        <template v-else>
          <MdEditor
            ref="cleanedEditorRef"
            v-model="data.cleanedText"
            class="md-box"
            :theme="editorTheme"
          />
        </template>
      </div>

      <!-- 下方十三项规则检出脏数据列表表格 -->
      <div class="table-section">
        <a-card
          size="small"
          :bordered="false"
          title="十三项清洗规则流水与脏数据定位（点击行可高亮定位文本）"
          class="findings-card"
        >
          <template #extra>
            <a-space size="small">
              <a-select
                v-model:value="filterKind"
                size="small"
                style="width: 140px"
                placeholder="按规则种类筛选"
              >
                <a-select-option value="all">全量规则 (13项)</a-select-option>
                <a-select-option value="watermark">网站水印 (Watermark)</a-select-option>
                <a-select-option value="pua">生僻字 PUA</a-select-option>
                <a-select-option value="header_footer">页眉页脚残留</a-select-option>
                <a-select-option value="duplicate">紧邻段落重复</a-select-option>
                <a-select-option value="escape_residue">HTML转义残留</a-select-option>
              </a-select>
            </a-space>
          </template>

          <a-table
            :columns="columns"
            :data-source="filteredFindings"
            row-key="ruleId"
            size="small"
            :pagination="{ pageSize: 5 }"
            :custom-row="customRowHandler"
            :row-class-name="(record: SanitizationFindingItem) => (record.ruleId === activeFindingId ? 'active-row' : '')"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'ruleId'">
                <a-tag :color="getRuleColor(record.kind)">{{ record.ruleId }}</a-tag>
              </template>

              <template v-else-if="column.key === 'kind'">
                <span>{{ getKindLabel(record.kind) }}</span>
              </template>

              <template v-else-if="column.key === 'originalText'">
                <span class="dirty-snippet" :title="record.originalText">{{ record.originalText }}</span>
              </template>

              <template v-else-if="column.key === 'suggestedReplacement'">
                <span v-if="record.suggestedReplacement" class="clean-snippet">
                  {{ record.suggestedReplacement }}
                </span>
                <a-tag v-else color="default">直接剔除</a-tag>
              </template>

              <template v-else-if="column.key === 'span'">
                <span class="mono-span">[{{ record.startOffset }} : {{ record.endOffset }}]</span>
              </template>

              <template v-else-if="column.key === 'terminalState'">
                <a-tag :color="record.terminalState === 'cleaned' ? 'success' : 'warning'">
                  {{ record.terminalState === 'cleaned' ? '已清洗' : '待处理' }}
                </a-tag>
              </template>

              <template v-else-if="column.key === 'action'">
                <a-space size="small">
                  <a-button
                    type="link"
                    size="small"
                    @click.stop="toggleCleanItem(record)"
                  >
                    {{ record.terminalState === 'cleaned' ? '还原' : '采纳清洗' }}
                  </a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { ReloadOutlined, DownloadOutlined } from '@ant-design/icons-vue';
import { MdEditor } from 'md-editor-v3';
import 'md-editor-v3/lib/style.css';
import type { SanitizationWorkbenchData, SanitizationFindingItem } from '../types';
import { getM2SanitizationData, applyM2Cleaning } from '../api';
import { usePipelineStore } from '../stores/pipeline';

const pipelineStore = usePipelineStore();

const viewMode = ref<'cleaned' | 'raw' | 'split'>('split');
const editorTheme = ref<'light' | 'dark'>('light');
const cleaning = ref<boolean>(false);
const filterKind = ref<string>('all');
const activeFindingId = ref<string>('');

const cleanedEditorRef = ref<any>(null);

const data = ref<SanitizationWorkbenchData>({
  runId: '',
  rawText: '',
  cleanedText: '',
  findings: [],
  totalFindings: 0,
});

const columns = [
  { title: '规则编号', dataIndex: 'ruleId', key: 'ruleId', width: 170 },
  { title: '规则类别', dataIndex: 'kind', key: 'kind', width: 130 },
  { title: '检出原文片段', dataIndex: 'originalText', key: 'originalText', ellipsis: true },
  { title: '推荐替换 / 修复建议', dataIndex: 'suggestedReplacement', key: 'suggestedReplacement', width: 180 },
  { title: '字符跨度', key: 'span', width: 110 },
  { title: '状态', dataIndex: 'terminalState', key: 'terminalState', width: 90 },
  { title: '操作', key: 'action', width: 110 },
];

const cleanedCount = computed(
  () => data.value.findings.filter((f) => f.terminalState === 'cleaned').length
);

const deferredCount = computed(
  () => data.value.findings.filter((f) => f.terminalState !== 'cleaned').length
);

const filteredFindings = computed(() => {
  if (filterKind.value === 'all') return data.value.findings;
  return data.value.findings.filter((f) => f.kind === filterKind.value);
});

onMounted(async () => {
  await loadData();
});

async function loadData() {
  try {
    data.value = await getM2SanitizationData(pipelineStore.currentRunId);
  } catch (err) {
    console.error(err);
  }
}

function getRuleColor(kind: string): string {
  switch (kind) {
    case 'watermark':
      return 'volcano';
    case 'pua':
      return 'magenta';
    case 'header_footer':
      return 'orange';
    case 'duplicate':
      return 'purple';
    case 'escape_residue':
      return 'cyan';
    default:
      return 'blue';
  }
}

function getKindLabel(kind: string): string {
  switch (kind) {
    case 'watermark':
      return '网站广告水印';
    case 'pua':
      return 'PUA生僻字';
    case 'header_footer':
      return '页眉页脚残留';
    case 'duplicate':
      return '相邻重复段落';
    case 'escape_residue':
      return 'HTML实体残留';
    case 'replacement_char':
      return '占位乱码符';
    default:
      return '文本异动';
  }
}

function customRowHandler(record: SanitizationFindingItem) {
  return {
    onClick: () => {
      activeFindingId.value = record.ruleId;
      message.info(`已定位至规则 [${record.ruleId}]: ${record.originalText}`);
    },
  };
}

async function handleRunFullCleaning() {
  cleaning.value = true;
  try {
    const allRuleIds = data.value.findings.map((f) => f.ruleId);
    const updated = await applyM2Cleaning(pipelineStore.currentRunId, allRuleIds);
    data.value = updated;
    message.success('已应用 13 项清洗规则，脏数据清理完毕');
  } finally {
    cleaning.value = false;
  }
}

function toggleCleanItem(item: SanitizationFindingItem) {
  if (item.terminalState === 'cleaned') {
    item.terminalState = 'deferred';
    message.info(`已将 [${item.ruleId}] 置为保留状态`);
  } else {
    item.terminalState = 'cleaned';
    message.success(`已采纳 [${item.ruleId}] 清洗补丁`);
  }
}

function handleExportPatch() {
  const patchJson = JSON.stringify(
    {
      runId: pipelineStore.currentRunId,
      exportedAt: new Date().toISOString(),
      findingsCount: data.value.findings.length,
      patches: data.value.findings,
    },
    null,
    2
  );
  const blob = new Blob([patchJson], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `sanitization_patch_${pipelineStore.currentRunId || 'run'}.json`;
  a.click();
  URL.revokeObjectURL(url);
  message.success('已导出 DeterministicPatchSet 文件');
}
</script>

<style scoped>
.m2-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 190px);
  background: #f0f2f5;
}

.m2-header-card {
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}

.m2-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 12px;
  gap: 12px;
}

.editor-section {
  flex: 1;
  min-height: 280px;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  background: #fff;
}

.split-view {
  display: flex;
  height: 100%;
  gap: 8px;
}

.split-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
}

.pane-header {
  padding: 6px 12px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  font-size: 12px;
  font-weight: 600;
  color: #666;
}

.md-box {
  height: 100% !important;
  flex: 1;
}

.table-section {
  height: 260px;
  overflow: hidden;
}

.findings-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.findings-card :deep(.ant-card-body) {
  padding: 0;
  flex: 1;
  overflow-y: auto;
}

.dirty-snippet {
  font-family: monospace;
  background: rgba(255, 77, 79, 0.1);
  color: #cf1322;
  padding: 2px 4px;
  border-radius: 3px;
}

.clean-snippet {
  font-family: monospace;
  background: rgba(82, 196, 26, 0.1);
  color: #389e0d;
  padding: 2px 4px;
  border-radius: 3px;
  font-weight: 600;
}

.mono-span {
  font-family: monospace;
  color: #888;
  font-size: 11px;
}

:deep(.active-row) {
  background-color: #e6f4ff !important;
}
</style>
