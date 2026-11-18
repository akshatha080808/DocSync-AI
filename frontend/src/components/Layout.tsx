import React from 'react';
import { NavLink, Outlet, useParams } from 'react-router-dom';
import {
  FolderGit2,
  Upload,
  Cpu,
  AlertTriangle,
  Bot,
  Network,
  FileCheck2,
  FileText,
  Home,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { api } from '../services/api';

interface LayoutProps {
  children?: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { projectId } = useParams<{ projectId: string }>();
  const [health, setHealth] = React.useState<{ status: string; gemini_configured: boolean } | null>(null);

  React.useEffect(() => {
    api.getHealth()
      .then((res) => setHealth(res))
      .catch(() => setHealth({ status: 'offline', gemini_configured: false }));
  }, []);

  return (
    <div className="flex h-screen bg-[#070b12] text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800/80 bg-[#0b101b] flex flex-col justify-between shrink-0">
        <div>
          {/* Logo Header */}
          <div className="h-16 flex items-center px-6 border-b border-slate-800/80 gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold">
              DS
            </div>
            <div>
              <span className="font-semibold text-slate-100 text-sm tracking-wide">DocSync AI</span>
              <span className="block text-[11px] text-slate-500 font-mono">v0.1.0 • Core Engine</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`
              }
            >
              <Home className="w-4 h-4" />
              Projects Dashboard
            </NavLink>

            {projectId && (
              <>
                <div className="pt-4 pb-1 px-3 text-[10px] uppercase font-bold tracking-wider text-slate-500">
                  Workspace
                </div>
                <NavLink
                  to={`/projects/${projectId}`}
                  end
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`
                  }
                >
                  <FolderGit2 className="w-4 h-4" />
                  Overview
                </NavLink>

                <NavLink
                  to={`/projects/${projectId}/uploads`}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`
                  }
                >
                  <Upload className="w-4 h-4" />
                  Uploads
                </NavLink>

                <NavLink
                  to={`/projects/${projectId}/analysis`}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`
                  }
                >
                  <Cpu className="w-4 h-4" />
                  Codebase Analysis
                </NavLink>

                <NavLink
                  to={`/projects/${projectId}/findings`}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`
                  }
                >
                  <AlertTriangle className="w-4 h-4" />
                  Drift Findings
                </NavLink>

                <NavLink
                  to={`/projects/${projectId}/agent`}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`
                  }
                >
                  <Bot className="w-4 h-4" />
                  AI Agent & Trace
                </NavLink>

                <NavLink
                  to={`/projects/${projectId}/dependencies`}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`
                  }
                >
                  <Network className="w-4 h-4" />
                  Dependency Graph
                </NavLink>

                <NavLink
                  to={`/projects/${projectId}/corrections`}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`
                  }
                >
                  <FileCheck2 className="w-4 h-4" />
                  Proposed Corrections
                </NavLink>

                <NavLink
                  to={`/projects/${projectId}/reports`}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`
                  }
                >
                  <FileText className="w-4 h-4" />
                  Audit Reports
                </NavLink>
              </>
            )}
          </nav>
        </div>

        {/* Backend & Gemini Status Indicator */}
        <div className="p-4 border-t border-slate-800/80 bg-[#090d16] text-[11px] space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span>FastAPI Server:</span>
            <div className="flex items-center gap-1.5 font-medium">
              {health?.status === 'ok' ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-emerald-400">Online</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span className="text-rose-400">Offline</span>
                </>
              )}
            </div>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Gemini AI:</span>
            <div className="flex items-center gap-1.5 font-medium">
              {health?.gemini_configured ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-indigo-500" />
                  <span className="text-indigo-400">Configured</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-amber-500/60" />
                  <span className="text-amber-400/80">Deterministic Fallback</span>
                </>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="h-14 border-b border-slate-800/60 bg-[#0b101b]/60 backdrop-blur px-8 flex items-center justify-between shrink-0">
          <div className="text-xs text-slate-400">
            Developer Console &bull; <span className="text-slate-200 font-mono">127.0.0.1:8000</span>
          </div>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            <span>Swagger API Docs</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </header>
        <div className="flex-1 p-8">
          {children || <Outlet />}
        </div>
      </main>
    </div>
  );
};
