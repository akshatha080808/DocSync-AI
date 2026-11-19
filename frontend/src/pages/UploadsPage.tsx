import React from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Upload,
  FileArchive,
  FileText,
  CheckCircle2,
  AlertCircle,
  FileCode,
  HardDrive,
  GitFork,
  RefreshCw,
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import type { FileInfo, ProjectDetail } from '../types/api';

export const UploadsPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  // State
  const [project, setProject] = React.useState<ProjectDetail | null>(null);
  const [zipFile, setZipFile] = React.useState<File | null>(null);
  const [docFiles, setDocFiles] = React.useState<File[]>([]);
  const [uploadingZip, setUploadingZip] = React.useState(false);
  const [uploadingDocs, setUploadingDocs] = React.useState(false);
  const [zipMessage, setZipMessage] = React.useState<string | null>(null);
  const [docsMessage, setDocsMessage] = React.useState<string | null>(null);
  const [zipError, setZipError] = React.useState<string | null>(null);
  const [docsError, setDocsError] = React.useState<string | null>(null);

  // Deletion modal & action state
  const [fileToDelete, setFileToDelete] = React.useState<string | null>(null);
  const [deletingFile, setDeletingFile] = React.useState(false);
  const [actionMessage, setActionMessage] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);

  // Files in project
  const [projectFiles, setProjectFiles] = React.useState<FileInfo[]>([]);
  const [loadingFiles, setLoadingFiles] = React.useState(true);

  const loadFiles = React.useCallback(async () => {
    if (!projectId) return;
    try {
      setLoadingFiles(true);
      const [res, proj] = await Promise.all([
        api.getProjectFiles(projectId),
        api.getProject(projectId).catch(() => null),
      ]);
      setProjectFiles(res.files);
      if (proj) setProject(proj);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingFiles(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  const handleZipUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !zipFile) return;

    try {
      setUploadingZip(true);
      setZipError(null);
      setZipMessage(null);
      setActionMessage(null);
      const res = await api.uploadZip(projectId, zipFile);
      setZipMessage(res.message);
      setZipFile(null);
      await loadFiles();
    } catch (err: any) {
      setZipError(err?.response?.data?.detail || err.message || 'ZIP upload rejected.');
    } finally {
      setUploadingZip(false);
    }
  };

  const handleDocsUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || docFiles.length === 0) return;

    try {
      setUploadingDocs(true);
      setDocsError(null);
      setDocsMessage(null);
      setActionMessage(null);
      const res = await api.uploadDocuments(projectId, docFiles);
      setDocsMessage(res.message);
      setDocFiles([]);
      await loadFiles();
    } catch (err: any) {
      setDocsError(err?.response?.data?.detail || err.message || 'Document upload rejected.');
    } finally {
      setUploadingDocs(false);
    }
  };

  const handleDeleteDocument = async () => {
    if (!projectId || !fileToDelete) return;

    try {
      setDeletingFile(true);
      setActionError(null);
      const res = await api.deleteDocument(projectId, fileToDelete);
      setActionMessage(res.message);
      setTimeout(() => setActionMessage(null), 5000);
      setFileToDelete(null);
      await loadFiles();
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || err.message || 'Failed to delete documentation file.');
    } finally {
      setDeletingFile(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Project Uploads</h1>
        <p className="text-xs text-slate-400 mt-1">
          Upload repository source archives (.zip) and documentation documents (.pdf, .md, .txt).
        </p>
      </div>

      {/* Global Success Feedback Banner */}
      {actionMessage && (
        <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between gap-3 text-emerald-400 text-xs">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-emerald-400 hover:text-emerald-300 font-bold ml-2"
          >
            &times;
          </button>
        </div>
      )}

      {/* Global Error Feedback Banner */}
      {actionError && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center justify-between gap-3 text-rose-400 text-xs">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-rose-400 hover:text-rose-300 font-bold ml-2"
          >
            &times;
          </button>
        </div>
      )}

      {project?.audit_mode === 'github' && (
        <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/30 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-600/20 text-purple-400 border border-purple-500/30">
              <GitFork className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-semibold text-purple-200">
                Mode 2: GitHub Repository Connected
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">
                This project is synchronized with <span className="font-mono text-purple-300">{project.github_repo || 'GitHub'}</span> on branch <span className="font-mono text-purple-300">{project.github_branch || 'main'}</span>. You can trigger syncs directly on the Overview page or optionally upload supplemental documentation files below.
              </div>
            </div>
          </div>
          <Link
            to={`/projects/${projectId}`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Go to Sync</span>
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ZIP Upload Card */}
        <div className="p-6 rounded-xl bg-[#0d1322] border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-lg bg-indigo-600/10 text-indigo-400 border border-indigo-500/20">
                <FileArchive className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Source Repository Archive</h2>
                <p className="text-[11px] text-slate-500">ZIP archive containing Python or JavaScript code</p>
              </div>
            </div>

            <form onSubmit={handleZipUpload} className="space-y-4">
              <div className="border-2 border-dashed border-slate-700/80 rounded-lg p-6 text-center hover:border-indigo-500/50 transition-colors">
                <input
                  type="file"
                  accept=".zip"
                  onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                  className="hidden"
                  id="zip-upload-input"
                />
                <label htmlFor="zip-upload-input" className="cursor-pointer block">
                  <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                  <span className="text-xs text-slate-300 font-medium block">
                    {zipFile ? zipFile.name : 'Click to select .zip repository archive'}
                  </span>
                  <span className="text-[11px] text-slate-500 block mt-1">
                    Protected by Zip Slip defense & 40 MB max limit
                  </span>
                </label>
              </div>

              {zipError && (
                <div className="p-3 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{zipError}</span>
                </div>
              )}

              {zipMessage && (
                <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{zipMessage}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={!zipFile || uploadingZip}
                className="w-full py-2.5 px-4 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors disabled:opacity-40"
              >
                {uploadingZip ? 'Extracting Safely...' : 'Upload & Unpack Archive'}
              </button>
            </form>
          </div>
        </div>

        {/* Documentation Upload Card */}
        <div className="p-6 rounded-xl bg-[#0d1322] border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-lg bg-amber-600/10 text-amber-400 border border-amber-500/20">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Documentation Documents</h2>
                <p className="text-[11px] text-slate-500">PDF manuals, API specs, Markdown guides</p>
              </div>
            </div>

            <form onSubmit={handleDocsUpload} className="space-y-4">
              <div className="border-2 border-dashed border-slate-700/80 rounded-lg p-6 text-center hover:border-amber-500/50 transition-colors">
                <input
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt,.rst"
                  onChange={(e) => setDocFiles(Array.from(e.target.files || []))}
                  className="hidden"
                  id="docs-upload-input"
                />
                <label htmlFor="docs-upload-input" className="cursor-pointer block">
                  <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                  <span className="text-xs text-slate-300 font-medium block">
                    {docFiles.length > 0
                      ? `${docFiles.length} file(s) selected`
                      : 'Click to select PDF or Markdown files'}
                  </span>
                  <span className="text-[11px] text-slate-500 block mt-1">
                    Multi-file upload supported &bull; PyMuPDF & Markdown parsed
                  </span>
                </label>
              </div>

              {docsError && (
                <div className="p-3 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{docsError}</span>
                </div>
              )}

              {docsMessage && (
                <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{docsMessage}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={docFiles.length === 0 || uploadingDocs}
                className="w-full py-2.5 px-4 rounded-md bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium transition-colors disabled:opacity-40"
              >
                {uploadingDocs ? 'Uploading Documents...' : 'Upload Documentation Files'}
              </button>
            </form>

            {/* List of active documentation files in this project with individual delete buttons */}
            {project?.document_names && project.document_names.length > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-800/80 space-y-2">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Uploaded Documents ({project.document_names.length})
                </span>
                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {project.document_names.map((docName) => (
                    <div
                      key={docName}
                      className="flex items-center justify-between p-2 rounded-md bg-slate-900/60 border border-slate-800 text-xs"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <FileText className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        <span className="font-mono text-slate-200 truncate">{docName}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setFileToDelete(docName)}
                        className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors shrink-0 ml-2"
                        title={`Delete ${docName}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Uploaded Files Table */}
      <div className="p-6 rounded-xl bg-[#0d1322] border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">Files In Project Workspace</h2>
            <p className="text-xs text-slate-500">
              Preserved in isolated directory &bull; Server paths sanitized
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">{projectFiles.length} total files</span>
        </div>

        {loadingFiles ? (
          <div className="text-xs text-slate-500 py-6 text-center">Loading files...</div>
        ) : projectFiles.length === 0 ? (
          <div className="text-xs text-slate-500 py-8 text-center border border-dashed border-slate-800 rounded-lg">
            No files in project yet. Upload a source archive or documentation above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-500 bg-slate-900/40">
                <tr>
                  <th className="py-2.5 px-3">Path</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Language</th>
                  <th className="py-2.5 px-3 text-right">Size</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {projectFiles.map((file, idx) => {
                  const isDeletableDoc =
                    file.category === 'documentation' && file.rel_path.startsWith('documents/');
                  const docFilename = isDeletableDoc
                    ? file.rel_path.replace(/^documents\//, '')
                    : null;

                  return (
                    <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-2.5 px-3 text-slate-200 flex items-center gap-2">
                        {isDeletableDoc ? (
                          <FileText className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        ) : (
                          <FileCode className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        )}
                        <span>{file.rel_path}</span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-sans font-medium uppercase tracking-wider ${
                            file.category === 'documentation'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {file.category}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">{file.language || '—'}</td>
                      <td className="py-2.5 px-3 text-right text-slate-500">
                        {(file.size_bytes / 1024).toFixed(1)} KB
                      </td>
                      <td className="py-2.5 px-3 text-right font-sans">
                        {isDeletableDoc && docFilename ? (
                          <button
                            type="button"
                            onClick={() => setFileToDelete(docFilename)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors text-xs"
                            title={`Delete documentation file ${docFilename}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>Delete</span>
                          </button>
                        ) : (
                          <span className="text-slate-600 text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Documentation Confirmation Modal */}
      {fileToDelete && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-rose-500/30 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400 mb-3">
              <AlertTriangle className="w-6 h-6" />
              <h2 className="text-lg font-bold text-slate-100">Delete Documentation File</h2>
            </div>
            <p className="text-xs text-slate-300 mb-3">
              Are you sure you want to delete <span className="font-semibold text-white font-mono">"{fileToDelete}"</span>?
            </p>
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-300 text-xs mb-5 space-y-1">
              <div>&bull; The documentation file will be permanently deleted from the project.</div>
              <div>&bull; Previous audit analysis results that relied on this document will be invalidated.</div>
              <div>&bull; You can upload an updated version with the same filename at any time.</div>
            </div>
            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                disabled={deletingFile}
                onClick={() => setFileToDelete(null)}
                className="px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deletingFile}
                onClick={handleDeleteDocument}
                className="flex items-center gap-2 px-4 py-2 text-xs font-medium bg-rose-600 hover:bg-rose-500 text-white rounded-md transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                {deletingFile ? 'Deleting...' : 'Delete File'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
