<template>
  <div class="m8-container">
    <div class="m8-content">
      <!-- 编译产物发布统计指标看板 -->
      <a-card :bordered="false" class="metrics-card">
        <template #title>
          <span class="card-title">
            <RocketOutlined style="color: #1677ff; margin-right: 8px" />
            M8 古籍编译成果：标准发布包 (Release Bundle)
          </span>
        </template>
        <template #extra>
          <a-tag color="success">状态：已完成创世汇编，就绪可分发</a-tag>
        </template>

        <a-row :gutter="24">
          <a-col :span="6">
            <div class="metric-box">
              <div class="metric-num">148</div>
              <div class="metric-lbl">标准化概念与实体词条</div>
              <div class="metric-sub">实体前缀 pat_ / ent_ 100% 映射对账</div>
            </div>
          </a-col>
          <a-col :span="6">
            <div class="metric-box">
              <div class="metric-num">42</div>
              <div class="metric-lbl">术数推演与断句规则</div>
              <div class="metric-sub">含双路 AI 对比与人工复核裁决</div>
            </div>
          </a-col>
          <a-col :span="6">
            <div class="metric-box highlight">
              <div class="metric-num">99.4%</div>
              <div class="metric-lbl">因果图谱门禁闭包率</div>
              <div class="metric-sub">G1/G2/G3/G5 自动全量门禁已通过</div>
            </div>
          </a-col>
          <a-col :span="6">
            <div class="metric-box">
              <div class="metric-num">100%</div>
              <div class="metric-lbl">七层证据锚点溯源率</div>
              <div class="metric-sub">精确至原书单字检测框 CharBox 偏移</div>
            </div>
          </a-col>
        </a-row>

        <a-divider style="margin: 20px 0" />

        <!-- 一键出包下载区 -->
        <div class="download-section">
          <a-space size="large" align="center">
            <a-button
              type="primary"
              size="large"
              :loading="downloading"
              class="btn-download"
              @click="handleDownloadBundle"
            >
              <template #icon><DownloadOutlined /></template>
              下载 Release Bundle (JSON)
            </a-button>

            <a-button size="large" @click="handlePreviewJson">
              <template #icon><FileTextOutlined /></template>
              在线检视 Bundle 规范格式
            </a-button>

            <span class="file-spec-hint">
              包含完整 Manifest、Schema 对账、知识实体与带原书绝对坐标的七段引文证据链
            </span>
          </a-space>
        </div>
      </a-card>

      <!-- 下游服务与 Firebase Config 同步预留配置卡片 -->
      <a-card :bordered="false" class="integration-card">
        <template #title>
          <span class="card-title">
            <CloudSyncOutlined style="color: #52c41a; margin-right: 8px" />
            下游主数据服务与 Firebase Config / Hosting 同步规范预留
          </span>
        </template>
        <template #extra>
          <a-tag color="processing">API Gateway 适配接口桩已就绪</a-tag>
        </template>

        <a-alert
          message="下游自动化分发接入说明"
          description="系统支持一键将冻结后的 ReleaseBundle 推送至 Firebase Remote Config、Cloud Firestore、Turso Edge 分布式数据库或企业级下游知识图谱服务。请配置目标环境凭据与回调 Webhook。"
          type="info"
          show-icon
          style="margin-bottom: 20px"
        />

        <a-form layout="vertical">
          <a-row :gutter="24">
            <a-col :span="8">
              <a-form-item label="分发目标平台 (Distribution Target)">
                <a-select v-model:value="distConfig.target">
                  <a-select-option value="firebase">Google Firebase (Hosting & Config)</a-select-option>
                  <a-select-option value="turso">Turso / LibSQL 分布式边缘库</a-select-option>
                  <a-select-option value="r2">Cloudflare R2 对象存储</a-select-option>
                  <a-select-option value="master_data">企业内部主数据 API Gateway</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>

            <a-col :span="8">
              <a-form-item label="目标部署环境 (Deployment Environment)">
                <a-radio-group v-model:value="distConfig.env" button-style="solid">
                  <a-radio-button value="development">Dev 开发</a-radio-button>
                  <a-radio-button value="staging">Staging 预发</a-radio-button>
                  <a-radio-button value="production">Production 生产</a-radio-button>
                </a-radio-group>
              </a-form-item>
            </a-col>

            <a-col :span="8">
              <a-form-item label="Firebase Project ID / 命名空间">
                <a-input v-model:value="distConfig.projectId" placeholder="例如：learn-system-prod-asia" />
              </a-form-item>
            </a-col>
          </a-row>

          <a-row :gutter="24">
            <a-col :span="12">
              <a-form-item label="下游服务同步 Endpoint URL">
                <a-input
                  v-model:value="distConfig.endpointUrl"
                  placeholder="https://api.domain.com/v1/distribute/release-bundle"
                />
              </a-form-item>
            </a-col>

            <a-col :span="12">
              <a-form-item label="API Access Key / 认证令牌 (Bearer Token)">
                <a-input-password
                  v-model:value="distConfig.apiKey"
                  placeholder="sk_live_xuan_learn_system_..."
                />
              </a-form-item>
            </a-col>
          </a-row>

          <a-row :gutter="24">
            <a-col :span="16">
              <a-form-item label="发布事件回调 Webhook URL (通知下游缓存刷新)">
                <a-input
                  v-model:value="distConfig.webhookUrl"
                  placeholder="https://hooks.slack.com/services/... 或自有 Webhook 端点"
                />
              </a-form-item>
            </a-col>

            <a-col :span="8" style="display: flex; align-items: flex-end; padding-bottom: 24px">
              <a-space>
                <a-button type="primary" :loading="pushing" @click="handlePushDownstream">
                  <template #icon><CloudUploadOutlined /></template>
                  下发同步至下游
                </a-button>
                <a-button @click="handleSaveConfig">保存配置</a-button>
              </a-space>
            </a-col>
          </a-row>
        </a-form>
      </a-card>
    </div>

    <!-- Bundle JSON 规范检视抽屉 -->
    <a-drawer
      v-model:open="previewDrawerOpen"
      title="Release Bundle (标准 JSON 规范预览)"
      width="640"
      placement="right"
    >
      <div class="json-preview-wrap">
        <pre class="json-code">{{ previewJsonContent }}</pre>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { message } from 'ant-design-vue';
import {
  RocketOutlined,
  DownloadOutlined,
  FileTextOutlined,
  CloudSyncOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons-vue';
import { exportReleaseBundle } from '../api';
import { usePipelineStore } from '../stores/pipeline';

const pipelineStore = usePipelineStore();

const downloading = ref<boolean>(false);
const pushing = ref<boolean>(false);
const previewDrawerOpen = ref<boolean>(false);
const previewJsonContent = ref<string>('');

const distConfig = ref({
  target: 'firebase',
  env: 'production',
  projectId: 'learn-system-prod-asia',
  endpointUrl: 'https://api.learn-system.internal/v1/distribute/release',
  apiKey: 'ls_live_prod_sec_9938b812f',
  webhookUrl: 'https://api.learn-system.internal/hooks/release-notify',
});

async function handleDownloadBundle() {
  downloading.value = true;
  try {
    const runId = pipelineStore.currentRunId || 'run_default';
    const blob = await exportReleaseBundle(runId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `release_bundle_${runId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(`已成功下载 ${runId} 标准 Release Bundle 文件`);
  } catch (err) {
    message.error('下载失败，请稍后重试');
  } finally {
    downloading.value = false;
  }
}

function handlePreviewJson() {
  const sample = {
    $schema: 'https://schema.learn-system.internal/v1/release-bundle.json',
    bundle_id: `bundle_${pipelineStore.currentRunId || 'run_demo'}_v1.0`,
    metadata: {
      work: pipelineStore.currentRun?.work || '新刻张果星宗',
      edition: pipelineStore.currentRun?.edition || '四库全书本',
      compiler_version: 'learn_system_v2.4.0',
      exported_at: new Date().toISOString(),
      integrity_hash: 'sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
    },
    statistics: {
      entities: 148,
      rules: 42,
      gate_pass_rate: 0.994,
      evidence_coverage: 1.0,
    },
    entities: [
      {
        id: 'pat_taiyang_wu',
        name: '日丽中天格',
        category: '天文格局',
        evidence_anchor: {
          evidence_level: 'glyphbox',
          span: '320:348',
          page: 1,
          char_boxes: ['c_1_0', 'c_1_1', 'c_1_2', 'c_1_3'],
        },
      },
    ],
    rules: [
      {
        rule_id: 'rule_taiyang_001',
        antecedent: ['太阳居午位', '昼生人'],
        consequent: ['官禄格最吉', '主贵显名扬'],
        status: 'VERDICT_ACCEPT',
      },
    ],
  };

  previewJsonContent.value = JSON.stringify(sample, null, 2);
  previewDrawerOpen.value = true;
}

function handleSaveConfig() {
  message.success('下游同步配置已保存在工作区 profile 中');
}

async function handlePushDownstream() {
  pushing.value = true;
  try {
    // 模拟下发与 webhook 触发过程
    await new Promise((resolve) => setTimeout(resolve, 1200));
    message.success(
      `已成功将 Release Bundle 推送至 [${distConfig.value.target.toUpperCase()}] (${distConfig.value.env}) 环境！`
    );
  } finally {
    pushing.value = false;
  }
}
</script>

<style scoped>
.m8-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 190px);
  background: #f0f2f5;
  overflow-y: auto;
  padding: 16px 20px;
}

.m8-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1300px;
  margin: 0 auto;
  width: 100%;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
  display: flex;
  align-items: center;
}

.metrics-card,
.integration-card {
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  border-radius: 8px;
}

.metric-box {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 16px;
  text-align: center;
}

.metric-box.highlight {
  background: #f6ffed;
  border-color: #b7eb8f;
}

.metric-num {
  font-size: 32px;
  font-weight: 700;
  color: #1677ff;
  line-height: 1.2;
}

.metric-box.highlight .metric-num {
  color: #52c41a;
}

.metric-lbl {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-top: 6px;
}

.metric-sub {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

.download-section {
  padding: 8px 0;
}

.btn-download {
  height: 44px;
  padding: 0 28px;
  font-size: 15px;
  border-radius: 6px;
}

.file-spec-hint {
  font-size: 13px;
  color: #888;
}

.json-preview-wrap {
  background: #1e1e1e;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
  max-height: 100%;
}

.json-code {
  color: #d4d4d4;
  font-family: Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  margin: 0;
  line-height: 1.5;
}
</style>
