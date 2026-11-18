# DocSync AI — Developer Documentation Drift Platform

**DocSync AI** is a documentation drift intelligence platform designed for software engineering teams. It bridges the gap between evolving codebases and technical documentation by pairing deterministic AST parsing with Google Gemini agentic function calling.

---

## 🏛 System Architecture Overview

```text
DocSync-AI-Project/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entrypoint & CORS
│   │   ├── core/                       # Config, exceptions, secret redaction
│   │   ├── routes/                     # Projects, uploads, analysis, drift, reports
│   │   ├── services/                   # ProjectService, UploadService, DriftService
│   │   ├── engines/                    # Archive, Source (AST/Tree-sitter), Dependency (NetworkX),
│   │   │                               # Documentation (PyMuPDF), Config, Drift, Impact, Correction, Report
│   │   ├── agents/                     # Gemini Orchestrator, dynamic tool calling, investigation tools
│   │   └── models/                     # Pydantic schemas (Project, AST, DriftFinding, Correction, Trace)
│   └── tests/                          # 28 automated tests (100% passing)
├── frontend/                           # React 19 + TypeScript + Tailwind v4 + React Flow v13
│   ├── src/
│   │   ├── components/                 # Layout with health monitoring & navigation
│   │   ├── pages/                      # 8 Developer Console Views
│   │   ├── services/                   # Centralized Axios API client
│   │   └── types/                      # TypeScript API model interfaces
│   └── dist/                           # Production build assets
└── docs/
    └── QUARTER_3_REPORT.md             # Quarter 3 comprehensive delivery report
```

---

## 🎯 Features Delivered across Quarters

### Quarter 1: Deterministic Analysis Foundation
- **Safe ZIP Extraction**: Zip Slip directory traversal defense, symlink rejection, byte/file limits.
- **Polyglot AST Parsing**: Python `ast` parser and JavaScript `tree-sitter` parser extracting functions, classes, signatures, parameters, docstrings, and comments.
- **Documentation Ingestion**: Markdown, RST, TXT, and PDF parsing using PyMuPDF.
- **Config & Secret Redaction**: YAML, JSON, `.env.example` parser with regex-based credential masking.
- **NetworkX Dependency Engine**: Directed import dependency graph, circular cycle detection, isolated module identification.

### Quarter 2 & 2.5: Agentic AI Drift Detection
- **Deterministic Drift Engine**: Identifies parameter mismatches, missing symbols, signature drifts, and configuration divergence.
- **Dynamic Gemini Tool Calling**: Gemini 2.0 Flash agent using `google-genai` function calling with strict parameter schema validation and allowlisted tool execution.
- **Step-by-Step Observable Trace**: Full audit trail recording tool requests, inputs, outputs, and model reasoning.
- **Deterministic Fallback**: Graceful heuristic investigation if Gemini API keys are unconfigured.
- **Non-Destructive Corrections**: Synthesizes unified `git diff` patch proposals without overwriting source documentation.

### Quarter 3: Frontend Developer Console & Executive Reporting
- **Modern React 19 + Vite + Tailwind Console**: Dark-themed UI crafted for engineering teams.
- **Interactive React Flow Dependency Graph**: Visual module relationships, circular dependency cycle alerts, and node inspector.
- **Visual Drift Inspector**: Documented claim vs codebase truth side-by-side comparison with confidence ratings.
- **AI Agent Audit Timeline**: Live observable step execution distinguishing model-selected tools from deterministic heuristics.
- **Proposed Diff Viewer**: Syntax-highlighted patch preview with one-click clipboard copy.
- **Executive Reporting Hub**: ReportLab-powered PDF executive summaries and machine-readable JSON compliance bundles.

---

## 🚀 Quickstart Guide

### 1. Run Backend
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Swagger UI available at: `http://127.0.0.1:8000/docs`

### 2. Run Frontend
```bash
cd frontend
npm install
npm run dev
```
Developer Console available at: `http://localhost:5173`

### 3. Run Test Suite
```bash
cd backend
python -m pytest tests -v
```
**Current Test Status**: 28 passed, 0 failed, 1 warning (100% pass rate).

---

## 🔒 Security & Privacy Guarantees

- **No Code Execution**: Source code is strictly parsed statically (AST/CST). Uploaded code is never run.
- **Non-Destructive Documentation**: DocSync AI never automatically overwrites repository documentation.
- **Strict Project Isolation**: File storage is partitioned per project under `data/projects/{project_id}/`.
- **Zero API Key Leakage**: API credentials remain isolated on the backend server.
