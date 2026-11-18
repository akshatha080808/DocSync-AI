import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node,
  Edge,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { api } from '../services/api';
import type { DependencyGraph, DependencyNode } from '../types/api';
import {
  GitFork,
  AlertTriangle,
  Search,
  Maximize2,
  RefreshCw,
  FileCode,
  Layers,
  ArrowRight,
  Info,
  ExternalLink,
  Code2,
} from 'lucide-react';

export const DependencyGraphPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [graph, setGraph] = useState<DependencyGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const fetchDependencies = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDependencies(projectId);
      setGraph(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load dependency graph. Make sure analysis has been run.');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchDependencies();
  }, [fetchDependencies]);

  // Layout and map nodes/edges for React Flow
  useEffect(() => {
    if (!graph || !graph.nodes || graph.nodes.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    // Identify nodes involved in cycles
    const cycleNodeIds = new Set<string>();
    (graph.cycles || []).forEach(cycle => {
      cycle.forEach(id => cycleNodeIds.add(id));
    });

    // Layout configuration: grid-based placement with grouping
    const cols = Math.max(3, Math.ceil(Math.sqrt(graph.nodes.length * 1.5)));
    const spacingX = 280;
    const spacingY = 160;

    const flowNodes: Node[] = graph.nodes.map((node, index) => {
      const row = Math.floor(index / cols);
      const col = index % cols;
      const isCycle = cycleNodeIds.has(node.id);
      const isIsolated = graph.isolated_modules?.includes(node.id);
      const isMatch = searchQuery ? node.label.toLowerCase().includes(searchQuery.toLowerCase()) : true;

      const isPython = node.language?.toLowerCase() === 'python' || node.file_path.endsWith('.py');
      const isJS = node.language?.toLowerCase().includes('javascript') || node.file_path.endsWith('.js') || node.file_path.endsWith('.ts');

      return {
        id: node.id,
        position: { x: col * spacingX + 50, y: row * spacingY + 50 },
        data: {
          label: (
            <div className={`p-3 rounded-lg border text-left w-56 transition-all shadow-md ${
              isCycle
                ? 'bg-rose-950/40 border-rose-600/70 text-rose-200 ring-2 ring-rose-500/30'
                : isIsolated
                ? 'bg-slate-900/60 border-slate-700/50 text-slate-400'
                : isMatch && searchQuery
                ? 'bg-indigo-950/70 border-indigo-500 text-indigo-100 ring-2 ring-indigo-400/40'
                : 'bg-slate-900 border-slate-700/80 text-slate-200 hover:border-slate-500'
            }`}>
              <div className="flex items-center justify-between mb-1.5">
                <span className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded font-semibold ${
                  isPython ? 'bg-emerald-950/70 text-emerald-300 border border-emerald-800/40' :
                  isJS ? 'bg-amber-950/70 text-amber-300 border border-amber-800/40' :
                  'bg-slate-800 text-slate-400'
                }`}>
                  {node.language || (node.file_path.endsWith('.py') ? 'Python' : 'Code')}
                </span>
                {isCycle && (
                  <span className="flex items-center text-[10px] text-rose-400 font-semibold gap-0.5">
                    <AlertTriangle className="w-3 h-3 text-rose-400" /> Cycle
                  </span>
                )}
              </div>
              <div className="font-mono text-xs font-medium truncate text-white" title={node.label}>
                {node.label}
              </div>
              <div className="text-[10px] text-slate-400 truncate mt-0.5 font-mono" title={node.file_path}>
                {node.file_path}
              </div>
            </div>
          ),
          rawNode: node,
        },
        style: {
          background: 'transparent',
          border: 'none',
          padding: 0,
        },
      };
    });

    const flowEdges: Edge[] = (graph.edges || []).map((edge, i) => {
      const isCycleEdge = (graph.cycles || []).some(cycle => {
        for (let c = 0; c < cycle.length; c++) {
          const next = (c + 1) % cycle.length;
          if (cycle[c] === edge.source && cycle[next] === edge.target) return true;
        }
        return false;
      });

      return {
        id: `e-${edge.source}-${edge.target}-${i}`,
        source: edge.source,
        target: edge.target,
        animated: isCycleEdge,
        style: {
          stroke: isCycleEdge ? '#f43f5e' : '#64748b',
          strokeWidth: isCycleEdge ? 2.5 : 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isCycleEdge ? '#f43f5e' : '#64748b',
          width: 15,
          height: 15,
        },
      };
    });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [graph, searchQuery, setNodes, setEdges]);

  // Selected node details
  const selectedNode = useMemo(() => {
    if (!selectedNodeId || !graph) return null;
    return graph.nodes.find(n => n.id === selectedNodeId) || null;
  }, [selectedNodeId, graph]);

  const incomingEdges = useMemo(() => {
    if (!selectedNodeId || !graph) return [];
    return (graph.edges || []).filter(e => e.target === selectedNodeId);
  }, [selectedNodeId, graph]);

  const outgoingEdges = useMemo(() => {
    if (!selectedNodeId || !graph) return [];
    return (graph.edges || []).filter(e => e.source === selectedNodeId);
  }, [selectedNodeId, graph]);

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <GitFork className="w-6 h-6 text-indigo-400" />
            Module Dependency Graph
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            NetworkX directed dependency model rendered via React Flow. Inspect import relationships and architectural cycles.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchDependencies}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700/60 font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics & Badges Bar */}
      {graph && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Nodes (Modules)</div>
              <div className="text-2xl font-bold text-white mt-1 font-mono">{graph.nodes.length}</div>
            </div>
            <FileCode className="w-6 h-6 text-indigo-400/80" />
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Edges (Imports)</div>
              <div className="text-2xl font-bold text-white mt-1 font-mono">{graph.edges?.length || 0}</div>
            </div>
            <GitFork className="w-6 h-6 text-cyan-400/80" />
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Circular Cycles</div>
              <div className={`text-2xl font-bold mt-1 font-mono ${(graph.cycles?.length || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {graph.cycles?.length || 0}
              </div>
            </div>
            <AlertTriangle className={`w-6 h-6 ${(graph.cycles?.length || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'}`} />
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Isolated Modules</div>
              <div className="text-2xl font-bold text-slate-300 mt-1 font-mono">{graph.isolated_modules?.length || 0}</div>
            </div>
            <Layers className="w-6 h-6 text-slate-400/80" />
          </div>
        </div>
      )}

      {/* Cycle Warning Banner if circular dependencies exist */}
      {graph && graph.cycles && graph.cycles.length > 0 && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-800/60 text-rose-300 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-rose-200 text-sm">Circular Dependencies Detected</h3>
            <p className="text-xs text-rose-300/90 mt-1">
              NetworkX detected {graph.cycles.length} circular dependency cycle(s). These create tight coupling and fragile documentation assumptions:
            </p>
            <div className="mt-2 space-y-1">
              {graph.cycles.map((cycle, i) => (
                <div key={i} className="text-xs font-mono bg-rose-950/60 p-2 rounded border border-rose-900/50 flex flex-wrap items-center gap-1.5 text-rose-200">
                  {cycle.map((nodeId, ci) => (
                    <React.Fragment key={ci}>
                      <span className="font-semibold text-white">{nodeId}</span>
                      {ci < cycle.length - 1 && <ArrowRight className="w-3 h-3 text-rose-400 inline" />}
                    </React.Fragment>
                  ))}
                  <ArrowRight className="w-3 h-3 text-rose-400 inline" />
                  <span className="font-semibold text-rose-400">{cycle[0]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Zero edges informational banner */}
      {graph && graph.nodes.length > 0 && (!graph.edges || graph.edges.length === 0) && (
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 flex items-start gap-3">
          <Info className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-slate-200 text-sm">No Internal Module Dependencies Detected</h3>
            <p className="text-xs text-slate-400 mt-1">
              No internal module dependencies were detected in the analyzed source files. The uploaded files are either independent standalone modules or exclusively import external packages ({graph.external_dependencies?.join(', ') || 'none'}).
            </p>
          </div>
        </div>
      )}

      {/* Main Canvas + Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-[640px]">
        {/* Flow Canvas */}
        <div className="lg:col-span-3 rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden relative flex flex-col min-h-[640px]">
          {/* Canvas Controls Header */}
          <div className="p-3 bg-slate-900/90 border-b border-slate-800/80 flex items-center justify-between gap-3 z-10">
            <div className="relative w-64">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search modules..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700/80 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span> Python
              </span>
              <span className="flex items-center gap-1.5 ml-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span> JS/TS
              </span>
              <span className="flex items-center gap-1.5 ml-2">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span> Cycle
              </span>
            </div>
          </div>

          {/* React Flow Workspace */}
          <div className="flex-1 w-full h-[580px]">
            {loading ? (
              <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
                <p className="text-sm">Building module graph...</p>
              </div>
            ) : error ? (
              <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 p-6 text-center">
                <AlertTriangle className="w-10 h-10 text-amber-400 mb-3" />
                <p className="text-sm text-slate-200 mb-2 font-medium">{error}</p>
                <Link
                  to={`/projects/${projectId}/analysis`}
                  className="px-4 py-2 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
                >
                  Go to Code Analysis
                </Link>
              </div>
            ) : nodes.length === 0 ? (
              <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 p-6 text-center">
                <GitFork className="w-10 h-10 text-slate-600 mb-3" />
                <p className="text-sm text-slate-300 font-medium">No module dependencies found</p>
                <p className="text-xs text-slate-500 mt-1">Make sure source code has been uploaded and analyzed.</p>
              </div>
            ) : (
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={handleNodeClick}
                fitView
              >
                <Background color="#334155" gap={20} size={1} variant={BackgroundVariant.Dots} />
                <Controls className="bg-slate-900 border-slate-700 text-slate-200 fill-slate-200" />
                <MiniMap
                  nodeColor={n => {
                    if (graph?.cycles?.some(cycle => cycle.includes(n.id))) return '#f43f5e';
                    return '#6366f1';
                  }}
                  className="bg-slate-900/90 border border-slate-800 rounded-lg"
                  maskColor="rgba(15, 23, 42, 0.7)"
                />
              </ReactFlow>
            )}
          </div>
        </div>

        {/* Selected Node Details Inspector */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 flex flex-col h-full">
          <div className="flex items-center gap-2 text-sm font-semibold text-white border-b border-slate-800 pb-3 mb-4">
            <Info className="w-4 h-4 text-indigo-400" />
            Module Inspector
          </div>

          {selectedNode ? (
            <div className="space-y-4 flex-1 overflow-y-auto">
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Module ID</div>
                <div className="text-sm font-mono font-medium text-white break-all mt-0.5">{selectedNode.label}</div>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">File Path</div>
                <div className="text-xs font-mono text-indigo-300 break-all mt-0.5 bg-slate-950 p-2 rounded border border-slate-800">
                  {selectedNode.file_path}
                </div>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Language</div>
                <div className="text-xs text-slate-200 mt-0.5">{selectedNode.language || 'Unknown'}</div>
              </div>

              {/* Outgoing Imports */}
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Imports ({outgoingEdges.length})</span>
                  <span className="text-[10px] text-slate-500 font-mono">Outgoing</span>
                </div>
                <div className="mt-1.5 space-y-1 max-h-36 overflow-y-auto">
                  {outgoingEdges.length === 0 ? (
                    <div className="text-xs text-slate-500 italic">No internal imports</div>
                  ) : (
                    outgoingEdges.map((e, idx) => (
                      <div
                        key={idx}
                        onClick={() => setSelectedNodeId(e.target)}
                        className="text-xs font-mono p-1.5 rounded bg-slate-950/70 hover:bg-slate-800/80 border border-slate-800 cursor-pointer text-slate-300 hover:text-white transition-colors flex items-center justify-between"
                      >
                        <span className="truncate">{e.target}</span>
                        <ArrowRight className="w-3 h-3 text-slate-500 shrink-0 ml-1" />
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Incoming Imports */}
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Imported By ({incomingEdges.length})</span>
                  <span className="text-[10px] text-slate-500 font-mono">Incoming</span>
                </div>
                <div className="mt-1.5 space-y-1 max-h-36 overflow-y-auto">
                  {incomingEdges.length === 0 ? (
                    <div className="text-xs text-slate-500 italic">No incoming imports</div>
                  ) : (
                    incomingEdges.map((e, idx) => (
                      <div
                        key={idx}
                        onClick={() => setSelectedNodeId(e.source)}
                        className="text-xs font-mono p-1.5 rounded bg-slate-950/70 hover:bg-slate-800/80 border border-slate-800 cursor-pointer text-slate-300 hover:text-white transition-colors flex items-center justify-between"
                      >
                        <span className="truncate">{e.source}</span>
                        <ArrowRight className="w-3 h-3 text-slate-500 shrink-0 ml-1" />
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-4 text-slate-500">
              <FileCode className="w-8 h-8 text-slate-600 mb-2" />
              <p className="text-xs">Click on any module node on the canvas to inspect its inward and outward dependency links.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
