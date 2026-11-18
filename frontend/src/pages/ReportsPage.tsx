import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import type { AnalysisResult, ProjectFindingsResponse, ProjectCorrectionsResponse, ProjectDetail } from '../types/api';
import {
  FileDown,
  FileText,
  Download,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Code2,
  FileCode,
  Activity,
  Layers,
  Sparkles,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [findings, setFindings] = useState<ProjectFindingsResponse | null>(null);
  const [corrections, setCorrections] = useState<ProjectCorrectionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingJson, setDownloadingJson] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!projectId) return;
      setLoading(true);
      try {
        const [projData, anData, fData, cData] = await Promise.allSettled([
          api.getProject(projectId),
          api.getAnalysis(projectId),
          api.getFindings(projectId),
          api.getCorrections(projectId),
        ]);

        if (projData.status === 'fulfilled') setProject(projData.value);
        if (anData.status === 'fulfilled') setAnalysis(anData.value);
        if (fData.status === 'fulfilled') setFindings(fData.value);
        if (cData.status === 'fulfilled') setCorrections(cData.value);
      } catch (err) {
        console.error('Error loading report data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [projectId]);

  // Handle JSON export download
  const handleDownloadJson = async () => {
    if (!projectId) return;
    setDownloadingJson(true);
    try {
      const data = await api.getJsonReport(projectId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `DocSync-Audit-Report-${projectId}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download JSON report:', err);
      alert('Could not download JSON report. Make sure analysis and drift detection have completed.');
    } finally {
      setDownloadingJson(false);
    }
  };

  const handleDownloadPdf = () => {
    if (!projectId) return;
    window.open(api.getPdfReportUrl(projectId), '_blank');
  };

  // Calculate health score & metrics
  const totalFindings = findings?.total_findings || 0;
  const criticalCount = findings?.findings?.filter(f => f.severity === 'CRITICAL').length || 0;
  const highCount = findings?.findings?.filter(f => f.severity === 'HIGH').length || 0;
  const mediumCount = findings?.findings?.filter(f => f.severity === 'MEDIUM').length || 0;
  const lowCount = findings?.findings?.filter(f => f.severity === 'LOW').length || 0;

  // Health index: 100 - (critical*25 + high*10 + med*5 + low*2) bounded [0, 100]
  const penalty = criticalCount * 25 + highCount * 10 + mediumCount * 5 + lowCount * 2;
  const healthScore = Math.max(0, Math.min(100, 100 - penalty));

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <FileDown className="w-6 h-6 text-indigo-400" />
            Executive Audit & Compliance Reports
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Export presentation-ready PDF summaries and machine-readable JSON audit bundles with complete drift provenance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleDownloadPdf}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium shadow-md transition-all cursor-pointer"
          >
            <Download className="w-4 h-4" />
            Download PDF Report
          </button>
          <button
            onClick={handleDownloadJson}
            disabled={downloadingJson}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700/80 font-medium transition-all disabled:opacity-50 cursor-pointer"
          >
            <FileCode className="w-4 h-4 text-cyan-400" />
            {downloadingJson ? 'Exporting...' : 'Export JSON Audit'}
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Health Score Card */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Documentation Health
              </span>
              <Activity className="w-5 h-5 text-indigo-400" />
            </div>
            <div className="mt-4 flex items-baseline gap-2">
              <span className={`text-5xl font-black font-mono ${
                healthScore >= 80 ? 'text-emerald-400' :
                healthScore >= 50 ? 'text-amber-400' :
                'text-rose-400'
              }`}>
                {healthScore}%
              </span>
              <span className="text-xs text-slate-400">Integrity Index</span>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-slate-800/80 text-xs text-slate-400">
            {healthScore >= 80 ? (
              <span className="text-emerald-300 font-medium flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" /> High alignment with codebase
              </span>
            ) : (
              <span className="text-amber-300 font-medium flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-400" /> Drift detected, requires updates
              </span>
            )}
          </div>
        </div>

        {/* Severity Distribution Card */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Drift Findings Severity Breakdown
          </div>
          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-rose-300 font-mono">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span> CRITICAL
              </span>
              <span className="font-bold text-white font-mono">{criticalCount}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-amber-300 font-mono">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> HIGH
              </span>
              <span className="font-bold text-white font-mono">{highCount}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-yellow-300 font-mono">
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500"></span> MEDIUM
              </span>
              <span className="font-bold text-white font-mono">{mediumCount}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-blue-300 font-mono">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span> LOW
              </span>
              <span className="font-bold text-white font-mono">{lowCount}</span>
            </div>
          </div>
        </div>

        {/* Audit Scope Card */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 flex flex-col justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Analysis Scope & Volume
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                <div className="text-slate-500 text-[10px] uppercase">Lines of Code</div>
                <div className="text-base font-bold text-white font-mono mt-0.5">
                  {analysis?.summary?.total_loc?.toLocaleString() || 0}
                </div>
              </div>
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                <div className="text-slate-500 text-[10px] uppercase">Functions & Classes</div>
                <div className="text-base font-bold text-white font-mono mt-0.5">
                  {(analysis?.summary?.total_functions || 0) + (analysis?.summary?.total_classes || 0)}
                </div>
              </div>
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                <div className="text-slate-500 text-[10px] uppercase">Doc Files</div>
                <div className="text-base font-bold text-white font-mono mt-0.5">
                  {analysis?.summary?.documentation_files_count || 0}
                </div>
              </div>
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                <div className="text-slate-500 text-[10px] uppercase">Corrections Ready</div>
                <div className="text-base font-bold text-indigo-400 font-mono mt-0.5">
                  {corrections?.total_corrections || 0}
                </div>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500 font-mono truncate">
            Project: {project?.name || projectId}
          </div>
        </div>
      </div>

      {/* Available Export Formats Detail */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* PDF Card */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-950/80 border border-indigo-800/60 flex items-center justify-center text-indigo-400">
                <FileDown className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Executive PDF Audit Report</h3>
                <p className="text-xs text-slate-400 font-mono">ReportLab 5.1 Generated Stream</p>
              </div>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Cleanly structured for engineering leadership and compliance reviews. Includes document health summary, severity breakdown tables, detailed drift findings, agent investigation provenance, and synthesized unified diff patches.
            </p>
          </div>
          <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-500">Format: Standard A4 / PDF 1.4</span>
            <button
              onClick={handleDownloadPdf}
              className="px-4 py-2 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" /> Download PDF
            </button>
          </div>
        </div>

        {/* JSON Card */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
                <FileCode className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Full-Fidelity JSON Audit Bundle</h3>
                <p className="text-xs text-slate-400 font-mono">Machine-readable JSON schema</p>
              </div>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Direct export of deterministic parsing results, NetworkX dependency graphs, AST metadata, drift claims vs codebase facts, full agent execution steps, and evidence pool objects suitable for CI/CD gates.
            </p>
          </div>
          <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-500">Format: JSON schema v1.0</span>
            <button
              onClick={handleDownloadJson}
              disabled={downloadingJson}
              className="px-4 py-2 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg font-medium border border-slate-700/80 transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <FileDown className="w-3.5 h-3.5 text-cyan-400" />
              {downloadingJson ? 'Downloading...' : 'Export JSON'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
