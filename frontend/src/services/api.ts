import axios from 'axios';
import type {
  ProjectSummary,
  ProjectDetail,
  ProjectCreate,
  ProjectFilesResponse,
  UploadResponse,
  AnalysisResult,
  DependencyGraph,
  ProjectFindingsResponse,
  DriftFinding,
  AgentRunResponse,
  AgentExecutionTrace,
  ProjectCorrectionsResponse,
  DocumentationCorrection,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // System Health
  async getHealth(): Promise<{ status: string; app: string; gemini_configured: boolean; data_dir_ready: boolean }> {
    const res = await client.get('/health');
    return res.data;
  },

  // Projects
  async listProjects(): Promise<ProjectSummary[]> {
    const res = await client.get('/api/projects');
    return res.data;
  },

  async createProject(data: ProjectCreate): Promise<ProjectSummary> {
    const res = await client.post('/api/projects', data);
    return res.data;
  },

  async getProject(projectId: string): Promise<ProjectDetail> {
    const res = await client.get(`/api/projects/${projectId}`);
    return res.data;
  },

  async getProjectFiles(projectId: string): Promise<ProjectFilesResponse> {
    const res = await client.get(`/api/projects/${projectId}/files`);
    return res.data;
  },

  async deleteProject(projectId: string): Promise<{ status: string; message: string }> {
    const res = await client.delete(`/api/projects/${projectId}`);
    return res.data;
  },

  // Uploads
  async uploadZip(projectId: string, file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await client.post(`/api/projects/${projectId}/upload-zip`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async uploadDocuments(projectId: string, files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await client.post(`/api/projects/${projectId}/upload-documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Analysis
  async triggerAnalysis(projectId: string): Promise<AnalysisResult> {
    const res = await client.post(`/api/projects/${projectId}/analyze`);
    return res.data;
  },

  async getAnalysis(projectId: string): Promise<AnalysisResult> {
    const res = await client.get(`/api/projects/${projectId}/analysis`);
    return res.data;
  },

  async getDependencies(projectId: string): Promise<DependencyGraph> {
    const res = await client.get(`/api/projects/${projectId}/dependencies`);
    return res.data;
  },

  // Drift Detection
  async detectDrift(projectId: string): Promise<ProjectFindingsResponse> {
    const res = await client.post(`/api/projects/${projectId}/detect-drift`);
    return res.data;
  },

  async getFindings(projectId: string): Promise<ProjectFindingsResponse> {
    const res = await client.get(`/api/projects/${projectId}/findings`);
    return res.data;
  },

  async getFinding(projectId: string, findingId: string): Promise<DriftFinding> {
    const res = await client.get(`/api/projects/${projectId}/findings/${findingId}`);
    return res.data;
  },

  // Agent Orchestrator
  async runAgent(projectId: string): Promise<AgentRunResponse> {
    const res = await client.post(`/api/projects/${projectId}/run-agent`);
    return res.data;
  },

  async getAgentTrace(projectId: string): Promise<AgentExecutionTrace> {
    const res = await client.get(`/api/projects/${projectId}/agent-trace`);
    return res.data;
  },

  // Documentation Corrections
  async getCorrections(projectId: string): Promise<ProjectCorrectionsResponse> {
    const res = await client.get(`/api/projects/${projectId}/corrections`);
    return res.data;
  },

  async getCorrection(projectId: string, correctionId: string): Promise<DocumentationCorrection> {
    const res = await client.get(`/api/projects/${projectId}/corrections/${correctionId}`);
    return res.data;
  },

  // Reports
  async getJsonReport(projectId: string): Promise<any> {
    const res = await client.get(`/api/projects/${projectId}/report/json`);
    return res.data;
  },

  getPdfReportUrl(projectId: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/report/pdf`;
  },
};
