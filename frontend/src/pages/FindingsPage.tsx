import React from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  AlertTriangle,
  Play,
  Filter,
  CheckCircle2,
  FileText,
  FileCode,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import type { DriftFinding, SeverityLevel, DriftCategory } from '../types/api';

export const FindingsPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [findings, setFindings] = React.useState<DriftFinding[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [detecting, setDetecting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Filters
  const [selectedSeverity, setSelectedSeverity] = React.useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = React.useState<string>('ALL');
  const [searchQuery, setSearchQuery] = React.useState<string>('');

  const loadFindings = React.useCallback(async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.getFindings(projectId);
      setFindings(res.findings);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load findings.');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  const handleRunDetection = async () => {
    if (!projectId) return;
    try {
      setDetecting(true);
      setError(null);
      const res = await api.detectDrift(projectId);
      setFindings(res.findings);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Drift scan failed.');
    } finally {
      setDetecting(false);
    }
  };

  // Filtered findings
  const filteredFindings = React.useMemo(() => {
    return findings.filter((f) => {
      if (selectedSeverity !== 'ALL' && f.severity !== selectedSeverity) return false;
      if (selectedCategory !== 'ALL' && f.category !== selectedCategory) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = f.title.toLowerCase().includes(q);
        const matchesDesc = f.description.toLowerCase().includes(q);
        const matchesSym = f.symbol?.toLowerCase().includes(q);
        const matchesFile = f.documentation.file.toLowerCase().includes(q);
        if (!matchesTitle && !matchesDesc && !matchesSym && !matchesFile) return false;
      }
      return true;
    });
  }, [findings, selectedSeverity, selectedCategory, searchQuery]);

  const severityBadge = (sev: SeverityLevel) => {
    const config = {
      CRITICAL: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      HIGH: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
      MEDIUM: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      LOW: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
      INFO: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    }[sev] || 'bg-slate-800 text-slate-300';

    return (
      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${config}`}>
        {sev}
      </span>
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Documentation Drift Findings</h1>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic code truth vs documentation claims &bull; Impact ranked
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadFindings}
            className="p-2 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleRunDetection}
            disabled={detecting}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-sm transition-colors disabled:opacity-40"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{detecting ? 'Scanning for Drift...' : 'Run Drift Detection'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
          {error}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-[240px]">
          <input
            type="text"
            placeholder="Search by symbol, file, title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-md text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Severity:</span>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
              <option value="INFO">Info</option>
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>Category:</span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Categories</option>
              <option value="OUTDATED">Outdated</option>
              <option value="MISSING">Missing</option>
              <option value="CONTRADICTORY">Contradictory</option>
              <option value="INVALID">Invalid</option>
              <option value="INCOMPLETE">Incomplete</option>
            </select>
          </div>
        </div>
      </div>

      {/* Findings List */}
      {loading ? (
        <div className="text-xs text-slate-500 py-12 text-center">Loading drift findings...</div>
      ) : filteredFindings.length === 0 ? (
        <div className="p-12 text-center rounded-xl bg-[#0b101b] border border-dashed border-slate-800 space-y-2">
          <CheckCircle2 className="w-10 h-10 text-emerald-500/80 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-300">No Matching Findings</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            {findings.length === 0
              ? 'Click "Run Drift Detection" to compare extracted documentation against codebase ground truth.'
              : 'No findings match your current filter parameters.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredFindings.map((finding) => (
            <div
              key={finding.finding_id}
              className="p-5 rounded-xl bg-[#0d1322] border border-slate-800 hover:border-slate-700 transition-all space-y-4"
            >
              {/* Finding Card Top */}
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs font-bold text-slate-400">{finding.finding_id}</span>
                    {severityBadge(finding.severity)}
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium tracking-wider uppercase bg-slate-800 text-slate-400">
                      {finding.category}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium tracking-wider uppercase bg-indigo-950/60 text-indigo-400 border border-indigo-500/20">
                      {finding.verification_status}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-slate-100">{finding.title}</h3>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-[11px] font-mono text-slate-400">
                    Confidence: {(finding.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Explanations & Facts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-rose-500/5 border border-rose-500/20 space-y-1">
                  <span className="text-[10px] uppercase font-bold text-rose-400 tracking-wider">
                    Documented Claim:
                  </span>
                  <div className="font-mono text-slate-300">{finding.documented_claim}</div>
                  <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1">
                    <FileText className="w-3 h-3" />
                    <span>{finding.documentation.file}</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 space-y-1">
                  <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">
                    Actual Code Fact:
                  </span>
                  <div className="font-mono text-slate-300">{finding.actual_fact}</div>
                  <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1">
                    <FileCode className="w-3 h-3" />
                    <span>{finding.source?.file || 'Extracted AST'}</span>
                  </div>
                </div>
              </div>

              {/* Explanation & Suggested Correction */}
              <div className="text-xs text-slate-400 space-y-2 pt-1 border-t border-slate-800/60">
                <p>
                  <b className="text-slate-300">Explanation:</b> {finding.explanation}
                </p>
                {finding.suggested_correction && (
                  <p className="text-indigo-300">
                    <b>Suggested Correction:</b> {finding.suggested_correction}
                  </p>
                )}
                {finding.impact_explanation && (
                  <p className="text-amber-400/90 text-[11px]">
                    <b>Impact:</b> {finding.impact_explanation}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
