import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import api from '../api/client';

interface AuthUser {
  id: number;
  username: string;
  role: string;
}

interface AuthContextType {
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

function decodeToken(token: string): { sub: number; username: string; role: string; exp: number } {
  return JSON.parse(atob(token.split('.')[1]));
}

function getUserFromToken(token: string): AuthUser | null {
  try {
    const payload = decodeToken(token);
    if (payload.exp * 1000 < Date.now()) return null;
    return { id: payload.sub, username: payload.username, role: payload.role };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      const restored = getUserFromToken(token);
      setUser(restored);
      if (!restored) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    const res = await api.post('/auth/login', { username, password });
    const { access_token, refresh_token } = res.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    const decoded = getUserFromToken(access_token);
    if (!decoded) throw new Error('Invalid token received');
    setUser(decoded);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
