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
  GitFork,
  GitBranch,
  RefreshCw,
  GitCommit,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Clock,
  Archive,
  Key,
} from 'lucide-react';
import { api } from '../services/api';
import type {
  ProjectDetail,
  GitHubRepoStatus,
  GitHubBranchInfo,
  GitHubCommitHistoryItem,
  GitHubSyncResponse,
} from '../types/api';

export const OverviewPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = React.useState<ProjectDetail | null>(null);
  const [loading, setLoading] = React.useState(true);

  // GitHub Mode 2 states
  const [githubStatus, setGithubStatus] = React.useState<GitHubRepoStatus | null>(null);
  const [branches, setBranches] = React.useState<GitHubBranchInfo[]>([]);
  const [selectedBranch, setSelectedBranch] = React.useState<string>('');
  const [history, setHistory] = React.useState<GitHubCommitHistoryItem[]>([]);
  const [syncing, setSyncing] = React.useState(false);
  const [syncResult, setSyncResult] = React.useState<GitHubSyncResponse | null>(null);
  const [syncError, setSyncError] = React.useState<string | null>(null);

  // Connect GitHub modal (for upgrading Mode 1 or changing repo)
  const [isConnectModalOpen, setIsConnectModalOpen] = React.useState(false);
  const [connectUrl, setConnectUrl] = React.useState('');
  const [connectBranch, setConnectBranch] = React.useState('');
  const [connectToken, setConnectToken] = React.useState('');
  const [connecting, setConnecting] = React.useState(false);

  const loadProjectData = React.useCallback(async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      const proj = await api.getProject(projectId);
      setProject(proj);

      if (proj.audit_mode === 'github') {
        try {
          const [statusData, branchesData, historyData] = await Promise.all([
            api.getGitHubStatus(projectId),
            api.getGitHubBranches(projectId).catch(() => []),
            api.getGitHubHistory(projectId).catch(() => []),
          ]);
          setGithubStatus(statusData);
          setBranches(branchesData);
          setHistory(historyData);
          if (statusData.branch) {
            setSelectedBranch(statusData.branch);
          }
        } catch (ghErr) {
          console.warn('Failed to fetch some GitHub details:', ghErr);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    loadProjectData();
  }, [loadProjectData]);

  const handleSyncNow = async () => {
    if (!projectId) return;
    try {
      setSyncing(true);
      setSyncError(null);
      setSyncResult(null);

      // If GitHub mode is active but not yet connected on the backend, connect first
      if (isGitHubMode && (!githubStatus || !githubStatus.connected) && project.github_repo) {
        await api.connectGitHub(projectId, {
          repo_url: project.github_repo,
          branch: selectedBranch || project.github_branch || undefined,
        });
      }

      const res = await api.syncGitHub(projectId, selectedBranch || undefined);
      setSyncResult(res);

      // Refresh project status and history
      const [proj, statusData, historyData] = await Promise.all([
        api.getProject(projectId),
        api.getGitHubStatus(projectId).catch(() => null),
        api.getGitHubHistory(projectId).catch(() => []),
      ]);
      setProject(proj);
      if (statusData) setGithubStatus(statusData);
      setHistory(historyData);
    } catch (err: any) {
      setSyncError(err?.response?.data?.detail || err.message || 'GitHub synchronization failed.');
    } finally {
      setSyncing(false);
    }
  };

  const handleBranchChange = async (newBranch: string) => {
    setSelectedBranch(newBranch);
    if (!projectId || !newBranch) return;
    try {
      setSyncing(true);
      setSyncError(null);
      setSyncResult(null);
      const res = await api.syncGitHub(projectId, newBranch);
      setSyncResult(res);
      await loadProjectData();
    } catch (err: any) {
      setSyncError(err?.response?.data?.detail || err.message || 'Branch switch sync failed.');
    } finally {
      setSyncing(false);
    }
  };

  const handleConnectRepo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !connectUrl.trim()) return;

    try {
      setConnecting(true);
      setSyncError(null);
      await api.connectGitHub(projectId, {
        repo_url: connectUrl.trim(),
        branch: connectBranch.trim() || undefined,
        github_token: connectToken.trim() || undefined,
      });
      setIsConnectModalOpen(false);
      setConnectUrl('');
      setConnectBranch('');
      setConnectToken('');
      await loadProjectData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to connect GitHub repository.');
    } finally {
      setConnecting(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-sm text-slate-400">Loading project overview...</div>;
  }

  if (!project) {
    return <div className="p-8 text-sm text-rose-400">Project not found.</div>;
  }

  const isGitHubMode = project.audit_mode === 'github';

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header Info */}
      <div className="p-6 rounded-xl bg-[#0d1322] border border-slate-800 flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-slate-100">{project.name}</h1>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wider flex items-center gap-1 ${
                isGitHubMode
                  ? githubStatus?.connected
                    ? 'bg-purple-500/10 text-purple-300 border border-purple-500/30'
                    : 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
                  : 'bg-slate-700/20 text-slate-400 border border-slate-700/40'
              }`}
            >
              {isGitHubMode ? (
                <>
                  <GitFork className="w-3 h-3 text-purple-400" />
                  {githubStatus?.connected ? 'Mode 2: GitHub Connected' : 'Mode 2: GitHub (Not Connected)'}
                </>
              ) : (
                <>
                  <Archive className="w-3 h-3 text-slate-400" />
                  Mode 1: ZIP Upload
                </>
              )}
            </span>
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
          <div className="flex items-center gap-6 text-[11px] text-slate-500 mt-4 font-mono flex-wrap">
            <span>Project ID: {project.id}</span>
            <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
            <span>Updated: {new Date(project.updated_at).toLocaleDateString()}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isGitHubMode ? (
            <button
              onClick={handleSyncNow}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 rounded-md bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold shadow-sm transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
              <span>
                {syncing
                  ? (githubStatus?.connected ? 'Syncing Repository...' : 'Connecting & Syncing...')
                  : (githubStatus?.connected ? 'Sync Now' : 'Connect & Sync')}
              </span>
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsConnectModalOpen(true)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-md bg-purple-600/10 border border-purple-500/30 hover:bg-purple-600/20 text-purple-300 text-xs font-medium transition-colors"
                title="Connect this project to GitHub (Mode 2)"
              >
                <GitFork className="w-3.5 h-3.5" />
                <span>Connect GitHub</span>
              </button>
              <Link
                to={`/projects/${project.id}/uploads`}
                className="flex items-center gap-2 px-3.5 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Upload Files</span>
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Mode 2: GitHub Repository Status Banner */}
      {isGitHubMode && (
        <div className="p-5 rounded-xl bg-[#0e1628] border border-purple-500/30 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-purple-600/20 text-purple-400 border border-purple-500/30">
                <GitFork className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-bold text-slate-100 font-mono">
                    {project.github_repo || githubStatus?.owner + '/' + githubStatus?.repo_name || 'Connected Repository'}
                  </h3>
                  {githubStatus?.repo_url && (
                    <a
                      href={githubStatus.repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-purple-400 hover:text-purple-300 transition-colors"
                      title="Open repository on GitHub"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                  {githubStatus?.is_private && (
                    <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 border border-amber-500/30 text-amber-400">
                      Private Repo
                    </span>
                  )}
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-medium border ${
                      githubStatus?.connected
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                        : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                    }`}
                  >
                    {githubStatus?.connected ? 'Connected' : 'Not Connected'}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs text-slate-400 mt-1 flex-wrap">
                  <span className="flex items-center gap-1 font-mono">
                    <GitCommit className="w-3 h-3 text-purple-400" />
                    Commit: {project.latest_commit_sha ? project.latest_commit_sha.slice(0, 8) : 'Not analyzed'}
                  </span>
                  {githubStatus?.last_synced_at && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      Last Synced: {new Date(githubStatus.last_synced_at).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Branch Switcher & Drift Status Badge */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-700/80 rounded-md px-2.5 py-1 text-xs">
                <GitBranch className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-slate-400">Branch:</span>
                {branches.length > 0 ? (
                  <select
                    value={selectedBranch || project.github_branch || 'main'}
                    onChange={(e) => handleBranchChange(e.target.value)}
                    disabled={syncing}
                    className="bg-transparent text-slate-200 font-mono text-xs focus:outline-none cursor-pointer"
                  >
                    {branches.map((b) => (
                      <option key={b.name} value={b.name} className="bg-slate-900 text-slate-200">
                        {b.name} {b.is_default ? '(default)' : ''}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="font-mono text-purple-300">{project.github_branch || 'main'}</span>
                )}
              </div>

              {/* Status Badge */}
              <span
                className={`px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 ${
                  project.drift_status === 'DRIFT_DETECTED'
                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                    : project.drift_status === 'CHANGES_DETECTED'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    : project.drift_status === 'UP_TO_DATE' || project.drift_status === 'ANALYSIS_COMPLETED'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : 'bg-slate-700/20 text-slate-400 border border-slate-700/30'
                }`}
              >
                {project.drift_status === 'DRIFT_DETECTED' ? (
                  <AlertTriangle className="w-3.5 h-3.5" />
                ) : project.drift_status === 'UP_TO_DATE' || project.drift_status === 'ANALYSIS_COMPLETED' ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5" />
                )}
                {project.drift_status || 'NEVER_SYNCED'}
              </span>
            </div>
          </div>

          {/* Sync Success Feedback */}
          {syncResult && (
            <div className="p-3.5 rounded-lg bg-emerald-950/20 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{syncResult.message}</span>
              </div>
              <div className="flex items-center gap-3 font-mono text-[11px] text-emerald-400/90">
                {syncResult.files_changed && syncResult.files_changed.length > 0 && (
                  <span>Files: {syncResult.files_changed.length} ({syncResult.doc_changes.length} docs, {syncResult.code_changes.length} code)</span>
                )}
                <span>Findings: {syncResult.drift_findings_count}</span>
              </div>
            </div>
          )}

          {/* Sync Error Feedback */}
          {syncError && (
            <div className="p-3.5 rounded-lg bg-rose-950/20 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{syncError}</span>
            </div>
          )}
        </div>
      )}

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

      {/* Mode 2: Commit & Synchronization Audit History Table */}
      {isGitHubMode && history.length > 0 && (
        <div className="p-5 rounded-xl bg-[#0d1322] border border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <GitCommit className="w-4 h-4 text-purple-400" />
              <span>Commit & Synchronization History</span>
            </h2>
            <span className="text-xs text-slate-500 font-mono">{history.length} sync checkpoints</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/60 text-slate-400 text-[11px] uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Commit SHA</th>
                  <th className="py-2.5 px-3">Message & Author</th>
                  <th className="py-2.5 px-3">Changes</th>
                  <th className="py-2.5 px-3">Drift Findings</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Synchronized</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {history.map((h, idx) => (
                  <tr key={`${h.commit_sha}-${idx}`} className="hover:bg-slate-800/20 transition-colors font-mono">
                    <td className="py-2.5 px-3 font-semibold text-purple-400">
                      {h.commit_sha ? h.commit_sha.slice(0, 8) : 'HEAD'}
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <div className="text-slate-200 font-medium line-clamp-1">{h.message || 'No commit message'}</div>
                      <div className="text-[10px] text-slate-500">{h.author || 'Author unavailable'}</div>
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                          {h.files_changed ? h.files_changed.length : 0} files
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          {h.doc_changes_count} doc
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          {h.code_changes_count} code
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        h.findings_detected_count > 0 ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-emerald-500/10 text-emerald-400'
                      }`}>
                        {h.findings_detected_count} findings
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-slate-800 text-slate-300">
                        {h.sync_status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px] font-sans">
                      {new Date(h.synced_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

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

      {/* Connect GitHub Modal (for Mode 1 projects) */}
      {isConnectModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-purple-500/30 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center gap-2 text-purple-400 mb-2">
              <GitFork className="w-5 h-5" />
              <h2 className="text-lg font-bold text-slate-100">Connect GitHub Repository</h2>
            </div>
            <p className="text-xs text-slate-400 mb-5">
              Connect this workspace to a remote Git repository to enable automated change tracking and multi-file drift detection.
            </p>

            <form onSubmit={handleConnectRepo} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Repository URL <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="https://github.com/owner/repo or owner/repo"
                  value={connectUrl}
                  onChange={(e) => setConnectUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-md text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Branch (optional)</label>
                <input
                  type="text"
                  placeholder="main (auto-detected if empty)"
                  value={connectBranch}
                  onChange={(e) => setConnectBranch(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-md text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">
                  <Key className="w-3.5 h-3.5 text-amber-400" />
                  <span>Personal Access Token (optional)</span>
                </label>
                <input
                  type="password"
                  placeholder="ghp_... for private repositories"
                  value={connectToken}
                  onChange={(e) => setConnectToken(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-md text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500 font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Stored securely and used solely for authenticating GitHub API requests.
                </p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsConnectModalOpen(false)}
                  className="px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={connecting}
                  className="px-4 py-2 text-xs font-medium bg-purple-600 hover:bg-purple-500 text-white rounded-md transition-colors disabled:opacity-50"
                >
                  {connecting ? 'Connecting...' : 'Connect Repository'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
