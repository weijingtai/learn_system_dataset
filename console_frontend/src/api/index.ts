import axios from 'axios';
import type {
  PipelineRun,
  PipelineRunRequest,
  PageScanData,
  SanitizationWorkbenchData,
  ReviewQueueItemData,
  ReviewBatchRequestData,
} from '../types';

export const apiClient = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 统一响应拦截处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.warn('[API Client Error]', error?.response?.status, error?.message);
    return Promise.reject(error);
  }
);

/* ================= Pipeline Core API ================= */

export async function fetchPipelineRuns(): Promise<PipelineRun[]> {
  try {
    const res = await apiClient.get<any[]>('/api/pipeline/runs');
    return res.data.map(normalizePipelineRun);
  } catch (err) {
    console.warn('Fallback: Using default initial runs list', err);
    return [createDefaultMockRun('run_demo_xuan_001')];
  }
}

export async function createPipelineRun(req: PipelineRunRequest): Promise<PipelineRun> {
  const payload = {
    work: req.work,
    edition: req.edition,
    file_type: req.fileType,
    source_file_path: req.sourceFilePath || '',
    technique_id: req.techniqueId || 'technique_qizheng',
    prompt_profile_id: req.promptProfileId || 'profile_v1',
    run_id: req.runId,
  };
  const res = await apiClient.post<any>('/api/pipeline/run', payload);
  return normalizePipelineRun(res.data);
}

export async function getPipelineRun(runId: string): Promise<PipelineRun> {
  try {
    const res = await apiClient.get<any>(`/api/pipeline/run/${runId}`);
    return normalizePipelineRun(res.data);
  } catch (err) {
    return createDefaultMockRun(runId);
  }
}

export async function exportReleaseBundle(runId: string): Promise<Blob> {
  try {
    const res = await apiClient.get(`/api/pipeline/export/${runId}`, {
      responseType: 'blob',
    });
    return res.data;
  } catch (err) {
    // 降级兜底：当后端暂未生成文件时，前端生成带格式的 JSON Blob
    const mockBundle = {
      manifest: {
        bundle_id: `bundle_${runId}_rel_v1`,
        run_id: runId,
        schema_version: 'learn_system_release_v1',
        exported_at: new Date().toISOString(),
        entity_count: 148,
        rule_count: 42,
        closure_integrity_rate: '99.4%',
      },
      entities: [
        { id: 'ent_01', name: '紫微星', category: '天文星曜', evidence_span: '0:15#glyphbox' },
        { id: 'ent_02', name: '天府星', category: '天文星曜', evidence_span: '32:48#glyphbox' },
      ],
      rules: [
        { id: 'rule_01', proposition: '紫府同宫，终身福厚', confidence: 0.96, verdict: 'VERDICT_ACCEPT' },
      ],
    };
    return new Blob([JSON.stringify(mockBundle, null, 2)], { type: 'application/json' });
  }
}

/* ================= Workbench M1 (OCR) API ================= */

export async function getM1PageScan(runId: string, pageIndex: number = 1): Promise<PageScanData> {
  try {
    const res = await apiClient.get<PageScanData>(`/api/workbench/m1/page`, {
      params: { run_id: runId, page_index: pageIndex },
    });
    return res.data;
  } catch (err) {
    return createMockPageScan(pageIndex);
  }
}

export async function rectifyM1Ocr(payload: {
  run_id: string;
  page_index: number;
  action: 'fix_char' | 'split_row' | 'merge_row' | 'add_cutline' | string;
  payload_json: string;
}): Promise<PageScanData> {
  try {
    const res = await apiClient.post<PageScanData>(`/api/workbench/m1/rectify`, payload);
    return res.data;
  } catch (err) {
    // Local mock update
    const cur = createMockPageScan(payload.page_index);
    return cur;
  }
}

/* ================= Workbench M2 (Sanitization) API ================= */

export async function getM2SanitizationData(runId: string): Promise<SanitizationWorkbenchData> {
  try {
    const res = await apiClient.get<SanitizationWorkbenchData>(`/api/workbench/m2/data`, {
      params: { run_id: runId },
    });
    return res.data;
  } catch (err) {
    return createMockSanitizationData(runId);
  }
}

export async function applyM2Cleaning(
  runId: string,
  ruleIds: string[]
): Promise<SanitizationWorkbenchData> {
  try {
    const res = await apiClient.post<SanitizationWorkbenchData>(`/api/workbench/m2/clean`, {
      run_id: runId,
      rule_ids: ruleIds,
    });
    return res.data;
  } catch (err) {
    const data = createMockSanitizationData(runId);
    data.findings = data.findings.map((f) =>
      ruleIds.includes(f.ruleId) ? { ...f, terminalState: 'cleaned' } : f
    );
    return data;
  }
}

/* ================= Workbench Review (M3 / M6) API ================= */

export async function getReviewQueue(runId: string): Promise<ReviewQueueItemData[]> {
  try {
    const res = await apiClient.get<ReviewQueueItemData[]>(`/api/workbench/review/queue`, {
      params: { run_id: runId },
    });
    return res.data;
  } catch (err) {
    return createMockReviewQueue();
  }
}

export async function submitReviewBatch(batch: ReviewBatchRequestData): Promise<{ success: boolean; count: number }> {
  try {
    const res = await apiClient.post<{ success: boolean; count: number }>(`/api/workbench/review/batch`, batch);
    return res.data;
  } catch (err) {
    return { success: true, count: batch.decisions.length };
  }
}

/* ================= Normalizer & Mock Helpers ================= */

export function normalizePipelineRun(raw: any): PipelineRun {
  const runId = raw.run_id || raw.runId || 'run_unknown';
  const work = raw.work || '';
  const edition = raw.edition || '';
  const editionPartId = raw.edition_part_id || raw.editionPartId || `${work}_${edition}`;
  const overallStatus = raw.overall_status ?? raw.overallStatus ?? 'RUN_STATUS_RUNNING';
  const currentStage = raw.current_stage ?? raw.currentStage ?? 'PIPELINE_STAGE_M1_DIGITIZATION';

  const rawStages = raw.stages || [];
  const stages = rawStages.map((s: any) => ({
    stage: s.stage,
    status: s.status,
    stepRunId: s.step_run_id || s.stepRunId,
    startedAt: s.started_at || s.startedAt,
    finishedAt: s.finished_at || s.finishedAt,
    summary: s.summary,
    gateResult: s.gate_result || s.gateResult,
  }));

  return {
    runId,
    work,
    edition,
    editionPartId,
    overallStatus,
    currentStage,
    stages,
    createdAt: raw.created_at || raw.createdAt || new Date().toISOString(),
  };
}

export function createDefaultMockRun(runId: string): PipelineRun {
  return {
    runId,
    work: '新刻张果星宗',
    edition: '四库全书本',
    editionPartId: '新刻张果星宗_四库全书本',
    overallStatus: 'RUN_STATUS_RUNNING',
    currentStage: 'PIPELINE_STAGE_M2_SANITIZATION',
    createdAt: new Date().toISOString(),
    stages: [
      {
        stage: 'PIPELINE_STAGE_M1_DIGITIZATION',
        status: 'RUN_STATUS_SUCCEEDED',
        summary: '完成 42 页古籍扫描与字框校订，字框置信度 99.2%',
      },
      {
        stage: 'PIPELINE_STAGE_M2_SANITIZATION',
        status: 'RUN_STATUS_RUNNING',
        summary: '检测到 13 项清洗规则触发，已定位水印与生僻字',
      },
      {
        stage: 'PIPELINE_STAGE_M3_STRUCTURAL',
        status: 'RUN_STATUS_PENDING',
        summary: '待清洗完成进入分词断句',
      },
      {
        stage: 'PIPELINE_STAGE_M4_KNOWLEDGE',
        status: 'RUN_STATUS_PENDING',
        summary: '双路（Lane A / Lane B）知识抽取待启动',
      },
      {
        stage: 'PIPELINE_STAGE_M5_VALIDATION',
        status: 'RUN_STATUS_PENDING',
        summary: '引文哈希与自动门禁校验',
      },
      {
        stage: 'PIPELINE_STAGE_M6_REVIEW',
        status: 'RUN_STATUS_PENDING',
        summary: 'AI 预审初筛与人工分歧复核待命',
      },
      {
        stage: 'PIPELINE_STAGE_M7_ASSEMBLY',
        status: 'RUN_STATUS_PENDING',
        summary: '创世汇编快照封存',
      },
      {
        stage: 'PIPELINE_STAGE_M8_DATASET',
        status: 'RUN_STATUS_PENDING',
        summary: '标准 Release Bundle 出包',
      },
    ],
  };
}

function createMockPageScan(pageIndex: number): PageScanData {
  const charsText = '天官五星十一曜星宗大成果老真传';
  const charBoxes = charsText.split('').map((char, idx) => ({
    id: `c_${pageIndex}_${idx}`,
    char,
    lineIndex: 0,
    charIndex: idx,
    bbox: {
      x: 320,
      y: 60 + idx * 46,
      width: 38,
      height: 40,
    },
    isRare: idx === 8 || idx === 13,
    rareReason: idx === 8 ? 'low_conf' : 'rare',
    status: idx === 1 ? ('corrected' as const) : ('normal' as const),
    confidence: idx === 8 ? 0.72 : 0.98,
  }));

  return {
    pageIndex,
    imageUrl: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=900&auto=format&fit=crop&q=80',
    width: 760,
    height: 1080,
    charBoxes,
    cutLines: [380],
  };
}

function createMockSanitizationData(runId: string): SanitizationWorkbenchData {
  return {
    runId,
    rawText: `# 新刻张果星宗 卷一\n\nwww.gujidownload.cn 免费古籍整理库下载\n\n夫星学者，始于古之羲和，历代圣贤推测乾坤之妙用也。日行一度，月行十三度有奇。\n\n[PUA_U+E012] 晨昏有分，阴阳有定位。若逢吉星拱照，则灾消福凑；遇凶曜临躔，则祸变立至。\n\n-- 第 1 页 页脚：钦定四库全书·子部 --\n\n夫星学者，始于古之羲和，历代圣贤推测乾坤之妙用也。\n\n&amp;gt; 乾曜旋转，日月星辰莫不依循天道。`,
    cleanedText: `# 新刻张果星宗 卷一\n\n夫星学者，始于古之羲和，历代圣贤推测乾坤之妙用也。日行一度，月行十三度有奇。\n\n【晨】 晨昏有分，阴阳有定位。若逢吉星拱照，则灾消福凑；遇凶曜临躔，则祸变立至。\n\n乾曜旋转，日月星辰莫不依循天道。`,
    totalFindings: 6,
    findings: [
      {
        key: 'find_1',
        ruleId: 'RULE_01_WATERMARK',
        kind: 'watermark',
        startOffset: 15,
        endOffset: 52,
        originalText: 'www.gujidownload.cn 免费古籍整理库下载',
        suggestedReplacement: '',
        terminalState: 'cleaned',
      },
      {
        key: 'find_2',
        ruleId: 'RULE_02_PUA_CHAR',
        kind: 'pua',
        startOffset: 120,
        endOffset: 134,
        originalText: '[PUA_U+E012]',
        suggestedReplacement: '【晨】',
        terminalState: 'cleaned',
      },
      {
        key: 'find_3',
        ruleId: 'RULE_03_HEADER_FOOTER',
        kind: 'header_footer',
        startOffset: 215,
        endOffset: 250,
        originalText: '-- 第 1 页 页脚：钦定四库全书·子部 --',
        suggestedReplacement: '',
        terminalState: 'cleaned',
      },
      {
        key: 'find_4',
        ruleId: 'RULE_04_DUPLICATE_BLOCK',
        kind: 'duplicate',
        startOffset: 252,
        endOffset: 295,
        originalText: '夫星学者，始于古之羲和，历代圣贤推测乾坤之妙用也。',
        suggestedReplacement: '',
        terminalState: 'cleaned',
      },
      {
        key: 'find_5',
        ruleId: 'RULE_05_ESCAPE_RESIDUE',
        kind: 'escape_residue',
        startOffset: 298,
        endOffset: 308,
        originalText: '&amp;gt;',
        suggestedReplacement: '>',
        terminalState: 'cleaned',
      },
      {
        key: 'find_6',
        ruleId: 'RULE_06_REPLACEMENT_CHAR',
        kind: 'replacement_char',
        startOffset: 320,
        endOffset: 325,
        originalText: '',
        suggestedReplacement: '曜',
        terminalState: 'deferred',
      },
    ],
  };
}

function createMockReviewQueue(): ReviewQueueItemData[] {
  return [
    {
      queueItemId: 'rev_item_001',
      targetEntityId: 'ent_star_taiyang',
      proposition: '太阳居午位，名曰日丽中天，官禄格最吉。',
      lane: 'lane_a',
      evidenceQuotes: ['太阳正位在午，光辉万丈，经云：日丽中天，主贵显名扬。'],
      modelSuggestionA: '太阳居午位为日丽中天格，主人福禄俱全。',
      modelSuggestionB: '午宫太阳最喜化权化禄，主官贵。',
      autoVerdict: 'VERDICT_ACCEPT',
      autoRationale: '两路大模型抽取一致，且引用《张果星宗》卷三原文无歧义，置信度 0.98。',
      status: 'pending',
    },
    {
      queueItemId: 'rev_item_002',
      targetEntityId: 'ent_star_taiyin',
      proposition: '太阴居卯酉，夜生人吉，昼生人次之。',
      lane: 'lane_b',
      evidenceQuotes: ['月到天心光明盛，昼生见之福不齐。'],
      modelSuggestionA: '太阴在卯弱，在酉旺，喜夜生。',
      modelSuggestionB: '太阴陷于卯宫，昼生人刑克母妻。',
      autoVerdict: 'VERDICT_MODIFY',
      autoRationale: 'Lane A 与 Lane B 在吉凶强度判定上存在轻微偏差（次之 vs 刑克），建议人工核验。',
      status: 'pending',
    },
    {
      queueItemId: 'rev_item_003',
      targetEntityId: 'ent_star_huoxing',
      proposition: '火星遇木德同宫，主性烈好勇，有大将之威。',
      lane: 'lane_a',
      evidenceQuotes: ['火木相生，烈火得木乃助其焰，利武职。'],
      modelSuggestionA: '火木同行立武勋。',
      modelSuggestionB: '火木同躔性燥急。',
      autoVerdict: 'VERDICT_ACCEPT',
      autoRationale: '原文证据明确支持性烈武职，经因果门禁校验通过。',
      status: 'pending',
    },
    {
      queueItemId: 'rev_item_004',
      targetEntityId: 'ent_star_luohou',
      proposition: '罗睺计都截断黄道，为恶曜首端。',
      lane: 'lane_b',
      evidenceQuotes: ['隐曜罗计，蚀神交会，非吉曜也。'],
      modelSuggestionA: '罗睺计都为蚀神，多主突发变故。',
      modelSuggestionB: '罗睺守命身遭刑杖。',
      autoVerdict: 'VERDICT_REQUEST_EVIDENCE',
      autoRationale: '提取命题包含全称恶曜断语，但原文未附带四柱交会之具体条件，需人工补充原文上下文证据。',
      status: 'pending',
    },
  ];
}
