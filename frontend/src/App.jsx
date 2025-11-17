import React, { useEffect, useState } from 'react';
import './App.css';
import HomePage from './pages/HomePage/HomePage';
import Navbar from './components/NavBar';
import { PublicClientApplication } from '@azure/msal-browser';
import msalConfig from './pages/LoginPage/config/msalConfig';
import LoginPage from './pages/LoginPage/LoginPage';
import ProtectedRoute from './routes/ProtectedRoute';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { MsalProvider } from '@azure/msal-react';

function App() {
  const msalInstance = new PublicClientApplication(msalConfig);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const initializeMsal = async () => {
      await msalInstance.initialize();
      await msalInstance.handleRedirectPromise();
      setInitialized(true);
    };

    initializeMsal();
  }, []);

  function signOutClickHandler() {
    let logintype = localStorage.getItem('logintype');
    sessionStorage.clear();
    localStorage.clear();
    if (logintype == 'sso') {
      msalInstance.logoutRedirect();
    } else {
      window.location.href = '/login';
    }
  }

  const router = createBrowserRouter([
    {
      path: '/',
      element: <LoginPage msalInstance={msalInstance} />,
    },
    {
      path: '/login',
      element: <LoginPage msalInstance={msalInstance} />,
    },
    {
      path: 'layout',
      element: (
        <ProtectedRoute redirectTo={'/'}>
          <Navbar signOutClickHandler={signOutClickHandler} />
        </ProtectedRoute>
      ),
      children: [{}],
    },
  ]);

  return (
    <>
      {initialized && (
        <MsalProvider instance={msalInstance}>
          <RouterProvider router={router} />
        </MsalProvider>
      )}
    </>
  );
}

export default App;
