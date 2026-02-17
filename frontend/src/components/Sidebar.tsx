import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';

interface Agent {
  id: number;
  name: string;
}

const linkBase = 'block px-4 py-2 rounded-md text-sm transition-colors';
const linkActive = 'bg-gray-700 text-white';
const linkInactive = 'text-gray-300 hover:bg-gray-700/50 hover:text-white';

function navLinkClass({ isActive }: { isActive: boolean }) {
  return `${linkBase} ${isActive ? linkActive : linkInactive}`;
}

export default function Sidebar() {
  const { user, logout } = useAuth();
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    api.get('/agents').then((res) => setAgents(res.data)).catch(() => {});
  }, []);

  return (
    <aside className="w-64 flex-shrink-0 bg-gray-800 border-r border-gray-700 flex flex-col h-full">
      <div className="px-4 py-5">
        <h1 className="text-xl font-bold text-white">AutoCode</h1>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        <NavLink to="/" end className={navLinkClass}>
          Dashboard
        </NavLink>

        <div className="border-t border-gray-700 my-3" />

        {agents.map((agent) => (
          <NavLink key={agent.id} to={`/agents/${agent.id}`} className={navLinkClass}>
            {agent.name}
          </NavLink>
        ))}

        <div className="border-t border-gray-700 my-3" />

        <NavLink to="/agents/new" className={navLinkClass}>
          + New Agent
        </NavLink>

        <div className="border-t border-gray-700 my-3" />

        <NavLink to="/settings" className={navLinkClass}>
          Settings
        </NavLink>

        {user?.role === 'admin' && (
          <NavLink to="/admin" className={navLinkClass}>
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
