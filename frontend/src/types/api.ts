export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export type DriftCategory = 'OUTDATED' | 'MISSING' | 'CONTRADICTORY' | 'INVALID' | 'INCOMPLETE';

export type VerificationStatus = 'VERIFIED' | 'UNVERIFIED' | 'UNCERTAIN';

export type DetectionMethod = 'DETERMINISTIC' | 'AI_ASSISTED' | 'HYBRID';

export interface ProjectSummary {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  has_source: boolean;
  source_archive_name: string | null;
  document_count: number;
  document_names: string[];
  analysis_status: string; // "unprocessed" | "completed" | "analyzing"
  last_analyzed_at: string | null;
  audit_mode?: 'zip' | 'github';
  github_repo?: string | null;
  github_branch?: string | null;
  latest_commit_sha?: string | null;
  drift_status?: string | null;
  last_drift_detected_at?: string | null;
}

export interface ProjectDetail extends ProjectSummary {
  file_count: number;
  total_size_bytes: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  audit_mode?: 'zip' | 'github';
  github_repo_url?: string;
  github_branch?: string;
  github_token?: string;
}

export interface FileInfo {
  rel_path: string;
  size_bytes: number;
  category: 'source' | 'documentation' | 'configuration' | 'other';
  language: string | null;
  extension: string;
}

export interface ProjectFilesResponse {
  project_id: string;
  total_files: number;
  files: FileInfo[];
}

export interface UploadResponse {
  project_id: string;
  message: string;
  files_processed: number;
  filenames: string[];
}

export interface DocumentDeleteResponse {
  project_id: string;
  filename: string;
  message: string;
  remaining_documents: string[];
  document_count: number;
}

export interface ParameterInfo {
  name: string;
  default_value: string | null;
  annotation: string | null;
}

export interface FunctionInfo {
  name: string;
  parameters: ParameterInfo[];
  return_annotation: string | null;
  is_async: boolean;
  docstring: string | null;
  line_start: number;
  line_end: number;
}

export interface MethodInfo extends FunctionInfo {
  is_static: boolean;
  is_classmethod: boolean;
}

export interface ClassInfo {
  name: string;
  bases: string[];
  docstring: string | null;
  methods: MethodInfo[];
  line_start: number;
  line_end: number;
}

export interface ImportInfo {
  module: string;
  imported_names: string[];
  is_from_import: boolean;
  line_number: number;
}

export interface ParsedSourceFile {
  file_path: string;
  language: string;
  functions: FunctionInfo[];
  classes: ClassInfo[];
  imports: ImportInfo[];
  exports: any[];
  docstrings: string[];
  comments: string[];
  loc: number;
  parse_error: string | null;
}

export interface DocSection {
  heading: string;
  level: number;
  content: string;
  code_examples: string[];
  page_number: number | null;
}

export interface ExtractedDocFile {
  file_path: string;
  doc_type: string;
  title: string | null;
  sections: DocSection[];
  code_examples: string[];
  function_references: string[];
  class_references: string[];
  parameter_references: string[];
  setup_instructions: string[];
  cli_commands: string[];
  config_references: string[];
  total_pages: number | null;
  extraction_note: string | null;
}

export interface ExtractedConfigItem {
  key: string;
  value_type: string;
  default_value: string | null;
  is_secret: boolean;
  file_path: string;
  line_number: number | null;
  source_code_references: string[];
}

export interface ExtractedConfigFile {
  file_path: string;
  format: string;
  items: ExtractedConfigItem[];
  parse_error: string | null;
}

export interface DependencyNode {
  id: string;
  label: string;
  file_path: string;
  language: string;
}

export interface DependencyEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface DependencyGraph {
  nodes: DependencyNode[];
  edges: DependencyEdge[];
  cycles: string[][];
  external_dependencies: string[];
  isolated_modules: string[];
}

export interface AnalysisSummary {
  project_id: string;
  analyzed_at: string;
  source_files_count: number;
  total_functions: number;
  total_classes: number;
  total_methods: number;
  total_loc: number;
  documentation_files_count: number;
  configuration_files_count: number;
  dependency_nodes_count: number;
  dependency_edges_count: number;
  circular_dependency_count: number;
  warnings: string[];
}

export interface AnalysisResult {
  project_id: string;
  summary: AnalysisSummary;
  source_files: ParsedSourceFile[];
  documentation_files: ExtractedDocFile[];
  configuration_files: ExtractedConfigFile[];
  dependency_graph: DependencyGraph;
}

export interface EvidenceReference {
  evidence_id: string;
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  page_number: number | null;
  snippet: string;
  source_type: 'code' | 'doc' | 'config';
}

export interface DocumentLocation {
  file: string;
  line?: number | null;
  page?: number | null;
  section?: string | null;
}

export interface SourceLocation {
  file: string;
  line_start?: number | null;
  line_end?: number | null;
}

export interface DriftFinding {
  finding_id: string;
  project_id: string;
  category: DriftCategory;
  title: string;
  description: string;
  severity: SeverityLevel;
  confidence: number;
  verification_status: VerificationStatus;
  documentation: DocumentLocation;
  source: SourceLocation | null;
  symbol: string | null;
  documented_claim: string;
  actual_fact: string;
  explanation: string;
  suggested_correction: string | null;
  detection_method: DetectionMethod;
  evidence_ids: string[];
  impact_explanation: string | null;
}

export interface ProjectFindingsResponse {
  project_id: string;
  total_findings: number;
  findings: DriftFinding[];
  evidence_pool: EvidenceReference[];
}

export interface AgentActionStep {
  step_number: number;
  agent_action: string;
  tool_selected: string | null;
  tool_input_summary: string | null;
  tool_output_summary: string | null;
  execution_status: 'SUCCESS' | 'FAILED' | 'SKIPPED' | 'TERMINATED';
  timestamp: string;
  reason: string;
}

export interface AgentExecutionTrace {
  project_id: string;
  started_at: string;
  completed_at: string;
  total_steps: number;
  steps: AgentActionStep[];
  termination_reason: string;
  status: 'COMPLETED' | 'FAILED' | 'PARTIAL';
}

export interface AgentRunResponse {
  project_id: string;
  status: string;
  message: string;
  total_findings_generated: number;
  total_corrections_generated: number;
  trace: AgentExecutionTrace;
}

export interface DocumentationCorrection {
  correction_id: string;
  project_id: string;
  file_path: string;
  original_text: string;
  proposed_replacement: string;
  unified_diff: string;
  line_start: number | null;
  line_end: number | null;
  section_name: string | null;
  reason: string;
  supporting_finding_ids: string[];
  supporting_evidence_ids: string[];
  validation_status: 'VERIFIED' | 'UNVERIFIED';
}

export interface ProjectCorrectionsResponse {
  project_id: string;
  total_corrections: number;
  corrections: DocumentationCorrection[];
}

// ==========================================
// Mode 2: GitHub Repository Audit Interfaces
// ==========================================

export interface GitHubConnectRequest {
  repo_url: string;
  branch?: string;
  github_token?: string;
}

export interface GitHubBranchInfo {
  name: string;
  is_default: boolean;
  commit_sha: string;
}

export interface GitHubRepoStatus {
  connected: boolean;
  repo_url: string | null;
  owner: string | null;
  repo_name: string | null;
  branch: string | null;
  default_branch: string | null;
  is_private: boolean;
  latest_commit_sha: string | null;
  last_synced_at: string | null;
  sync_status: string | null;
  drift_status: string | null;
  total_syncs: number;
  tracked_doc_files: string[];
}

export interface GitHubCommitHistoryItem {
  commit_sha: string;
  author: string;
  date: string;
  message: string;
  files_changed: string[];
  doc_changes_count: number;
  code_changes_count: number;
  findings_detected_count: number;
  synced_at: string;
  sync_status: string;
}

export interface GitHubSyncResponse {
  project_id: string;
  status: 'UP_TO_DATE' | 'CHANGES_DETECTED' | 'ANALYSIS_COMPLETED' | 'DRIFT_DETECTED' | 'FAILED';
  message: string;
  previous_commit_sha: string | null;
  latest_commit_sha: string;
  files_changed: string[];
  doc_changes: string[];
  code_changes: string[];
  drift_findings_count: number;
  synced_at: string;
  is_up_to_date: boolean;
}
