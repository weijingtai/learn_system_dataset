<template>
  <a-config-provider
    :theme="{
      token: {
        colorPrimary: '#1677ff',
        borderRadius: 4,
        fontFamily: '-apple-system, BlinkMacSystemFont, PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif',
      },
    }"
  >
    <a-layout class="app-layout">
      <!-- 顶部 Header 导航栏 -->
      <a-layout-header class="app-header">
        <div class="header-left">
          <div class="app-logo">
            <BookOutlined class="logo-icon" />
            <span class="logo-title">Learn System</span>
            <span class="logo-sub">古籍知识编译与协同控制台</span>
          </div>
        </div>

        <div class="header-right">
          <a-space size="middle">
            <!-- 运行任务选择器 -->
            <div class="run-selector-box">
              <span class="sel-label">当前任务:</span>
              <a-select
                v-model:value="pipelineStore.currentRunId"
                placeholder="选择或切换任务"
                style="width: 240px"
                size="small"
                @change="handleSelectRun"
              >
                <a-select-option
                  v-for="r in pipelineStore.runsList"
                  :key="r.runId"
                  :value="r.runId"
                >
                  {{ r.work }} ({{ r.edition || r.runId }})
                </a-select-option>
              </a-select>
            </div>

            <!-- 新建流水线按钮 -->
            <a-button type="primary" size="small" @click="createRunModalOpen = true">
              <template #icon><PlusOutlined /></template>
              新建任务
            </a-button>

            <a-divider type="vertical" />

            <!-- WebSocket 连接状态 Badge -->
            <a-tooltip :title="pipelineStore.wsConnected ? '实时 WebSocket 总线已连接' : 'WebSocket 连接中/离线'">
              <a-badge
                :status="pipelineStore.wsConnected ? 'success' : 'error'"
                :text="pipelineStore.wsConnected ? '实时总线在线' : '总线离线'"
                class="ws-badge"
              />
            </a-tooltip>

            <a-divider type="vertical" />

            <!-- 日志抽屉快捷触发器 -->
            <a-badge :count="pipelineStore.logs.length" :overflow-count="99">
              <a-button size="small" @click="logDrawerOpen = !logDrawerOpen">
                <template #icon><CodeOutlined /></template>
                控制台日志
              </a-button>
            </a-badge>
          </a-space>
        </div>
      </a-layout-header>

      <!-- 顶部 8 阶段动态步骤条 Steps -->
      <div class="stepper-bar">
        <a-steps
          :current="pipelineStore.currentStageIndex"
          size="small"
          type="navigation"
          class="pipeline-steps"
          @change="onStepChange"
        >
          <a-step
            v-for="st in pipelineStore.stagesStatus"
            :key="st.index"
            :title="st.label"
            :sub-title="getStageStatusText(st.status)"
            :status="mapRunStatusToStepStatus(st.status)"
            :description="st.desc"
          >
            <template #icon>
              <template v-if="mapRunStatusToStepStatus(st.status) === 'process'">
                <LoadingOutlined />
              </template>
              <template v-else-if="mapRunStatusToStepStatus(st.status) === 'finish'">
                <CheckCircleFilled style="color: #52c41a" />
              </template>
              <template v-else-if="mapRunStatusToStepStatus(st.status) === 'error'">
                <CloseCircleFilled style="color: #ff4d4f" />
              </template>
              <template v-else-if="mapRunStatusToStepStatus(st.status) === 'wait'">
                <span class="step-num">{{ st.index + 1 }}</span>
              </template>
            </template>
          </a-step>
        </a-steps>
      </div>

      <!-- 中间主工作台内容区 -->
      <a-layout-content class="app-content">
        <!-- 阶段 0: M1 图像转写与 OCR 字框 -->
        <M1OcrWorkbench v-if="pipelineStore.currentStageIndex === 0" />

        <!-- 阶段 1: M2 文本清洗与十三项规则 -->
        <M2SanitizationWorkbench v-else-if="pipelineStore.currentStageIndex === 1" />

        <!-- 阶段 2: M3 分词边界与语义窗口分块 -->
        <GenericStageWorkbench v-else-if="pipelineStore.currentStageIndex === 2" :stage-index="2" />

        <!-- 阶段 3: M4 实体抽取与双路对比 (Review) -->
        <ReviewWorkbench v-else-if="pipelineStore.currentStageIndex === 3" />

        <!-- 阶段 4: M5 关系与因果闭包自动门禁校验 -->
        <GenericStageWorkbench v-else-if="pipelineStore.currentStageIndex === 4" :stage-index="4" />

        <!-- 阶段 5: M6 命题提炼协同审核 (Review) -->
        <ReviewWorkbench v-else-if="pipelineStore.currentStageIndex === 5" />

        <!-- 阶段 6: M7 规则编译与创世快照 -->
        <GenericStageWorkbench v-else-if="pipelineStore.currentStageIndex === 6" :stage-index="6" />

        <!-- 阶段 7: M8 标准数据集发布与下游同步 -->
        <M8ReleaseExport v-else-if="pipelineStore.currentStageIndex === 7" />
      </a-layout-content>

      <!-- 底部状态栏 Footer -->
      <a-layout-footer class="app-footer">
        <div class="footer-left">
          <span>任务 ID: <strong>{{ pipelineStore.currentRunId || '未选择' }}</strong></span>
          <a-divider type="vertical" />
          <span>文献: <strong>{{ pipelineStore.currentRun?.work || '新刻张果星宗' }}</strong></span>
          <a-divider type="vertical" />
          <span>当前阶段: <a-tag color="blue">{{ pipelineStore.activeStage.label }}</a-tag></span>
        </div>
        <div class="footer-right">
          <span>Learn System Architecture v2.0 · Vue 3 + Ant Design Vue + md-editor-v3</span>
        </div>
      </a-layout-footer>

      <!-- 实时日志抽屉 -->
      <PipelineLogDrawer v-model:open="logDrawerOpen" />

      <!-- 新建任务弹窗 -->
      <CreateRunModal v-model:open="createRunModalOpen" />
    </a-layout>
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import {
  BookOutlined,
  PlusOutlined,
  CodeOutlined,
  LoadingOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
} from '@ant-design/icons-vue';
import { usePipelineStore } from './stores/pipeline';
import { wsClient } from './utils/ws';
import type { RunStatusEnum } from './types';

// Components
import M1OcrWorkbench from './components/M1OcrWorkbench.vue';
import M2SanitizationWorkbench from './components/M2SanitizationWorkbench.vue';
import ReviewWorkbench from './components/ReviewWorkbench.vue';
import M8ReleaseExport from './components/M8ReleaseExport.vue';
import GenericStageWorkbench from './components/GenericStageWorkbench.vue';
import PipelineLogDrawer from './components/PipelineLogDrawer.vue';
import CreateRunModal from './components/CreateRunModal.vue';

const pipelineStore = usePipelineStore();
const logDrawerOpen = ref<boolean>(false);
const createRunModalOpen = ref<boolean>(false);

onMounted(async () => {
  await pipelineStore.loadRuns();
  wsClient.connect();
});

function handleSelectRun(runId: string) {
  pipelineStore.selectRun(runId);
}

function onStepChange(idx: number) {
  pipelineStore.setStageIndex(idx);
}

function mapRunStatusToStepStatus(status: RunStatusEnum | number) {
  if (status === 'RUN_STATUS_SUCCEEDED' || status === 4) return 'finish';
  if (status === 'RUN_STATUS_RUNNING' || status === 2) return 'process';
  if (status === 'RUN_STATUS_FAILED' || status === 5) return 'error';
  return 'wait';
}

function getStageStatusText(status: RunStatusEnum | number) {
  if (status === 'RUN_STATUS_SUCCEEDED' || status === 4) return '已完成';
  if (status === 'RUN_STATUS_RUNNING' || status === 2) return '执行中';
  if (status === 'RUN_STATUS_FAILED' || status === 5) return '失败';
  if (status === 'RUN_STATUS_AWAITING_HUMAN' || status === 3) return '待人审';
  return '未开始';
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  height: 52px;
  line-height: 52px;
  padding: 0 20px;
  background: #001529;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 20;
}

.header-left {
  display: flex;
  align-items: center;
}

.app-logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-icon {
  font-size: 20px;
  color: #1677ff;
}

.logo-title {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
}

.logo-sub {
  font-size: 12px;
  color: #8c8c8c;
  margin-left: 6px;
}

.header-right {
  display: flex;
  align-items: center;
}

.run-selector-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sel-label {
  color: #d9d9d9;
  font-size: 12px;
}

.ws-badge {
  color: #fff;
  font-size: 12px;
}

.stepper-bar {
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  padding: 8px 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
}

.pipeline-steps :deep(.ant-steps-item-title) {
  font-weight: 600;
  font-size: 13px;
}

.pipeline-steps :deep(.ant-steps-item-description) {
  font-size: 11px;
}

.step-num {
  font-size: 12px;
  font-weight: bold;
}

.app-content {
  flex: 1;
  background: #f0f2f5;
  position: relative;
  overflow: hidden;
}

.app-footer {
  height: 38px;
  line-height: 38px;
  padding: 0 16px;
  background: #fafafa;
  border-top: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #666;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
