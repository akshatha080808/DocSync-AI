import React from 'react';
import { Link } from 'react-router-dom';
import { Plus, FolderGit2, Calendar, FileText, ArrowRight, Layers, AlertCircle, RefreshCw, Trash2, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import type { ProjectSummary } from '../types/api';

export const DashboardPage: React.FC = () => {
  const [projects, setProjects] = React.useState<ProjectSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [successMessage, setSuccessMessage] = React.useState<string | null>(null);

  // New project modal state
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [newProjectName, setNewProjectName] = React.useState('');
  const [newProjectDesc, setNewProjectDesc] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);

  // Delete project modal state
  const [projectToDelete, setProjectToDelete] = React.useState<ProjectSummary | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listProjects();
      setProjects(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load projects.');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    loadProjects();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;

    try {
      setSubmitting(true);
      await api.createProject({
        name: newProjectName.trim(),
        description: newProjectDesc.trim() || undefined,
      });
      setIsModalOpen(false);
      setNewProjectName('');
      setNewProjectDesc('');
      await loadProjects();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to create project.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!projectToDelete) return;

    try {
      setDeleting(true);
      setError(null);
      await api.deleteProject(projectToDelete.id);
      setProjects((prev) => prev.filter((p) => p.id !== projectToDelete.id));
      setSuccessMessage(`Project "${projectToDelete.name}" was permanently deleted.`);
      setTimeout(() => setSuccessMessage(null), 4000);
      setProjectToDelete(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to delete project.');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Top Banner */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Project Workspaces</h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic codebase analysis & documentation drift detection management.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadProjects}
            className="p-2 rounded-md bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 transition-colors border border-slate-700/60"
            title="Refresh projects"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Project
          </button>
        </div>
      </div>

      {/* Success Banner */}
      {successMessage && (
        <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-emerald-400 text-sm">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center gap-3 text-rose-400 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading Skeleton / Empty State / Projects Grid */}
      {loading && projects.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 rounded-xl bg-slate-900/60 border border-slate-800/60 animate-pulse p-5 space-y-4" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 px-4 rounded-xl border border-dashed border-slate-800 bg-[#0b101b]/40">
          <FolderGit2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No projects yet</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto mt-1 mb-5">
            Create your first workspace to start uploading repository code and detecting documentation drift.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Workspace
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((proj) => (
            <Link
              key={proj.id}
              to={`/projects/${proj.id}`}
              className="group flex flex-col justify-between p-5 rounded-xl bg-[#0d1322] border border-slate-800/80 hover:border-indigo-500/50 hover:bg-[#10172a] transition-all shadow-sm"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="w-9 h-9 rounded-lg bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <FolderGit2 className="w-5 h-5" />
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                      proj.analysis_status === 'completed'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : proj.has_source
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        : 'bg-slate-700/20 text-slate-400 border border-slate-700/40'
                    }`}
                  >
                    {proj.analysis_status}
                  </span>
                </div>
                <h3 className="font-semibold text-slate-100 text-base group-hover:text-indigo-300 transition-colors">
                  {proj.name}
                </h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                  {proj.description || 'No description provided.'}
                </p>
              </div>

              <div className="pt-4 mt-4 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
                <div className="flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{new Date(proj.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setProjectToDelete(proj);
                    }}
                    className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                    title="Delete Project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <div className="flex items-center gap-1 text-slate-400 group-hover:text-indigo-400 font-medium transition-colors">
                    <span>Open</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-lg font-bold text-slate-100 mb-1">Create Workspace</h2>
            <p className="text-xs text-slate-400 mb-5">
              Set up a project space to isolate codebase files and drift detection audits.
            </p>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Project Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. DocSync Payment Service"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-md text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Description (optional)</label>
                <textarea
                  rows={3}
                  placeholder="Repository purpose and documentation targets..."
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700/80 rounded-md text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-md transition-colors disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Workspace'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Project Confirmation Modal */}
      {projectToDelete && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-rose-500/30 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400 mb-3">
              <AlertTriangle className="w-6 h-6" />
              <h2 className="text-lg font-bold text-slate-100">Delete Project</h2>
            </div>
            <p className="text-xs text-slate-300 mb-3">
              Are you sure you want to delete <span className="font-semibold text-white">"{projectToDelete.name}"</span>?
            </p>
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-300 text-xs mb-5">
              Warning: This action is permanent and will completely remove all uploaded codebase files, documentation, analysis results, and generated reports for this project.
            </div>
            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                disabled={deleting}
                onClick={() => setProjectToDelete(null)}
                className="px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={handleDeleteProject}
                className="flex items-center gap-2 px-4 py-2 text-xs font-medium bg-rose-600 hover:bg-rose-500 text-white rounded-md transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                {deleting ? 'Deleting...' : 'Delete Project Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
