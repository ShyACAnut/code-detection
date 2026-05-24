/**
 * 路由保护组件
 * ============
 * 
 * 这个组件用于保护需要认证的路由，确保只有已登录且具有相应权限的用户才能访问。
 * 
 * 主要功能：
 * 1. 检查用户是否已登录
 * 2. 验证用户角色权限
 * 3. 自动重定向未授权用户
 * 4. 提供加载状态显示
 * 
 * 使用场景：
 * - 保护需要登录的页面
 * - 限制特定角色的访问权限
 * - 实现基于角色的访问控制
 * 
 * 安全特性：
 * - 自动验证用户身份
 * - 角色权限检查
 * - 防止未授权访问
 */

import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

/**
 * 路由保护组件属性接口
 */
interface ProtectedRouteProps {
  children: React.ReactNode;  // 子组件内容
  allowedRoles?: Array<'student' | 'teacher' | 'dean' | 'admin'>;  // 允许访问的角色列表
}

/**
 * 路由保护组件
 * 
 * 功能：
 * - 检查用户登录状态
 * - 验证用户角色权限
 * - 自动重定向未授权用户
 * 
 * @param props - 组件属性，包含子组件和允许的角色列表
 * @returns 受保护的路由内容或重定向组件
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  // 从认证上下文中获取用户信息和加载状态
  const { user, isLoading } = useAuth();

  // 如果正在加载认证信息，显示加载状态
  if (isLoading) return <div>加载中...</div>;

  // 如果用户未登录，重定向到登录页面
  if (!user) return <Navigate to="/login" replace />;

  // 如果指定了允许的角色且用户角色不在其中，重定向到未授权页面
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  // 用户已登录且具有相应权限，渲染子组件
  return <>{children}</>;
};

export default ProtectedRoute;