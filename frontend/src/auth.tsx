import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';

const API = import.meta.env.VITE_API_URL || '';

interface AuthUser {
  id: string;
  username: string;
  display_name: string;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null, token: null, login: async () => {}, logout: () => {}, loading: true,
});

export const useAuth = () => useContext(AuthContext);

// 全局 axios 拦截器 — 自动附加 Authorization header
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 回调 — 由 AuthProvider 注册，清除状态触发 React 重定向（不用 window.location 强刷）
let onAuthExpired: (() => void) | null = null;

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    // 只读模式（试用宽限期内）拦截 — 后端中间件返回 403 + error_code=READ_ONLY_MODE
    if (error.response?.status === 403 && error.response?.data?.error_code === 'READ_ONLY_MODE') {
      const detail = error.response.data.detail || '试用已到期，请激活正式版';
      const graceDays = error.response.data.grace_days_remaining;
      const msg = graceDays > 0
        ? `${detail}（宽限期还剩 ${graceDays} 天）`
        : detail;
      // 与项目其他错误一致，使用 alert；后续可改成 toast
      alert(msg);
      return Promise.reject(error);
    }
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      if (onAuthExpired) onAuthExpired();
    }
    return Promise.reject(error);
  }
);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // 注册 401 回调 — 清除 React state，ProtectedRoute 会自动跳转 /login
  useEffect(() => {
    onAuthExpired = () => { setToken(null); setUser(null); };
    return () => { onAuthExpired = null; };
  }, []);

  useEffect(() => {
    const savedToken = localStorage.getItem('auth_token');
    const savedUser = localStorage.getItem('auth_user');
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
      axios.get(`${API}/api/v1/auth/me`).catch(() => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        setToken(null);
        setUser(null);
      });
    }
    setLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    const res = await axios.post(`${API}/api/v1/auth/login`, { username, password });
    const { token: newToken, user: newUser } = res.data;
    localStorage.setItem('auth_token', newToken);
    localStorage.setItem('auth_user', JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
