import React from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  FolderGit2,
  Upload,
  Cpu,
  AlertTriangle,
  Bot,
  Network,
  FileCheck2,
  FileText,
  Calendar,
  Layers,
  ArrowRight,
  HardDrive,
  FileCode,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../services/api';
import type { ProjectDetail } from '../types/api';

export const OverviewPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = React.useState<ProjectDetail | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!projectId) return;
    api.getProject(projectId)
      .then((data) => setProject(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return <div className="p-8 text-sm text-slate-400">Loading project overview...</div>;
  }

  if (!project) {
    return <div className="p-8 text-sm text-rose-400">Project not found.</div>;
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header Info */}
      <div className="p-6 rounded-xl bg-[#0d1322] border border-slate-800 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-100">{project.name}</h1>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                project.analysis_status === 'completed'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
              }`}
            >
              {project.analysis_status}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-2 max-w-2xl">
            {project.description || 'No description provided.'}
          </p>
          <div className="flex items-center gap-6 text-[11px] text-slate-500 mt-4 font-mono">
            <span>Project ID: {project.id}</span>
            <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
            <span>Updated: {new Date(project.updated_at).toLocaleDateString()}</span>
          </div>
        </div>

        <Link
          to={`/projects/${project.id}/uploads`}
          className="flex items-center gap-2 px-3.5 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Upload Files</span>
        </Link>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-[#0b101b] border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Files In Scope</span>
            <FileCode className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">{project.file_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">Source & doc files</div>
        </div>

        <div className="p-4 rounded-xl bg-[#0b101b] border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Storage Size</span>
            <HardDrive className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">
            {(project.total_size_bytes / 1024).toFixed(1)} KB
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Isolated disk storage</div>
        </div>

        <div className="p-4 rounded-xl bg-[#0b101b] border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Documentation Files</span>
            <FileText className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">{project.document_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">PDF & Markdown docs</div>
        </div>

        <div className="p-4 rounded-xl bg-[#0b101b] border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Security Isolation</span>
            <ShieldCheck className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-sky-400 mt-2">Enforced</div>
          <div className="text-[11px] text-slate-500 mt-1">Secrets masked; 0 code execution</div>
        </div>
      </div>

      {/* Navigation Quick Actions */}
      <div>
        <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-4">Workspace Navigation</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to={`/projects/${project.id}/analysis`}
            className="p-4 rounded-xl bg-[#0d1322] border border-slate-800/80 hover:border-indigo-500/40 transition-all flex items-start gap-4 group"
          >
            <div className="p-2.5 rounded-lg bg-indigo-600/10 text-indigo-400 border border-indigo-500/20">
              <Cpu className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-slate-200 text-sm group-hover:text-indigo-300 transition-colors flex items-center justify-between">
                <span>Codebase Analysis</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Inspect AST functions, classes, and configuration items.
              </p>
            </div>
          </Link>

          <Link
            to={`/projects/${project.id}/findings`}
            className="p-4 rounded-xl bg-[#0d1322] border border-slate-800/80 hover:border-amber-500/40 transition-all flex items-start gap-4 group"
          >
            <div className="p-2.5 rounded-lg bg-amber-600/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-slate-200 text-sm group-hover:text-amber-300 transition-colors flex items-center justify-between">
                <span>Drift Findings</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Review outdated, missing, contradictory, or invalid docs.
              </p>
            </div>
          </Link>

          <Link
            to={`/projects/${project.id}/agent`}
            className="p-4 rounded-xl bg-[#0d1322] border border-slate-800/80 hover:border-violet-500/40 transition-all flex items-start gap-4 group"
          >
            <div className="p-2.5 rounded-lg bg-violet-600/10 text-violet-400 border border-violet-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-slate-200 text-sm group-hover:text-violet-300 transition-colors flex items-center justify-between">
                <span>AI Agent & Trace</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Run controlled Gemini agent investigation and inspect tool actions.
              </p>
            </div>
          </Link>

          <Link
            to={`/projects/${project.id}/dependencies`}
            className="p-4 rounded-xl bg-[#0d1322] border border-slate-800/80 hover:border-cyan-500/40 transition-all flex items-start gap-4 group"
          >
            <div className="p-2.5 rounded-lg bg-cyan-600/10 text-cyan-400 border border-cyan-500/20">
              <Network className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-slate-200 text-sm group-hover:text-cyan-300 transition-colors flex items-center justify-between">
                <span>Dependency Graph</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Explore internal imports, external libraries, and cycles.
              </p>
            </div>
          </Link>

          <Link
            to={`/projects/${project.id}/corrections`}
            className="p-4 rounded-xl bg-[#0d1322] border border-slate-800/80 hover:border-emerald-500/40 transition-all flex items-start gap-4 group"
          >
            <div className="p-2.5 rounded-lg bg-emerald-600/10 text-emerald-400 border border-emerald-500/20">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-slate-200 text-sm group-hover:text-emerald-300 transition-colors flex items-center justify-between">
                <span>Proposed Corrections</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Inspect unified diffs generated for detected documentation drift.
              </p>
            </div>
          </Link>

          <Link
            to={`/projects/${project.id}/reports`}
            className="p-4 rounded-xl bg-[#0d1322] border border-slate-800/80 hover:border-slate-500/40 transition-all flex items-start gap-4 group"
          >
            <div className="p-2.5 rounded-lg bg-slate-600/10 text-slate-400 border border-slate-500/20">
              <FileText className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-slate-200 text-sm group-hover:text-slate-300 transition-colors flex items-center justify-between">
                <span>Audit Reports</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Download printable executive PDF summaries and full JSON snapshots.
              </p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
};
