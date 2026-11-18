# DocSync AI — Frontend Application (Quarter 3)

DocSync AI provides an enterprise-grade developer console for detecting, investigating, and resolving codebase documentation drift with deterministic precision and Gemini AI agent intelligence.

## 🛠 Tech Stack

- **Framework**: React 19 + TypeScript
- **Bundler**: Vite 8 with `@vitejs/plugin-react`
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite`)
- **Routing**: React Router v7 (`react-router-dom`)
- **Graph Visualization**: React Flow (`@xyflow/react` v13)
- **Icons**: Lucide React
- **HTTP Client**: Axios with centralized error handling and health checks

---

## 🧭 Page Architecture & Views

| View | Route | Functionality |
| :--- | :--- | :--- |
| **Project Dashboard** | `/` | Projects inventory, creation modal, storage size & file metrics, deletion safeguards. |
| **Project Overview** | `/projects/:projectId` | System health badge, parsed LOC/functions counters, drift summary, workflow action hub. |
| **Uploads Management** | `/projects/:projectId/uploads` | Drag-and-drop ZIP codebase upload with Zip Slip defense warnings; PDF/MD doc uploads. |
| **Code & AST Analysis** | `/projects/:projectId/analysis` | Trigger deterministic AST parsing; inspect Python/JS functions, classes, methods, docstrings. |
| **Drift Findings** | `/projects/:projectId/findings` | Severity/category filters, side-by-side documented claim vs actual code fact comparisons. |
| **AI Agent Trace** | `/projects/:projectId/agent` | Gemini function-calling timeline; distinguishes `MODEL_SELECTED_TOOL` from deterministic fallback steps. |
| **Dependency Graph** | `/projects/:projectId/dependencies` | Interactive React Flow canvas showing NetworkX directed imports, circular cycle alerts, isolated modules. |
| **Proposed Corrections** | `/projects/:projectId/corrections` | Non-destructive unified diff viewer (`git diff` patch format) with one-click clipboard copy. |
| **Audit Reports** | `/projects/:projectId/reports` | Executive documentation health index, one-click ReportLab PDF streaming download, JSON audit export. |

---

## 🚀 Getting Started

### 1. Prerequisites
- Node.js `v20+` (verified with `v22.12.0`)
- npm `v10+` (verified with `10.9.0`)
- Running DocSync AI Backend (`127.0.0.1:8000`)

### 2. Environment Variables
Create or verify `.env` in the `frontend` root:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### 3. Install Dependencies & Run Development Server
```bash
cd frontend
npm install
npm run dev
```
The application will launch on `http://localhost:5173`.

### 4. Build for Production
```bash
npm run build
```
Production assets are compiled to `frontend/dist/`.

---

## 🛡 Security & Non-Destructive Principles

1. **Strict Non-Destructive Editing**: The frontend never triggers or allows automatic in-place overwrites of original uploaded markdown or source code files. All proposals are presented as standard unified diffs for manual review.
2. **Zero Code Execution**: Uploaded source code is inspected strictly via AST / Tree-sitter parsers. Code is never evaluated or run on either frontend or backend.
3. **No Key Leakage**: Gemini API keys are maintained exclusively on the backend via environment variables and never exposed to the browser client.
