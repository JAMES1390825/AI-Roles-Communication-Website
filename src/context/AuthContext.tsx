// frontend/src/context/AuthContext.tsx
'use client'; // 标记为客户端组件，因为要使用 useState, useEffect

import React, { createContext, useState, useContext, useEffect, ReactNode, useCallback } from 'react'; // 导入 useCallback
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

  // 使用 useCallback 包裹 fetchUserData，并将其依赖项也传入
  const fetchUserData = useCallback(async (authToken: string) => {
    console.log('AuthContext: fetchUserData called');
    try {
      const response = await axios.get(`${BACKEND_URL}/users/me/`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      setUser(response.data);
      console.log('AuthContext: User data fetched successfully:', response.data.username);
    } catch (error) {
      console.error('AuthContext: Failed to fetch user data:', error);
      // 这里 logout 也应该在 useCallback 的依赖中，或者移出
      // 为了简化，我们暂时不将 logout 传入 useCallback，而是直接调用
      localStorage.removeItem('access_token');
      setToken(null);
      setUser(null);
      window.location.href = '/login'; 
    } finally {
      setIsLoading(false);
      console.log('AuthContext: fetchUserData finished, isLoading set to false');
    }
  }, [setToken, setUser, setIsLoading]); // 添加 setUser, setToken, setIsLoading 作为依赖

  // 尝试从 localStorage 加载 token 和用户数据
  useEffect(() => {
    console.log('AuthContext: useEffect triggered');
    const storedToken = localStorage.getItem('access_token');
    console.log('AuthContext: Stored token:', storedToken ? 'present' : 'absent');
    if (storedToken) {
      setToken(storedToken);
      // 尝试获取用户数据
      fetchUserData(storedToken); // 现在 fetchUserData 是一个稳定的函数
    } else {
      setIsLoading(false); // 没有token，认证加载完成
      console.log('AuthContext: No token found, isLoading set to false');
    }
  }, [fetchUserData, setToken]); // 将 fetchUserData 和 setToken 添加到依赖数组

  const login = async (newToken: string) => {
    console.log('AuthContext: login called');
    localStorage.setItem('access_token', newToken);
    setToken(newToken);
    await fetchUserData(newToken);
  };

  const logout = () => {
    console.log('AuthContext: logout called');
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
    setIsLoading(false);
    // 重定向到登录页面，这里可以根据实际路由库来做
    window.location.href = '/login'; 
  };

  console.log('AuthContext: Render with token:', token ? 'present' : 'absent', 'user:', user ? user.username : 'null', 'isLoading:', isLoading);

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