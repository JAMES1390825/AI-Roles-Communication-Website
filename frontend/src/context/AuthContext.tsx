// src/context/AuthContext.tsx
'use client'; // 标记为客户端组件，因为要使用 useState, useEffect

import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import axios from 'axios';

// 从环境变量获取后端URL
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL;

interface AuthContextType {
  token: string | null;
  user: { id: string; username: string; email: string } | null;
  login: (token: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<{ id: string; username: string; email: string } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 尝试从 localStorage 加载 token 和用户数据
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      setToken(storedToken);
      // 尝试获取用户数据
      fetchUserData(storedToken);
    } else {
      setIsLoading(false); // 没有token，认证加载完成
    }
  }, []);

  const fetchUserData = async (authToken: string) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/users/me/`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      logout(); // 获取失败则清除token
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (newToken: string) => {
    localStorage.setItem('access_token', newToken);
    setToken(newToken);
    await fetchUserData(newToken);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
    setIsLoading(false);
    // 重定向到登录页面，这里可以根据实际路由库来做
    window.location.href = '/login'; 
  };

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};