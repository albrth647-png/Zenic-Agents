import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { auth, getToken, setToken, clearToken, getUser, setUser, clearUser } from '../api';
import type { LoginRequest, RegisterRequest, UserResponse } from '../types';

interface AuthContextType {
  user: UserResponse | null;
  token: string | null;
  loading: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<UserResponse | null>(getUser);
  const [token, setTokenState] = useState<string | null>(getToken);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = getToken();
    const savedUser = getUser();
    if (savedToken && savedUser) {
      setTokenState(savedToken);
      setUserState(savedUser);
      // Verify token is still valid
      auth.me().catch(() => {
        clearToken();
        clearUser();
        setTokenState(null);
        setUserState(null);
      }).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (payload: LoginRequest) => {
    const res = await auth.login(payload);
    setToken(res.access_token);
    setTokenState(res.access_token);
    setUserState(res.user);
    setUser(res.user);
  };

  const register = async (payload: RegisterRequest) => {
    await auth.register(payload);
  };

  const logout = () => {
    clearToken();
    clearUser();
    setTokenState(null);
    setUserState(null);
  };

  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
