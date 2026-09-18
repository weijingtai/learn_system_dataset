<template>
  <div class="review-container">
    <!-- 顶部状态看板与双轨初审统计 -->
    <a-card :bordered="false" class="review-header-card" :body-style="{ padding: '16px 20px' }">
      <a-row :gutter="16" align="middle">
        <a-col :span="6">
          <a-statistic title="待审知识命题总量" :value="queueItems.length">
            <template #suffix>条</template>
          </a-statistic>
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="第三方 AI 预审通过 (高置信放行)"
            :value="autoAcceptCount"
            :value-style="{ color: '#3f8600' }"
          >
            <template #prefix><CheckCircleOutlined /></template>
            <template #suffix>条</template>
          </a-statistic>
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="AI 标记疑难分歧 (需人工裁决)"
            :value="humanRequiredCount"
            :value-style="{ color: '#cf1322' }"
          >
            <template #prefix><ExclamationCircleOutlined /></template>
            <template #suffix>条</template>
          </a-statistic>
        </a-col>
        <a-col :span="6" style="text-align: right">
          <a-space direction="vertical" align="end">
            <a-space>
              <a-button @click="handleBatchAcceptAI">
                一键批量采纳 AI 预审
              </a-button>
              <a-button type="primary" :loading="submitting" @click="handleSubmitBatch">
                <template #icon><SendOutlined /></template>
                提交复核决策并放行
              </a-button>
            </a-space>
            <span class="sub-hint">已决策 {{ decidedCount }} / {{ queueItems.length }} 项</span>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <a-space size="middle">
        <a-radio-group v-model:value="filterTab" size="small" button-style="solid">
          <a-radio-button value="all">全量列表 ({{ queueItems.length }})</a-radio-button>
          <a-radio-button value="divergent">需人工复核 ({{ humanRequiredCount }})</a-radio-button>
          <a-radio-button value="ai_pass">AI 自动放行 ({{ autoAcceptCount }})</a-radio-button>
          <a-radio-button value="decided">已完成裁决 ({{ decidedCount }})</a-radio-button>
        </a-radio-group>

        <a-input-search
          v-model:value="searchKeyword"
          placeholder="按命题或引文关键字检索..."
          size="small"
          style="width: 260px"
        />
      </a-space>
    </div>

    <!-- 审核列表主体 -->
    <div class="review-body">
      <a-empty v-if="filteredList.length === 0" description="暂无符合条件的待审命题" />

      <a-card
        v-for="item in filteredList"
        :key="item.queueItemId"
        class="review-item-card"
        :bordered="false"
        size="small"
      >
        <div class="item-header">
          <a-space size="small">
            <a-tag color="purple">{{ item.targetEntityId }}</a-tag>
            <a-tag :color="item.lane === 'lane_a' ? 'blue' : 'cyan'">{{ item.lane }}</a-tag>
            <span class="item-id mono">ID: {{ item.queueItemId }}</span>
          </a-space>

          <!-- AI 预审初筛 Badge -->
          <div class="ai-verdict-badge">
            <span class="ai-label">第三方 AI 初筛判定:</span>
            <a-tag :color="getVerdictColor(item.autoVerdict)">
              {{ getVerdictLabel(item.autoVerdict) }}
            </a-tag>
          </div>
        </div>

        <div class="item-content-grid">
          <!-- 左侧：命题与双模型主张 -->
          <div class="claim-block">
            <div class="prop-title">
              <span class="badge-idx">命题</span>
              <span class="prop-text">{{ item.proposition }}</span>
            </div>

            <!-- 双路对比 (Lane A vs Lane B) -->
            <div class="lanes-box">
              <div class="lane-col">
                <span class="lane-title">Lane A 抽取：</span>
                <span class="lane-val">{{ item.modelSuggestionA || '无提取建议' }}</span>
              </div>
              <div class="lane-col">
                <span class="lane-title">Lane B 抽取：</span>
                <span class="lane-val">{{ item.modelSuggestionB || '无提取建议' }}</span>
              </div>
            </div>

            <!-- AI 预审初筛理由 -->
            <div class="ai-rationale">
              <span class="reason-title">AI 初审理由：</span>
              <span>{{ item.autoRationale }}</span>
            </div>
          </div>

          <!-- 中间：原文证据引文 (Evidence Quotes) -->
          <div class="evidence-block">
            <div class="evidence-title">
              <FileTextOutlined /> 原文支持引文证据 (Seven-tier Span)
            </div>
            <div
              v-for="(quote, qIdx) in item.evidenceQuotes"
              :key="qIdx"
              class="quote-snippet"
            >
              “{{ quote }}”
            </div>
          </div>

          <!-- 右侧：人工复核决策控制区 -->
          <div class="decision-block">
            <div class="decision-status">
              <span class="dec-label">人工裁决结果:</span>
              <a-tag v-if="item.humanVerdict" :color="getVerdictColor(item.humanVerdict)">
                {{ getVerdictLabel(item.humanVerdict) }}
              </a-tag>
              <a-tag v-else color="default">待人工复核</a-tag>
            </div>

            <div class="action-buttons">
              <a-button
                type="primary"
                size="small"
                :ghost="item.humanVerdict !== 'VERDICT_ACCEPT'"
                @click="setVerdict(item, 'VERDICT_ACCEPT')"
              >
                采纳
              </a-button>

              <a-button
                size="small"
                :type="item.humanVerdict === 'VERDICT_MODIFY' ? 'primary' : 'default'"
                @click="openModifyModal(item)"
              >
                修改
              </a-button>

              <a-button
                size="small"
                danger
                :ghost="item.humanVerdict !== 'VERDICT_REJECT'"
                @click="setVerdict(item, 'VERDICT_REJECT')"
              >
                驳回
              </a-button>

              <a-button
                size="small"
                :type="item.humanVerdict === 'VERDICT_REQUEST_EVIDENCE' ? 'primary' : 'default'"
                @click="setVerdict(item, 'VERDICT_REQUEST_EVIDENCE')"
              >
                补证
              </a-button>
            </div>

            <div v-if="item.modifiedContent" class="modified-tip">
              已修订为：{{ item.modifiedContent }}
            </div>
          </div>
        </div>
      </a-card>
    </div>

    <!-- 人工修改命题弹窗 -->
    <a-modal
      v-model:open="modifyModalOpen"
      title="人工微调修改提取命题"
      @ok="handleSaveModify"
      @cancel="modifyModalOpen = false"
      ok-text="确认修改"
      cancel-text="取消"
    >
      <a-form layout="vertical">
        <a-form-item label="原始命题">
          <div class="mono-quote">{{ activeModifyingItem?.proposition }}</div>
        </a-form-item>
        <a-form-item label="修正常规化命题文本 (Modified Proposition)">
          <a-textarea
            v-model:value="modifyInputText"
            :rows="4"
            placeholder="输入修正后的命题陈述..."
          />
        </a-form-item>
        <a-form-item label="修改裁决理由 (Rationale)">
          <a-input
            v-model:value="modifyReasonText"
            placeholder="例如：剔除过度推断，保留原书字面因果"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SendOutlined,
  FileTextOutlined,
} from '@ant-design/icons-vue';
import type { ReviewQueueItemData, VerdictType } from '../types';
import { getReviewQueue, submitReviewBatch } from '../api';
import { usePipelineStore } from '../stores/pipeline';

const pipelineStore = usePipelineStore();

const queueItems = ref<ReviewQueueItemData[]>([]);
const filterTab = ref<'all' | 'divergent' | 'ai_pass' | 'decided'>('divergent');
const searchKeyword = ref<string>('');
const submitting = ref<boolean>(false);

const modifyModalOpen = ref<boolean>(false);
const activeModifyingItem = ref<ReviewQueueItemData | null>(null);
const modifyInputText = ref<string>('');
const modifyReasonText = ref<string>('');

onMounted(async () => {
  await loadQueue();
});

async function loadQueue() {
  try {
    const items = await getReviewQueue(pipelineStore.currentRunId);
    queueItems.value = items;
  } catch (err) {
    console.error(err);
  }
}

const autoAcceptCount = computed(
  () => queueItems.value.filter((it) => it.autoVerdict === 'VERDICT_ACCEPT').length
);

const humanRequiredCount = computed(
  () => queueItems.value.filter((it) => it.autoVerdict !== 'VERDICT_ACCEPT').length
);

const decidedCount = computed(
  () => queueItems.value.filter((it) => it.humanVerdict !== undefined).length
);

const filteredList = computed(() => {
  let list = queueItems.value;

  if (filterTab.value === 'divergent') {
    list = list.filter((it) => it.autoVerdict !== 'VERDICT_ACCEPT');
  } else if (filterTab.value === 'ai_pass') {
    list = list.filter((it) => it.autoVerdict === 'VERDICT_ACCEPT');
  } else if (filterTab.value === 'decided') {
    list = list.filter((it) => it.humanVerdict !== undefined);
  }

  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase();
    list = list.filter(
      (it) =>
        it.proposition.toLowerCase().includes(kw) ||
        it.evidenceQuotes.some((q) => q.toLowerCase().includes(kw))
    );
  }

  return list;
});

function getVerdictColor(verdict?: VerdictType): string {
  switch (verdict) {
    case 'VERDICT_ACCEPT':
      return 'green';
    case 'VERDICT_MODIFY':
      return 'blue';
    case 'VERDICT_REJECT':
      return 'red';
    case 'VERDICT_REQUEST_EVIDENCE':
      return 'orange';
    default:
      return 'default';
  }
}

function getVerdictLabel(verdict?: VerdictType): string {
  switch (verdict) {
    case 'VERDICT_ACCEPT':
      return '采纳 (Accept)';
    case 'VERDICT_MODIFY':
      return '修改 (Modify)';
    case 'VERDICT_REJECT':
      return '驳回 (Reject)';
    case 'VERDICT_REQUEST_EVIDENCE':
      return '补证 (Evidence)';
    default:
      return '待裁决';
  }
}

function setVerdict(item: ReviewQueueItemData, verdict: VerdictType) {
  item.humanVerdict = verdict;
  item.status = 'decided';
  message.success(`条目 [${item.queueItemId}] 已裁决为: ${getVerdictLabel(verdict)}`);
}

function openModifyModal(item: ReviewQueueItemData) {
  activeModifyingItem.value = item;
  modifyInputText.value = item.modifiedContent || item.proposition;
  modifyReasonText.value = item.humanRationale || '校正主张陈述口径';
  modifyModalOpen.value = true;
}

function handleSaveModify() {
  if (!activeModifyingItem.value) return;
  activeModifyingItem.value.modifiedContent = modifyInputText.value;
  activeModifyingItem.value.humanRationale = modifyReasonText.value;
  activeModifyingItem.value.humanVerdict = 'VERDICT_MODIFY';
  activeModifyingItem.value.status = 'decided';
  modifyModalOpen.value = false;
  message.success('已登记修改建议并标记为【修改】通过');
}

function handleBatchAcceptAI() {
  let count = 0;
  queueItems.value.forEach((item) => {
    if (!item.humanVerdict && item.autoVerdict === 'VERDICT_ACCEPT') {
      item.humanVerdict = 'VERDICT_ACCEPT';
      item.status = 'decided';
      count++;
    }
  });
  message.success(`已批量采纳 ${count} 个第三方 AI 预审通过项`);
}

async function handleSubmitBatch() {
  submitting.value = true;
  try {
    const decisions = queueItems.value
      .filter((it) => it.humanVerdict !== undefined)
      .map((it) => ({
        queueItemId: it.queueItemId,
        verdict: it.humanVerdict!,
        rationale: it.humanRationale || it.autoRationale,
        modifiedContent: it.modifiedContent,
      }));

    if (decisions.length === 0) {
      message.warning('请至少对一个命题条目进行裁决后再提交');
      return;
    }

    await submitReviewBatch({
      runId: pipelineStore.currentRunId,
      decisions,
    });

    message.success(`已成功提交 ${decisions.length} 项人工复核裁决，流水线放行进入 M7`);
    pipelineStore.updateStageStatus(
      'PIPELINE_STAGE_M6_REVIEW',
      'RUN_STATUS_SUCCEEDED',
      `人工复核决策全部签发完毕（采纳 ${decisions.length} 项）`
    );
    pipelineStore.setStageIndex(6); // 跳转 M7
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.review-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 190px);
  background: #f0f2f5;
}

.review-header-card {
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.sub-hint {
  font-size: 12px;
  color: #888;
}

.filter-bar {
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
}

.review-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.review-item-card {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  border-radius: 6px;
  transition: all 0.2s;
}

.review-item-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 8px;
  margin-bottom: 10px;
}

.item-id {
  font-size: 12px;
  color: #999;
}

.ai-verdict-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ai-label {
  font-size: 12px;
  color: #666;
}

.item-content-grid {
  display: grid;
  grid-template-columns: 2fr 1.6fr 1.2fr;
  gap: 16px;
}

.claim-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prop-title {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.badge-idx {
  background: #1677ff;
  color: #fff;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.prop-text {
  font-size: 14px;
  font-weight: 600;
  color: #1f1f1f;
  line-height: 1.5;
}

.lanes-box {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 8px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lane-title {
  color: #666;
  font-weight: 500;
}

.lane-val {
  color: #333;
}

.ai-rationale {
  font-size: 12px;
  color: #555;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  padding: 6px 8px;
  border-radius: 4px;
}

.reason-title {
  font-weight: 600;
  color: #389e0d;
}

.evidence-block {
  background: #fcfcfc;
  border-left: 3px solid #1677ff;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.evidence-title {
  font-size: 12px;
  font-weight: 600;
  color: #1677ff;
  display: flex;
  align-items: center;
  gap: 4px;
}

.quote-snippet {
  font-family: 'PingFang SC', serif;
  font-size: 13px;
  color: #434343;
  line-height: 1.6;
  background: #fff;
  padding: 6px 8px;
  border-radius: 4px;
  border: 1px solid #e8e8e8;
}

.decision-block {
  border-left: 1px solid #f0f0f0;
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.decision-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin-bottom: 12px;
}

.dec-label {
  color: #666;
}

.action-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.modified-tip {
  font-size: 11px;
  color: #1677ff;
  background: #e6f4ff;
  padding: 4px 6px;
  border-radius: 4px;
  margin-top: 8px;
}

.mono {
  font-family: monospace;
}

.mono-quote {
  font-family: monospace;
  background: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
}
</style>
