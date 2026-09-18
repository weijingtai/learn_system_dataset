<template>
  <a-drawer
    v-model:open="visible"
    title="流水线 WebSocket 实时执行日志总线"
    placement="bottom"
    height="360"
    :body-style="{ padding: '8px 16px', background: '#141414' }"
  >
    <template #extra>
      <a-space size="small">
        <a-radio-group v-model:value="filterLevel" size="small" button-style="solid">
          <a-radio-button value="all">全部 ({{ logs.length }})</a-radio-button>
          <a-radio-button value="info">INFO</a-radio-button>
          <a-radio-button value="warn">WARN</a-radio-button>
          <a-radio-button value="error">ERROR</a-radio-button>
        </a-radio-group>

        <a-button size="small" @click="clearLogs">清屏</a-button>
        <a-button size="small" type="primary" ghost @click="copyAllLogs">导出日志</a-button>
      </a-space>
    </template>

    <!-- 日志终端控制台内容 -->
    <div class="terminal-box" ref="terminalRef">
      <div v-if="filteredLogs.length === 0" class="empty-terminal">
        > 等待流水线事件推送中...
      </div>
      <div
        v-for="log in filteredLogs"
        :key="log.id"
        :class="['log-line', `lvl-${log.level}`]"
      >
        <span class="log-time">[{{ formatTime(log.timestamp) }}]</span>
        <span class="log-tag" v-if="log.stage">{{ log.stage }}</span>
        <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
        <span class="log-msg">{{ log.message }}</span>
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import { message } from 'ant-design-vue';
import { usePipelineStore } from '../stores/pipeline';
import type { PipelineLogEntry } from '../types';

const visible = defineModel<boolean>('open', { default: false });

const pipelineStore = usePipelineStore();
const filterLevel = ref<string>('all');
const terminalRef = ref<HTMLElement | null>(null);

const logs = computed(() => pipelineStore.logs);

const filteredLogs = computed(() => {
  if (filterLevel.value === 'all') return logs.value;
  return logs.value.filter((l: PipelineLogEntry) => l.level === filterLevel.value);
});

watch(
  () => logs.value.length,
  () => {
    nextTick(() => {
      if (terminalRef.value) {
        terminalRef.value.scrollTop = 0; // 最新在上
      }
    });
  }
);

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toTimeString().slice(0, 8) + '.' + String(d.getMilliseconds()).padStart(3, '0');
}

function clearLogs() {
  pipelineStore.clearLogs();
  message.info('控制台日志已清屏');
}

function copyAllLogs() {
  const text = logs.value
    .map(
      (l: PipelineLogEntry) =>
        `[${formatTime(l.timestamp)}] [${l.level.toUpperCase()}] ${l.stage ? `[${l.stage}] ` : ''}${l.message}`
    )
    .join('\n');
  navigator.clipboard.writeText(text);
  message.success('已将全量日志复制到剪贴板');
}
</script>

<style scoped>
.terminal-box {
  height: 100%;
  overflow-y: auto;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.empty-terminal {
  color: #666;
  padding: 16px;
}

.log-line {
  display: flex;
  gap: 8px;
  padding: 2px 4px;
  border-radius: 2px;
  word-break: break-all;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.log-time {
  color: #707070;
  white-space: nowrap;
}

.log-tag {
  color: #1890ff;
  font-weight: 500;
  white-space: nowrap;
}

.log-level {
  white-space: nowrap;
  font-weight: 600;
}

.lvl-info .log-level {
  color: #52c41a;
}
.lvl-info .log-msg {
  color: #e6e6e6;
}

.lvl-warn .log-level {
  color: #faad14;
}
.lvl-warn .log-msg {
  color: #ffe58f;
}

.lvl-error .log-level {
  color: #ff4d4f;
}
.lvl-error .log-msg {
  color: #ffccc7;
}

.lvl-success .log-level {
  color: #13c2c2;
}
.lvl-success .log-msg {
  color: #87e8de;
}
</style>
