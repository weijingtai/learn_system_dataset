import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type {
  PipelineRun,
  PipelineRunRequest,
  PipelineLogEntry,
  PipelineStageEnum,
  RunStatusEnum,
  StageProgress,
} from '../types';
import { fetchPipelineRuns, createPipelineRun, getPipelineRun } from '../api';

export const STAGE_CONFIGS = [
  { index: 0, key: 'PIPELINE_STAGE_M1_DIGITIZATION', enumVal: 1, label: 'M1 图像转写', desc: '古籍扫描与 OCR 识别' },
  { index: 1, key: 'PIPELINE_STAGE_M2_SANITIZATION', enumVal: 2, label: 'M2 文本清洗', desc: '十三项规则脏数据清洗' },
  { index: 2, key: 'PIPELINE_STAGE_M3_STRUCTURAL', enumVal: 3, label: 'M3 分词边界', desc: '句读断句与语义分块' },
  { index: 3, key: 'PIPELINE_STAGE_M4_KNOWLEDGE', enumVal: 4, label: 'M4 实体抽取', desc: '双路（Lane A/B）知识提取' },
  { index: 4, key: 'PIPELINE_STAGE_M5_VALIDATION', enumVal: 5, label: 'M5 自动门禁', desc: '引文哈希与闭包对账' },
  { index: 5, key: 'PIPELINE_STAGE_M6_REVIEW', enumVal: 6, label: 'M6 协同审核', desc: 'AI 预审初筛与人工复核' },
  { index: 6, key: 'PIPELINE_STAGE_M7_ASSEMBLY', enumVal: 7, label: 'M7 规则编译', desc: '创世汇编与版本快照' },
  { index: 7, key: 'PIPELINE_STAGE_M8_DATASET', enumVal: 8, label: 'M8 数据发布', desc: 'Release Bundle 出包分发' },
] as const;

export const usePipelineStore = defineStore('pipeline', () => {
  const runsList = ref<PipelineRun[]>([]);
  const currentRunId = ref<string>('');
  const currentRun = ref<PipelineRun | null>(null);
  const currentStageIndex = ref<number>(0);
  const logs = ref<PipelineLogEntry[]>([]);
  const wsConnected = ref<boolean>(false);
  const loading = ref<boolean>(false);

  const activeStage = computed(() => STAGE_CONFIGS[currentStageIndex.value] || STAGE_CONFIGS[0]);

  // 获取 8 个阶段在当前 Run 中的真实状态映射
  const stagesStatus = computed(() => {
    return STAGE_CONFIGS.map((cfg) => {
      const match = currentRun.value?.stages?.find((s) => {
        if (typeof s.stage === 'string') {
          return s.stage === cfg.key;
        }
        return s.stage === cfg.enumVal;
      });

      return {
        ...cfg,
        status: match?.status ?? 'RUN_STATUS_PENDING',
        summary: match?.summary || '',
        stepRunId: match?.stepRunId,
      };
    });
  });

  async function loadRuns() {
    loading.value = true;
    try {
      const runs = await fetchPipelineRuns();
      runsList.value = runs;
      if (runs.length > 0 && !currentRunId.value) {
        await selectRun(runs[0].runId);
      }
    } finally {
      loading.value = false;
    }
  }

  async function selectRun(runId: string) {
    currentRunId.value = runId;
    loading.value = true;
    try {
      const run = await getPipelineRun(runId);
      currentRun.value = run;
      // 同步选定当前阶段高亮
      syncCurrentStageIndex(run);
      appendLog({
        id: `log_${Date.now()}_sel`,
        timestamp: Date.now(),
        runId,
        level: 'info',
        message: `切换到任务 [${run.work || runId}]，当前阶段：${activeStage.value.label}`,
      });
    } finally {
      loading.value = false;
    }
  }

  function syncCurrentStageIndex(run: PipelineRun) {
    const cur = run.currentStage;
    const found = STAGE_CONFIGS.find((c) => c.key === cur || c.enumVal === cur);
    if (found) {
      currentStageIndex.value = found.index;
    }
  }

  async function createRun(req: PipelineRunRequest) {
    loading.value = true;
    try {
      const newRun = await createPipelineRun(req);
      runsList.value = [newRun, ...runsList.value.filter((r) => r.runId !== newRun.runId)];
      await selectRun(newRun.runId);
      appendLog({
        id: `log_${Date.now()}_new`,
        timestamp: Date.now(),
        runId: newRun.runId,
        level: 'success',
        message: `成功创建流水线任务: ${newRun.work} (${newRun.edition})`,
      });
      return newRun;
    } finally {
      loading.value = false;
    }
  }

  function setStageIndex(idx: number) {
    if (idx >= 0 && idx < STAGE_CONFIGS.length) {
      currentStageIndex.value = idx;
    }
  }

  function updateStageStatus(
    stage: PipelineStageEnum | number,
    status: RunStatusEnum | number,
    logMessage?: string
  ) {
    if (!currentRun.value) return;

    const targetCfg = STAGE_CONFIGS.find((c) => c.key === stage || c.enumVal === stage);
    if (!targetCfg) return;

    const existingStage = currentRun.value.stages.find(
      (s) => s.stage === stage || s.stage === targetCfg.key || s.stage === targetCfg.enumVal
    );

    if (existingStage) {
      existingStage.status = status;
      if (logMessage) existingStage.summary = logMessage;
    } else {
      currentRun.value.stages.push({
        stage: targetCfg.key,
        status,
        summary: logMessage,
      });
    }

    currentRun.value.currentStage = targetCfg.key;
    currentStageIndex.value = targetCfg.index;

    if (logMessage) {
      appendLog({
        id: `log_${Date.now()}_ws`,
        timestamp: Date.now(),
        runId: currentRun.value.runId,
        stage: targetCfg.label,
        level: status === 'RUN_STATUS_FAILED' || status === 5 ? 'error' : 'info',
        message: logMessage,
      });
    }
  }

  function appendLog(entry: PipelineLogEntry) {
    logs.value.unshift(entry);
    // 保持最多 300 条
    if (logs.value.length > 300) {
      logs.value.pop();
    }
  }

  function clearLogs() {
    logs.value = [];
  }

  function setWsConnected(val: boolean) {
    wsConnected.value = val;
  }

  return {
    runsList,
    currentRunId,
    currentRun,
    currentStageIndex,
    activeStage,
    stagesStatus,
    logs,
    wsConnected,
    loading,
    loadRuns,
    selectRun,
    createRun,
    setStageIndex,
    updateStageStatus,
    appendLog,
    clearLogs,
    setWsConnected,
  };
});
