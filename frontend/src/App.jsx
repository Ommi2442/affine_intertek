import React from 'react';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import { MsalProvider } from '@azure/msal-react';

import { msalInstance } from './msalInstance';

import LoginPage from './pages/LoginPage/LoginPage';
import ProtectedRoute from './routes/ProtectedRoute';

import MainLayout from './layout/MainLayout';
import Dashboard from './pages/Dashboard/Dashboard';
import UploadFilePage from './pages/UploadFilePage/UploadFilePage';
import ReportPage from './pages/ReportPage/ReportPage';
import GlobalLoader from './loader/GlobalLoader.jsx';
import './loader/axiosInterceptor';
import { BreadcrumbProvider } from './components/BreadCrumbContext';

function App() {
  const router = createBrowserRouter([
    // LOGIN PAGE
    { path: '/', element: <LoginPage /> },

    // MSAL REDIRECT HANDLER (IMPORTANT FIX)
    {
      path: '/redirect',
      element: <LoginPage />,
    },

    // Protected Layout (Navbar + Outlet)
    {
      path: '/',
      element: (
        <ProtectedRoute>
          <BreadcrumbProvider>
            <MainLayout />
          </BreadcrumbProvider>
        </ProtectedRoute>
      ),
      children: [
        { path: 'dashboard', element: <Dashboard /> },
        { path: 'create-project', element: <UploadFilePage /> },
        { path: 'report-page', element: <ReportPage /> },
      ],
    },
    // CATCH-ALL ROUTE (IMPORTANT FIX)
    {
      path: '*',
      element: <LoginPage />,
    },
  ]);

  return (
    <MsalProvider instance={msalInstance}>
      <GlobalLoader />
      <RouterProvider router={router} />
    </MsalProvider>
  );
}

export default App;
