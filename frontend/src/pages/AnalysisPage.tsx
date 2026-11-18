import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { Cpu, Play, CheckCircle2, AlertCircle, FileCode, Layers, ShieldCheck, ArrowRight, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import type { AnalysisResult } from '../types/api';

export const AnalysisPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [analysis, setAnalysis] = React.useState<AnalysisResult | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [analyzing, setAnalyzing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const loadAnalysis = React.useCallback(async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.getAnalysis(projectId);
      setAnalysis(res);
    } catch (err: any) {
      if (err?.response?.status === 422 || err?.response?.status === 404) {
        setAnalysis(null);
      } else {
        setError(err?.response?.data?.detail || err.message || 'Failed to fetch analysis.');
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    loadAnalysis();
  }, [loadAnalysis]);

  const handleRunAnalysis = async () => {
    if (!projectId) return;
    try {
      setAnalyzing(true);
      setError(null);
      const res = await api.triggerAnalysis(projectId);
      setAnalysis(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Deterministic analysis failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Top Banner */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Deterministic Codebase Analysis</h1>
          <p className="text-xs text-slate-400 mt-1">
            Python AST & JS Tree-sitter parsing &bull; Never executes untrusted code.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadAnalysis}
            className="p-2 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleRunAnalysis}
            disabled={analyzing}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-sm transition-colors disabled:opacity-40"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{analyzing ? 'Analyzing Codebase...' : 'Run Analysis Pipeline'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && !analysis ? (
        <div className="text-xs text-slate-500 py-12 text-center">Loading analysis results...</div>
      ) : !analysis ? (
        <div className="p-12 text-center rounded-xl bg-[#0b101b] border border-dashed border-slate-800 space-y-3">
          <Cpu className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-300">No Analysis Results Found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Upload your source repository in Uploads and click "Run Analysis Pipeline" to parse code facts.
          </p>
          <button
            onClick={handleRunAnalysis}
            disabled={analyzing}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Run Pipeline</span>
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Summary Metric Strip */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800">
              <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Parsed Files</span>
              <span className="text-2xl font-bold text-slate-100 mt-1 block">
                {analysis.summary.source_files_count}
              </span>
            </div>
            <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800">
              <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Functions</span>
              <span className="text-2xl font-bold text-indigo-400 mt-1 block">
                {analysis.summary.total_functions}
              </span>
            </div>
            <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800">
              <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Classes</span>
              <span className="text-2xl font-bold text-emerald-400 mt-1 block">
                {analysis.summary.total_classes}
              </span>
            </div>
            <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800">
              <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Lines of Code</span>
              <span className="text-2xl font-bold text-amber-400 mt-1 block">
                {analysis.summary.total_loc}
              </span>
            </div>
            <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800">
              <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Config Files</span>
              <span className="text-2xl font-bold text-sky-400 mt-1 block">
                {analysis.summary.configuration_files_count}
              </span>
            </div>
          </div>

          {/* Parsed Functions and Classes Details */}
          <div className="p-6 rounded-xl bg-[#0d1322] border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Extracted Source Symbols</h2>
                <p className="text-xs text-slate-500">
                  Deterministic AST facts &bull; Signatures, parameters, and async properties
                </p>
              </div>
              <Link
                to={`/projects/${projectId}/findings`}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
              >
                <span>View Drift Findings</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-3">
              {analysis.source_files.map((sf, idx) => (
                <div key={idx} className="p-4 rounded-lg bg-[#0b101b] border border-slate-800/80 space-y-3">
                  <div className="flex items-center justify-between text-xs border-b border-slate-800/60 pb-2">
                    <div className="flex items-center gap-2 text-slate-200 font-mono font-medium">
                      <FileCode className="w-4 h-4 text-indigo-400" />
                      <span>{sf.file_path}</span>
                    </div>
                    <span className="text-[11px] text-slate-500 font-mono">
                      {sf.language} &bull; {sf.loc} LOC
                    </span>
                  </div>

                  {/* Functions in this file */}
                  {sf.functions.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider">
                        Functions:
                      </span>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {sf.functions.map((fn, fIdx) => (
                          <div
                            key={fIdx}
                            className="p-2.5 rounded bg-slate-900/80 border border-slate-800 font-mono text-[11px] flex flex-col justify-between"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-indigo-300 font-medium">{fn.name}()</span>
                              {fn.is_async && (
                                <span className="px-1.5 py-0.2 rounded text-[9px] font-sans bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                                  async
                                </span>
                              )}
                            </div>
                            <div className="text-[10px] text-slate-500 mt-1 truncate">
                              Params: ({fn.parameters.map((p) => p.name).join(', ') || 'none'})
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Classes in this file */}
                  {sf.classes.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <span className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider">
                        Classes:
                      </span>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {sf.classes.map((cls, cIdx) => (
                          <div
                            key={cIdx}
                            className="p-2.5 rounded bg-slate-900/80 border border-slate-800 font-mono text-[11px]"
                          >
                            <span className="text-emerald-300 font-medium">class {cls.name}</span>
                            <div className="text-[10px] text-slate-500 mt-1">
                              Methods: {cls.methods.map((m) => m.name).join(', ') || 'none'}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
