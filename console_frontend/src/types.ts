export type PipelineStageEnum =
  | 'PIPELINE_STAGE_UNSPECIFIED'
  | 'PIPELINE_STAGE_M1_DIGITIZATION'
  | 'PIPELINE_STAGE_M2_SANITIZATION'
  | 'PIPELINE_STAGE_M3_STRUCTURAL'
  | 'PIPELINE_STAGE_M4_KNOWLEDGE'
  | 'PIPELINE_STAGE_M5_VALIDATION'
  | 'PIPELINE_STAGE_M6_REVIEW'
  | 'PIPELINE_STAGE_M7_ASSEMBLY'
  | 'PIPELINE_STAGE_M8_DATASET';

export type RunStatusEnum =
  | 'RUN_STATUS_UNSPECIFIED'
  | 'RUN_STATUS_PENDING'
  | 'RUN_STATUS_RUNNING'
  | 'RUN_STATUS_AWAITING_HUMAN'
  | 'RUN_STATUS_SUCCEEDED'
  | 'RUN_STATUS_FAILED';

export interface StageProgress {
  stage: PipelineStageEnum | number;
  status: RunStatusEnum | number;
  stepRunId?: string;
  startedAt?: number;
  finishedAt?: number;
  summary?: string;
  gateResult?: string;
}

export interface PipelineRun {
  runId: string;
  work: string;
  edition: string;
  editionPartId?: string;
  overallStatus: RunStatusEnum | number;
  currentStage: PipelineStageEnum | number;
  stages: StageProgress[];
  createdAt?: string;
}

export interface PipelineRunRequest {
  work: string;
  edition: string;
  fileType: string;
  sourceFilePath?: string;
  techniqueId?: string;
  promptProfileId?: string;
  runId?: string;
}

export interface WebSocketEvent {
  eventType: 'stage_change' | 'log_append' | 'human_ready' | 'error' | string;
  runId: string;
  stage?: PipelineStageEnum | number;
  status?: RunStatusEnum | number;
  logMessage?: string;
  payloadJson?: string;
  timestamp: number;
}

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface CharBoxItem {
  id?: string;
  char: string;
  bbox: BBox;
  lineIndex: number;
  charIndex: number;
  isRare?: boolean;
  rareReason?: 'low_conf' | 'rare' | string;
  status?: 'normal' | 'corrected' | 'flagged';
  confidence?: number;
}

export interface PageScanData {
  pageIndex: number;
  imageUrl: string;
  imageSha256?: string;
  width: number;
  height: number;
  charBoxes: CharBoxItem[];
  cutLines: number[];
}

export interface SanitizationFindingItem {
  key?: string;
  ruleId: string;
  kind: 'watermark' | 'pua' | 'escape_residue' | 'header_footer' | 'duplicate' | string;
  startOffset: number;
  endOffset: number;
  originalText: string;
  suggestedReplacement: string;
  terminalState: 'cleaned' | 'deferred' | 'retained' | string;
}

export interface SanitizationWorkbenchData {
  runId: string;
  rawText: string;
  cleanedText: string;
  findings: SanitizationFindingItem[];
  totalFindings: number;
}

export type VerdictType =
  | 'VERDICT_UNSPECIFIED'
  | 'VERDICT_ACCEPT'
  | 'VERDICT_MODIFY'
  | 'VERDICT_REJECT'
  | 'VERDICT_REQUEST_EVIDENCE';

export interface ReviewQueueItemData {
  queueItemId: string;
  targetEntityId: string;
  proposition: string;
  lane: 'lane_a' | 'lane_b' | string;
  evidenceQuotes: string[];
  modelSuggestionA?: string;
  modelSuggestionB?: string;
  autoVerdict: VerdictType;
  autoRationale: string;
  // Human review decision state
  humanVerdict?: VerdictType;
  humanRationale?: string;
  modifiedContent?: string;
  status?: 'pending' | 'decided';
}

export interface DecisionSubmissionItem {
  queueItemId: string;
  verdict: VerdictType;
  rationale?: string;
  modifiedContent?: string;
  evidenceRefs?: string[];
}

export interface ReviewBatchRequestData {
  runId: string;
  stepRunId?: string;
  resumeToken?: string;
  decisions: DecisionSubmissionItem[];
}

export interface PipelineLogEntry {
  id: string;
  timestamp: number;
  runId: string;
  stage?: string;
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
}
