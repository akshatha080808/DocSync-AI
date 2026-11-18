import React, { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import type { DocumentationCorrection, ProjectCorrectionsResponse } from '../types/api';
import {
  FileEdit,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  Search,
  RefreshCw,
  FileText,
  ShieldCheck,
  ArrowRight,
  ExternalLink,
  Layers,
  Sparkles,
} from 'lucide-react';

export const CorrectionsPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [corrections, setCorrections] = useState<DocumentationCorrection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCorrectionId, setSelectedCorrectionId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchCorrections = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data: ProjectCorrectionsResponse = await api.getCorrections(projectId);
      setCorrections(data.corrections || []);
      if (data.corrections?.length > 0 && !selectedCorrectionId) {
        setSelectedCorrectionId(data.corrections[0].correction_id);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load documentation corrections. Run Agent Investigation first.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCorrections();
  }, [projectId]);

  const filteredCorrections = useMemo(() => {
    return corrections.filter(c => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        c.file_path.toLowerCase().includes(q) ||
        (c.section_name && c.section_name.toLowerCase().includes(q)) ||
        c.reason.toLowerCase().includes(q)
      );
    });
  }, [corrections, searchQuery]);

  const selectedCorrection = useMemo(() => {
    return corrections.find(c => c.correction_id === selectedCorrectionId) || filteredCorrections[0] || null;
  }, [corrections, selectedCorrectionId, filteredCorrections]);

  const handleCopyDiff = (diffText: string, id: string) => {
    navigator.clipboard.writeText(diffText);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Render unified diff lines with syntax highlighting
  const renderDiffLines = (diff: string) => {
    const lines = diff.split('\n');
    return (
      <div className="font-mono text-xs leading-relaxed overflow-x-auto p-4 bg-slate-950 rounded-lg border border-slate-800 selection:bg-indigo-900">
        {lines.map((line, idx) => {
          let lineClass = 'text-slate-400';
          let bgClass = 'hover:bg-slate-900/50';

          if (line.startsWith('---') || line.startsWith('+++')) {
            lineClass = 'text-slate-500 font-semibold';
          } else if (line.startsWith('@@')) {
            lineClass = 'text-indigo-400 font-bold';
            bgClass = 'bg-indigo-950/30';
          } else if (line.startsWith('-')) {
            lineClass = 'text-rose-300';
            bgClass = 'bg-rose-950/40 border-l-2 border-rose-500 pl-2';
          } else if (line.startsWith('+')) {
            lineClass = 'text-emerald-300';
            bgClass = 'bg-emerald-950/40 border-l-2 border-emerald-500 pl-2';
          }

          return (
            <div key={idx} className={`py-0.5 px-2 flex items-start gap-3 transition-colors ${bgClass}`}>
              <span className="text-[10px] text-slate-600 select-none w-6 text-right shrink-0">{idx + 1}</span>
              <span className={`${lineClass} whitespace-pre-wrap break-all`}>{line}</span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <FileEdit className="w-6 h-6 text-indigo-400" />
            Proposed Documentation Corrections
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Agent-synthesized unified diff patches aligned with verified codebase truth. Non-destructive previews ready for review.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchCorrections}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700/60 font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Non-destructive safety banner */}
      <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-800/40 flex items-start gap-3.5">
        <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="text-xs text-indigo-200/90 leading-relaxed">
          <span className="font-semibold text-white">Strict Non-Destructive Guarantee:</span> DocSync AI never automatically overwrites your repository's original documentation.
          All corrections are presented as standard unified diffs (<span className="font-mono text-indigo-300">patch</span> format) that you can copy, inspect, or apply via Git.
        </div>
      </div>

      {/* Main Layout: List + Diff Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
        {/* Left Column: Corrections Navigation List */}
        <div className="lg:col-span-5 flex flex-col space-y-4">
          {/* Search filter */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search by file or reason..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* List Cards */}
          <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-1">
            {loading ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-500 mb-2" />
                Loading corrections...
              </div>
            ) : filteredCorrections.length === 0 ? (
              <div className="p-8 text-center bg-slate-900 rounded-xl border border-slate-800 text-slate-400">
                <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-sm font-medium text-slate-300">No corrections available</p>
                <p className="text-xs text-slate-500 mt-1">
                  Run the AI Agent Investigation to generate unified diff corrections for identified drift findings.
                </p>
                <Link
                  to={`/projects/${projectId}/agent`}
                  className="inline-flex items-center gap-1.5 mt-4 px-3.5 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors font-medium"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Run AI Agent
                </Link>
              </div>
            ) : (
              filteredCorrections.map(c => {
                const isSelected = selectedCorrection?.correction_id === c.correction_id;
                return (
                  <div
                    key={c.correction_id}
                    onClick={() => setSelectedCorrectionId(c.correction_id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-slate-800/90 border-indigo-500 ring-1 ring-indigo-500/40 text-white shadow-lg'
                        : 'bg-slate-900/80 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="font-mono text-xs font-semibold truncate text-indigo-300" title={c.file_path}>
                        {c.file_path.split('/').pop() || c.file_path}
                      </span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase font-mono ${
                        c.validation_status === 'VERIFIED'
                          ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/50'
                          : 'bg-amber-950/80 text-amber-300 border border-amber-800/50'
                      }`}>
                        {c.validation_status}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {c.reason}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 font-mono">
                      <span>{c.section_name ? `§ ${c.section_name}` : 'Document Root'}</span>
                      <span className="text-slate-400">
                        {c.supporting_finding_ids?.length || 0} finding(s) addressed
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Diff Preview & Metadata */}
        <div className="lg:col-span-7 flex flex-col space-y-4">
          {selectedCorrection ? (
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-5 flex-1">
              {/* Header Info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-bold text-white font-mono break-all">
                      {selectedCorrection.file_path}
                    </h2>
                    <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                      Lines {selectedCorrection.line_start || 1}-{selectedCorrection.line_end || '?'}
                    </span>
                  </div>
                  {selectedCorrection.section_name && (
                    <div className="text-xs text-slate-400 mt-1 font-mono">
                      Target Section: <span className="text-slate-200">{selectedCorrection.section_name}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleCopyDiff(selectedCorrection.unified_diff, selectedCorrection.correction_id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700/60 transition-colors"
                  >
                    {copiedId === selectedCorrection.correction_id ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied Patch</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-slate-400" />
                        <span>Copy Patch</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Reason Explanation */}
              <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 text-xs">
                <div className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider mb-1">
                  Correction Rationale
                </div>
                <p className="text-slate-300 leading-relaxed">{selectedCorrection.reason}</p>
              </div>

              {/* Unified Diff */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Unified Diff Preview
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">git diff format</span>
                </div>
                {renderDiffLines(selectedCorrection.unified_diff)}
              </div>

              {/* Supporting Evidence & Findings Links */}
              <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2 text-slate-400">
                  <Layers className="w-4 h-4 text-indigo-400" />
                  <span>
                    Linked Findings: {selectedCorrection.supporting_finding_ids?.join(', ') || 'Direct Agent Synthesis'}
                  </span>
                </div>
                <Link
                  to={`/projects/${projectId}/findings`}
                  className="text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1"
                >
                  View Related Findings <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-8 flex flex-col items-center justify-center text-center text-slate-500 h-full">
              <FileEdit className="w-10 h-10 text-slate-700 mb-3" />
              <p className="text-sm font-medium text-slate-400">Select a proposed correction to view the unified diff</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
