import React from 'react';
import { Navigate } from 'react-router-dom';
import { useMsal } from '@azure/msal-react';

const ProtectedRoute = ({ redirectTo, children }) => {
  const { accounts } = useMsal();

  const isLoggedIn = accounts && accounts.length > 0;

  return isLoggedIn ? children : <Navigate to={redirectTo} />;
};

export default ProtectedRoute;
