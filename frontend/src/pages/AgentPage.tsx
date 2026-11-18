import React from 'react';
import { useParams } from 'react-router-dom';
import { Bot, Play, CheckCircle2, AlertCircle, Wrench, ArrowRight, ShieldAlert, Terminal, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import type { AgentExecutionTrace } from '../types/api';

export const AgentPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [trace, setTrace] = React.useState<AgentExecutionTrace | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const loadTrace = React.useCallback(async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.getAgentTrace(projectId);
      setTrace(res);
    } catch (err: any) {
      if (err?.response?.status === 422 || err?.response?.status === 404) {
        setTrace(null);
      } else {
        setError(err?.response?.data?.detail || err.message || 'Failed to load trace.');
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    loadTrace();
  }, [loadTrace]);

  const handleRunAgent = async () => {
    if (!projectId) return;
    try {
      setRunning(true);
      setError(null);
      const res = await api.runAgent(projectId);
      setTrace(res.trace);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Agent investigation failed.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Top Banner */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">AI Agent Investigation & Trace</h1>
          <p className="text-xs text-slate-400 mt-1">
            Controlled Gemini 2.0 Flash tool-calling &bull; Multi-turn reasoning &bull; Allowlisted tools only
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadTrace}
            className="p-2 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleRunAgent}
            disabled={running}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-sm transition-colors disabled:opacity-40"
          >
            <Bot className="w-4 h-4" />
            <span>{running ? 'Agent Investigating...' : 'Trigger Agent Investigation'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Safety & Sandbox Notice */}
      <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/30 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <span className="font-semibold text-indigo-300">Bounded Execution & Sandbox Security Enforced</span>
          <p className="text-slate-400 leading-relaxed">
            The agent runs with a maximum bound of 10 turns. Only allowlisted tools (AST search, signature comparison, dependency inspection) can be executed. Secrets are redacted and repository content is treated as untrusted data.
          </p>
        </div>
      </div>

      {loading && !trace ? (
        <div className="text-xs text-slate-500 py-12 text-center">Loading agent execution trace...</div>
      ) : !trace ? (
        <div className="p-12 text-center rounded-xl bg-[#0b101b] border border-dashed border-slate-800 space-y-3">
          <Bot className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-300">No Agent Execution History</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Click "Trigger Agent Investigation" to launch the multi-turn agent investigation loop.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Execution Header Meta */}
          <div className="p-5 rounded-xl bg-[#0d1322] border border-slate-800 flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold text-slate-200">Execution Status:</span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                    trace.status === 'COMPLETED'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}
                >
                  {trace.status}
                </span>
                <span className="text-xs text-slate-400 font-mono">({trace.total_steps} steps)</span>
              </div>
              <p className="text-xs text-slate-500">
                <b>Termination Reason:</b> {trace.termination_reason}
              </p>
            </div>
            <div className="text-right text-[11px] font-mono text-slate-500">
              <div>Started: {new Date(trace.started_at).toLocaleTimeString()}</div>
              <div>Ended: {new Date(trace.completed_at).toLocaleTimeString()}</div>
            </div>
          </div>

          {/* Step-by-Step Observable Trace Timeline */}
          <div className="space-y-3">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Step-by-Step Observable Tool Audit
            </h2>

            {trace.steps.map((step) => {
              const isModelSelected = step.agent_action === 'MODEL_SELECTED_TOOL';
              return (
                <div
                  key={step.step_number}
                  className={`p-4 rounded-xl border transition-all space-y-3 ${
                    isModelSelected
                      ? 'bg-[#10172a] border-indigo-500/30'
                      : 'bg-[#0d1322] border-slate-800/80'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="w-6 h-6 rounded-md bg-slate-800 text-slate-300 font-mono text-xs flex items-center justify-center font-bold">
                        #{step.step_number}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold tracking-wider uppercase font-mono ${
                          isModelSelected
                            ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {step.agent_action}
                      </span>
                      {step.tool_selected && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-200 font-mono font-medium">
                          <Wrench className="w-3.5 h-3.5 text-indigo-400" />
                          <span>{step.tool_selected}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500">
                      <span
                        className={
                          step.execution_status === 'SUCCESS' ? 'text-emerald-400' : 'text-rose-400'
                        }
                      >
                        {step.execution_status}
                      </span>
                      <span>&bull;</span>
                      <span>{new Date(step.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>

                  {/* Observable Input & Output Summaries */}
                  {(step.tool_input_summary || step.tool_output_summary) && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800/60 text-xs">
                      {step.tool_input_summary && (
                        <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800/80 font-mono">
                          <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                            Arguments / Input:
                          </span>
                          <span className="text-slate-300 break-all">{step.tool_input_summary}</span>
                        </div>
                      )}
                      {step.tool_output_summary && (
                        <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800/80 font-mono">
                          <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                            Result / Output:
                          </span>
                          <span className="text-emerald-400/90 break-all">{step.tool_output_summary}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Reasoning note */}
                  <div className="text-[11px] text-slate-400">
                    <span className="text-slate-500">Observable Goal:</span> {step.reason}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
