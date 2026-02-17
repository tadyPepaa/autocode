import { useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAgents, useInitAgents, type Agent } from '../api/agents';

const typeIcons: Record<string, string> = {
  coding: '\u{1F4BB}',
  research: '\u{1F52C}',
  learning: '\u{1F393}',
  social_media: '\u{1F4F1}',
  custom: '\u{2699}\uFE0F',
};

const linkBase = 'block px-4 py-2 rounded-md text-sm transition-colors';
const linkActive = 'bg-gray-700 text-white';
const linkInactive = 'text-gray-300 hover:bg-gray-700/50 hover:text-white';

function navLinkClass({ isActive }: { isActive: boolean }) {
  return `${linkBase} ${isActive ? linkActive : linkInactive}`;
}

interface SidebarProps {
  onNavigate?: () => void;
}

export default function Sidebar({ onNavigate }: SidebarProps) {
  const { user, logout } = useAuth();
  const { data: agents = [] } = useAgents();
  const initAgents = useInitAgents();

  useEffect(() => {
    initAgents.mutate();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <aside className="w-64 flex-shrink-0 bg-gray-800 border-r border-gray-700 flex flex-col h-full">
      <div className="px-4 py-5 flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">AutoCode</h1>
        {/* Close button on mobile */}
        <button
          onClick={onNavigate}
          className="text-gray-400 hover:text-white lg:hidden"
          aria-label="Close menu"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        <NavLink to="/" end className={navLinkClass} onClick={onNavigate}>
          Dashboard
        </NavLink>

        <div className="border-t border-gray-700 my-3" />

        <p className="px-4 text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
          Agents
        </p>

        {agents.map((agent: Agent) => (
          <NavLink key={agent.id} to={`/agents/${agent.id}`} className={navLinkClass} onClick={onNavigate}>
            <span className="mr-2">{typeIcons[agent.type] || typeIcons.custom}</span>
            {agent.name}
          </NavLink>
        ))}

        <div className="border-t border-gray-700 my-3" />

        <NavLink to="/agents/new" className={navLinkClass} onClick={onNavigate}>
          + New Agent
        </NavLink>

        <div className="border-t border-gray-700 my-3" />

        <NavLink to="/settings" className={navLinkClass} onClick={onNavigate}>
          Settings
        </NavLink>

        {user?.role === 'admin' && (
          <NavLink to="/admin" className={navLinkClass} onClick={onNavigate}>
            Admin Panel
          </NavLink>
        )}
      </nav>

      <div className="px-3 py-4 border-t border-gray-700">
        <div className="flex items-center justify-between px-2">
          <span className="text-sm text-gray-300 truncate">{user?.username}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </aside>
  );
}
