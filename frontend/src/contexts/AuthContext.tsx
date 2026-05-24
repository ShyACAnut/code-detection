/**
 * 认证上下文组件
 * ==============
 * 
 * 这个组件提供了全局的认证状态管理，包括用户登录、登出和权限验证。
 * 
 * 主要功能：
 * 1. 管理用户登录状态
 * 2. 存储和验证JWT令牌
 * 3. 提供登录和登出方法
 * 4. 自动获取用户信息
 * 5. 全局权限控制
 * 
 * 使用场景：
 * - 全局用户状态管理
 * - 路由权限控制
 * - API请求认证
 * - 用户信息显示
 * 
 * 安全特性：
 * - JWT令牌存储在localStorage
 * - 自动验证令牌有效性
 * - 登出时清除敏感信息
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import api, { setAuthToken } from '../api/client';

/**
 * 用户信息接口
 */
interface User {
  id: number;  // 用户ID
  username: string;  // 用户名
  email: string;  // 邮箱
  role: 'student' | 'teacher' | 'dean' | 'admin';  // 用户角色
  created_at?: string;  // 创建时间（可选）
}

/**
 * 认证上下文类型接口
 */
interface AuthContextType {
  user: User | null;  // 当前用户信息
  token: string | null;  // JWT访问令牌
  login: (username: string, password: string) => Promise<void>;  // 登录方法
  logout: () => void;  // 登出方法
  isLoading: boolean;  // 加载状态
}

// 创建认证上下文
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * 认证提供者组件
 * 
 * 功能：
 * - 提供全局认证状态
 * - 管理用户登录和登出
 * - 自动获取和验证用户信息
 * - 处理JWT令牌的存储和验证
 * 
 * @param props - 组件属性，包含子组件
 * @returns 认证上下文提供者
 */
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 用户状态管理
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState(true);

  // ============================================================================
  // Token监听和用户信息获取
  // ============================================================================
  // 监听token变化，自动获取或清除用户信息
  useEffect(() => {
    let isMounted = true; // 防止组件卸载后更新状态

    /**
     * 获取用户信息函数
     */
    const fetchUser = async () => {
      try {
        // 调用API获取当前用户信息
        const response = await api.get('/auth/me');
        if (isMounted) {
          setUser(response.data);
        }
      } catch (error) {
        console.error('Failed to fetch user', error);
        // token无效，执行登出
        if (isMounted) {
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
          setAuthToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    // 如果存在token，设置认证头并获取用户信息
    if (token) {
      setIsLoading(true);
      setAuthToken(token);
      fetchUser();
    } else {
      // 没有token，清除用户信息
      setAuthToken(null);
      setUser(null);
      setIsLoading(false);
    }

    // 清理函数：组件卸载时设置标志
    return () => {
      isMounted = false;
    };
  }, [token]); // 只依赖token，不会造成循环

  // ============================================================================
  // 登录方法
  // ============================================================================
  /**
   * 用户登录方法
   * 
   * @param username - 用户名
   * @param password - 密码
   * @throws 登录失败时抛出异常
   */
  const login = async (username: string, password: string) => {
    // 创建URLSearchParams来发送x-www-form-urlencoded格式
    // OAuth2PasswordRequestForm 期望的格式
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/auth/token', formData);
    const { access_token } = response.data;
    
    // 存储token并更新状态
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setAuthToken(access_token);
    // 注意：用户信息会由上面的useEffect自动获取
  };

  // ============================================================================
  // 登出方法
  // ============================================================================
  /**
   * 用户登出方法
   * 清除所有认证信息和用户数据
   */
  const logout = () => {
    // 清除本地存储的token
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setAuthToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};