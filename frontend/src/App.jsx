import React, { useEffect } from 'react';
import {
  Navigate,
  RouterProvider,
  createBrowserRouter,
} from 'react-router-dom';
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
import CdrReportPage from './pages/ReportPage/CdrReportPage.jsx';
import LetterReportPage from './pages/ReportPage/LetterReportPage.jsx';
import UploadLetterFilePage from './pages/UploadFilePage/UploadLetterFilePage.jsx';

function App() {
  useEffect(() => {
    localStorage.setItem(
      'accessToken',
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ5b2dlc2guc2hhbm11a2hhcHBhQGFmZmluZS5haSIsInJvbGUiOjEsImV4cCI6MTc2OTY4MDQzOX0.9FT2BhekHQvvt6kprGVI1kblxrR3UxQ9AvCdqP5ArC8'
    );

    localStorage.setItem('email', 'yogesh.shanmukhappa@affine.ai');
    localStorage.setItem('name', 'Yogesh Shanmukhappa');
    localStorage.setItem('logintype', 'sso');
    localStorage.setItem('role', 1);
  }, []);
  const router = createBrowserRouter([
    // LOGIN PAGE
    { path: '/', element: <MainLayout /> },

    // MSAL REDIRECT HANDLER (IMPORTANT FIX)
    {
      path: '/redirect',
      element: <MainLayout />,
    },

    // Protected Layout (Navbar + Outlet)
    {
      path: '/',
      element: (
        // <MainLayout />
        // <ProtectedRoute>
        //   <BreadcrumbProvider>
        //     <MainLayout />
        //   </BreadcrumbProvider>
        // </ProtectedRoute>

        <BreadcrumbProvider>
          <MainLayout />
        </BreadcrumbProvider>
      ),
      children: [
        { index: true, element: <Dashboard /> },
        // { path: 'dashboard', element: <Dashboard /> },
        { path: 'create-project', element: <UploadFilePage /> },
        { path: 'create-project-letter', element: <UploadLetterFilePage /> },
        // REPORT ROUTES
        {
          path: 'report-page',
          children: [
            { index: true, element: <Navigate to="trf" replace /> },
            { path: 'trf', element: <ReportPage /> },
            { path: 'cdr', element: <CdrReportPage /> },
            { path: 'letter', element: <LetterReportPage /> },
            // { path: 'letter', element: <LetterPage /> },
          ],
        },
      ],
    },
    // CATCH-ALL ROUTE (IMPORTANT FIX)
    {
      path: '/dashboard',
      element: <Dashboard />,
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
