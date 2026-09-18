<template>
  <div class="generic-stage-container">
    <!-- M3 分词边界与断句视图 -->
    <template v-if="stageIndex === 2">
      <div class="stage-body">
        <a-card :bordered="false" title="M3 句读断句与语义窗口分块工作台" class="mb-3">
          <template #extra>
            <a-space>
              <a-tag color="blue">分块算法：Double-Window Sliding (300字)</a-tag>
              <a-tag color="green">金标分词对账：PASS (0.992)</a-tag>
            </a-space>
          </template>

          <a-row :gutter="16">
            <a-col :span="12">
              <a-card size="small" title="【模型 A】传统句读标点分词">
                <div class="text-passage">
                  夫星学者，始于古之羲和。历代圣贤，推测乾坤之妙用也。日行一度，月行十三度有奇。
                  晨昏有分，阴阳有定位。若逢吉星拱照，则灾消福凑；遇凶曜临躔，则祸变立至。
                  乾曜旋转，日月星辰，莫不依循天道。
                </div>
              </a-card>
            </a-col>
            <a-col :span="12">
              <a-card size="small" title="【模型 B】语义连贯断句分词">
                <div class="text-passage">
                  夫星学者，始于古之羲和，历代圣贤推测乾坤之妙用也。日行一度，月行十三度有奇。
                  晨昏有分，阴阳有定位。若逢吉星拱照，则灾消福凑；遇凶曜临躔，则祸变立至。
                  乾曜旋转，日月星辰莫不依循天道。
                </div>
              </a-card>
            </a-col>
          </a-row>

          <a-divider style="margin: 16px 0" />

          <a-table
            :columns="m3Columns"
            :data-source="m3Data"
            size="small"
            :pagination="false"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <a-tag color="success">{{ record.status }}</a-tag>
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
    </template>

    <!-- M5 自动门禁校验仪表盘 -->
    <template v-else-if="stageIndex === 4">
      <div class="stage-body">
        <a-card :bordered="false" title="M5 自动质量门禁与因果闭包校验 (Stage Gates)" class="mb-3">
          <template #extra>
            <a-tag color="success">Gate 总检判决：All Succeeded (Exit 0)</a-tag>
          </template>

          <a-row :gutter="16">
            <a-col :span="6">
              <a-card size="small" class="gate-card">
                <div class="gate-status pass"><CheckCircleFilled /> PASS</div>
                <div class="gate-name">G1 来源与可重放性门禁</div>
                <div class="gate-desc">原书 SHA-256 指纹与 Prompt 档案自洽</div>
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card size="small" class="gate-card">
                <div class="gate-status pass"><CheckCircleFilled /> PASS</div>
                <div class="gate-name">G2 全书字框全量覆盖</div>
                <div class="gate-desc">无悬空孤立字符，字位偏移无缝衔接</div>
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card size="small" class="gate-card">
                <div class="gate-status pass"><CheckCircleFilled /> PASS</div>
                <div class="gate-name">G3 身份与证据锚点对账</div>
                <div class="gate-desc">pat_/ent_ 复合键闭集验证通过</div>
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card size="small" class="gate-card">
                <div class="gate-status pass"><CheckCircleFilled /> PASS</div>
                <div class="gate-name">G5 因果闭包推演门禁</div>
                <div class="gate-desc">图谱无矛盾因果回环，断语全称性校验通过</div>
              </a-card>
            </a-col>
          </a-row>

          <a-divider style="margin: 16px 0" />

          <a-descriptions title="自动化门禁对账明细" bordered size="small" :column="2">
            <a-descriptions-item label="待验实体候选数">148 项 (100% 合法前缀)</a-descriptions-item>
            <a-descriptions-item label="推演规则命题数">42 条 (因果闭包无矛盾)</a-descriptions-item>
            <a-descriptions-item label="引文证据七段哈希">通过对账，绝对位移无截断</a-descriptions-item>
            <a-descriptions-item label="运行阶段用时">1.82 秒 (纯函数 Red-Green 校验)</a-descriptions-item>
          </a-descriptions>
        </a-card>
      </div>
    </template>

    <!-- M7 创世汇编与版本快照 -->
    <template v-else-if="stageIndex === 6">
      <div class="stage-body">
        <a-card :bordered="false" title="M7 创世汇编与不可变快照浏览器 (Genesis Assembly)" class="mb-3">
          <template #extra>
            <a-tag color="blue">Snapshot ID: snap_20260918_v1</a-tag>
          </template>

          <a-alert
            message="不可变快照封存"
            description="M7 创世汇编器已将人工审核采纳的 ReviewedEditionPackage 封装为确定性不可变版本快照，准备进入 M8 发布。"
            type="success"
            show-icon
            style="margin-bottom: 16px"
          />

          <a-descriptions bordered size="small" :column="2">
            <a-descriptions-item label="底本文献 (Work)">新刻张果星宗 (四库全书本)</a-descriptions-item>
            <a-descriptions-item label="快照封存哈希">sha256:7f83b1657ff1fc53b92dc181...</a-descriptions-item>
            <a-descriptions-item label="入库规范节点">190 个图谱节点 (Node)</a-descriptions-item>
            <a-descriptions-item label="语义关系连边">312 条关系有向边 (Edge)</a-descriptions-item>
          </a-descriptions>
        </a-card>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  stageIndex: number;
}>();

const m3Columns = [
  { title: '语义切块 ID', dataIndex: 'id', key: 'id' },
  { title: '切块字数', dataIndex: 'len', key: 'len' },
  { title: '跨度范围', dataIndex: 'span', key: 'span' },
  { title: '句读一致性', dataIndex: 'consistency', key: 'consistency' },
  { title: '门禁状态', dataIndex: 'status', key: 'status' },
];

const m3Data = [
  { id: 'chunk_001', len: 152, span: '[0 : 152]', consistency: '98.5%', status: 'PASS' },
  { id: 'chunk_002', len: 148, span: '[152 : 300]', consistency: '99.1%', status: 'PASS' },
  { id: 'chunk_003', len: 160, span: '[300 : 460]', consistency: '97.8%', status: 'PASS' },
];
</script>

<style scoped>
.generic-stage-container {
  padding: 16px;
  background: #f0f2f5;
  height: calc(100vh - 190px);
  overflow-y: auto;
}

.stage-body {
  max-width: 1200px;
  margin: 0 auto;
}

.text-passage {
  font-family: serif;
  font-size: 15px;
  line-height: 2;
  color: #262626;
  background: #fafafa;
  padding: 12px;
  border-radius: 4px;
}

.gate-card {
  text-align: center;
  padding: 12px;
}

.gate-status.pass {
  font-size: 18px;
  font-weight: 700;
  color: #52c41a;
  margin-bottom: 6px;
}

.gate-name {
  font-weight: 600;
  color: #1f1f1f;
  margin-bottom: 4px;
}

.gate-desc {
  font-size: 12px;
  color: #8c8c8c;
}
</style>
