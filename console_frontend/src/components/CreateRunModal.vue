<template>
  <a-modal
    v-model:open="visible"
    title="新建古籍知识编译任务 (New Pipeline Run)"
    :confirm-loading="submitting"
    ok-text="启动流水线"
    cancel-text="取消"
    width="580"
    @ok="handleCreateRun"
  >
    <a-form layout="vertical" :model="formState">
      <a-row :gutter="16">
        <a-col :span="14">
          <a-form-item label="古籍文献书名 (Work)" required>
            <a-input v-model:value="formState.work" placeholder="例如：新刻张果星宗、子平真诠" />
          </a-form-item>
        </a-col>
        <a-col :span="10">
          <a-form-item label="版本底本 (Edition)" required>
            <a-input v-model:value="formState.edition" placeholder="例如：四库全书本、清刻本" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="底本文件输入形式 (File Type)">
            <a-select v-model:value="formState.fileType">
              <a-select-option value="txt">纯电子文本 (TXT / Markdown)</a-select-option>
              <a-select-option value="pdf">古籍扫描件 (PDF / 影像)</a-select-option>
              <a-select-option value="epub">电子出版物 (EPUB)</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="术数流派档案 (Technique Profile)">
            <a-select v-model:value="formState.techniqueId">
              <a-select-option value="technique_qizheng">七政四余 (星宗天官学)</a-select-option>
              <a-select-option value="technique_ziping">子平八字 (十神格局学)</a-select-option>
              <a-select-option value="technique_qimen">奇门遁甲 (三奇六仪)</a-select-option>
              <a-select-option value="technique_liuren">大六壬 (月将课传)</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item label="Prompt 资产档案 (解除固定 SHA-256 解耦 Profile)">
        <a-select v-model:value="formState.promptProfileId">
          <a-select-option value="profile_v1.0">v1.0 标准语义分词与双路命题抽取档案</a-select-option>
          <a-select-option value="profile_v2.0_cot">v2.0 思维链（CoT）深度因果证据链增强档案</a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="运行模式策略">
        <a-radio-group v-model:value="formState.runMode" button-style="solid">
          <a-radio-button value="human_loop">人机协同复核模式 (推荐，精准度 99.8%)</a-radio-button>
          <a-radio-button value="auto_pilot">AI 全自动代审快穿模式 (10分钟出包)</a-radio-button>
        </a-radio-group>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { message } from 'ant-design-vue';
import { usePipelineStore } from '../stores/pipeline';

const visible = defineModel<boolean>('open', { default: false });
const pipelineStore = usePipelineStore();
const submitting = ref<boolean>(false);

const formState = reactive({
  work: '新刻张果星宗',
  edition: '四库全书本',
  fileType: 'txt',
  techniqueId: 'technique_qizheng',
  promptProfileId: 'profile_v1.0',
  runMode: 'human_loop',
});

async function handleCreateRun() {
  if (!formState.work.trim() || !formState.edition.trim()) {
    message.error('请输入古籍文献名与版本底本名称');
    return;
  }

  submitting.value = true;
  try {
    const runId = `run_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    await pipelineStore.createRun({
      work: formState.work,
      edition: formState.edition,
      fileType: formState.fileType,
      techniqueId: formState.techniqueId,
      promptProfileId: formState.promptProfileId,
      runId,
    });
    message.success('流水线任务已创建并启动执行！');
    visible.value = false;
  } catch (err: any) {
    message.error(`创建失败: ${err.message || err}`);
  } finally {
    submitting.value = false;
  }
}
</script>
