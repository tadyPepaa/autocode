import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AgentBuilder from './pages/AgentBuilder';
import AgentDetail from './pages/AgentDetail';
import ProjectDetail from './pages/ProjectDetail';
import ResearchChat from './pages/ResearchChat';
import LearningDetail from './pages/LearningDetail';
import CourseChat from './pages/CourseChat';
import SocialMedia from './pages/SocialMedia';
import Settings from './pages/Settings';
import AdminPanel from './pages/AdminPanel';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/agents/new" element={<AgentBuilder />} />
          <Route path="/agents/:id" element={<AgentDetail />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/research/:id" element={<ResearchChat />} />
          <Route path="/learning/:agentId" element={<LearningDetail />} />
          <Route path="/learning/course/:id" element={<CourseChat />} />
          <Route path="/social/:agentId" element={<SocialMedia />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/admin" element={<AdminPanel />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
