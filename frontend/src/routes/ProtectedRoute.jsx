import React from 'react';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ redirectTo = '/login', children }) => {
  const token = localStorage.getItem('accessToken');
  const loginType = localStorage.getItem('logintype');

  // 🔒 Only allow access if user explicitly logged in via button
  const isLoggedIn = Boolean(token && loginType === 'sso');

  if (!isLoggedIn) {
    return <Navigate to={redirectTo} replace />;
  }

  return children;
};

export default ProtectedRoute;
