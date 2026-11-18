import React from 'react';
import { useParams } from 'react-router-dom';
import { Upload, FileArchive, FileText, CheckCircle2, AlertCircle, FileCode, HardDrive } from 'lucide-react';
import { api } from '../services/api';
import type { FileInfo } from '../types/api';

export const UploadsPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  // State
  const [zipFile, setZipFile] = React.useState<File | null>(null);
  const [docFiles, setDocFiles] = React.useState<File[]>([]);
  const [uploadingZip, setUploadingZip] = React.useState(false);
  const [uploadingDocs, setUploadingDocs] = React.useState(false);
  const [zipMessage, setZipMessage] = React.useState<string | null>(null);
  const [docsMessage, setDocsMessage] = React.useState<string | null>(null);
  const [zipError, setZipError] = React.useState<string | null>(null);
  const [docsError, setDocsError] = React.useState<string | null>(null);

  // Files in project
  const [projectFiles, setProjectFiles] = React.useState<FileInfo[]>([]);
  const [loadingFiles, setLoadingFiles] = React.useState(true);

  const loadFiles = React.useCallback(async () => {
    if (!projectId) return;
    try {
      setLoadingFiles(true);
      const res = await api.getProjectFiles(projectId);
      setProjectFiles(res.files);
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

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Project Uploads</h1>
        <p className="text-xs text-slate-400 mt-1">
          Upload repository source archives (.zip) and documentation documents (.pdf, .md).
        </p>
      </div>

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
                    Multi-file upload supported &bull; PyMuPDF parsed
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
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {projectFiles.map((file, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 px-3 text-slate-200 flex items-center gap-2">
                      <FileCode className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span>{file.rel_path}</span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-sans font-medium uppercase tracking-wider bg-slate-800 text-slate-400">
                        {file.category}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">{file.language || '—'}</td>
                    <td className="py-2.5 px-3 text-right text-slate-500">
                      {(file.size_bytes / 1024).toFixed(1)} KB
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
