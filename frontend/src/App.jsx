import React, { useEffect, useState } from 'react';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import { MsalProvider } from '@azure/msal-react';

import { msalInstance } from './msalInstance'; // ✅ using shared instance
import LoginPage from './pages/LoginPage/LoginPage';
import Navbar from './components/NavBar';
import ProtectedRoute from './routes/ProtectedRoute';
import HomePage from './pages/HomePage/HomePage';
import UploadFilePage from './pages/UploadFilePage/UploadFilePage';
import BasicModal from './components/Modal';

function App() {
  const [initialized, setInitialized] = useState(false);
  console.log('msalApp', msalInstance);
  useEffect(() => {
    const init = async () => {
      await msalInstance.initialize();
      await msalInstance.handleRedirectPromise();
      setInitialized(true);
    };
    init();
  }, []);

  const router = createBrowserRouter([
    { path: '/', element: <LoginPage msalInstance={msalInstance} /> },
    { path: '/upload', element: <UploadFilePage /> },
    { path: '/modal', element: <BasicModal /> },

    {
      path: '/layout',
      element: (
        <ProtectedRoute redirectTo="/login">
          <Navbar />
        </ProtectedRoute>
      ),
    },
  ]);

  return (
    initialized && (
      <MsalProvider instance={msalInstance}>
        {/* <HomePage /> */}
        <div style={{ width: '100%', height: '100%' }}>
          <RouterProvider router={router} />
        </div>
      </MsalProvider>
    )
  );
}

export default App;
