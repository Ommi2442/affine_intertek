import React, { useEffect, useState } from 'react';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import { MsalProvider } from '@azure/msal-react';

import { msalInstance } from './msalInstance';

import LoginPage from './pages/LoginPage/LoginPage';
import ProtectedRoute from './routes/ProtectedRoute';

import MainLayout from './layout/MainLayout';
import HomePage from './pages/HomePage/HomePage';
import UploadFilePage from './pages/UploadFilePage/UploadFilePage';
import ReportPage from './pages/ReportPage/ReportPage';
import Dashboard from './pages/Dashboard/Dashboard';

function App() {
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const init = async () => {
      await msalInstance.initialize();
      await msalInstance.handleRedirectPromise();
      setInitialized(true);
    };
    init();
  }, []);

  const router = createBrowserRouter([
    // ❌ Login Page: NO NAVBAR
    { path: '/', element: <LoginPage msalInstance={msalInstance} /> },

    // Protected Layout (Navbar + Outlet)
    {
      path: '/',
      element: (
        <ProtectedRoute>
          <MainLayout />
        </ProtectedRoute>
      ),
      children: [
        { path: 'dashboard', element: <Dashboard /> },
        { path: 'create-project', element: <UploadFilePage /> },
        { path: 'report-page', element: <ReportPage /> },
      ],
    },
  ]);

  return (
    initialized && (
      <MsalProvider instance={msalInstance}>
        <RouterProvider router={router} />
      </MsalProvider>
    )
  );
}

export default App;
