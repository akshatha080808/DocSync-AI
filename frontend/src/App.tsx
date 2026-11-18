import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { OverviewPage } from './pages/OverviewPage';
import { UploadsPage } from './pages/UploadsPage';
import { AnalysisPage } from './pages/AnalysisPage';
import { FindingsPage } from './pages/FindingsPage';
import { AgentPage } from './pages/AgentPage';
import { DependencyGraphPage } from './pages/DependencyGraphPage';
import { CorrectionsPage } from './pages/CorrectionsPage';
import { ReportsPage } from './pages/ReportsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projects/:projectId" element={<OverviewPage />} />
          <Route path="/projects/:projectId/uploads" element={<UploadsPage />} />
          <Route path="/projects/:projectId/analysis" element={<AnalysisPage />} />
          <Route path="/projects/:projectId/findings" element={<FindingsPage />} />
          <Route path="/projects/:projectId/agent" element={<AgentPage />} />
          <Route path="/projects/:projectId/dependencies" element={<DependencyGraphPage />} />
          <Route path="/projects/:projectId/corrections" element={<CorrectionsPage />} />
          <Route path="/projects/:projectId/reports" element={<ReportsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
};

export default App;
