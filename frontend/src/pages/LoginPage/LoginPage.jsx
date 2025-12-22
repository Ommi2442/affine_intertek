import React, { useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Button,
} from '@mui/material';

import { useMsal } from '@azure/msal-react';
import { InteractionStatus } from '@azure/msal-browser';
import { useNavigate } from 'react-router-dom';
import { ssouserdataApi } from '../../redux/api/loginApi';

const LOGIN_CLICKED_KEY = 'LOGIN_CLICKED';

export default function LoginPage() {
  const { instance, inProgress } = useMsal();
  const navigate = useNavigate();

  /* ------------------------------------------------------
     HANDLE REDIRECT (ONLY AFTER LOGIN BUTTON CLICK)
  ------------------------------------------------------ */
  useEffect(() => {
    if (inProgress !== InteractionStatus.None) return;

    const loginClicked = sessionStorage.getItem(LOGIN_CLICKED_KEY);
    if (!loginClicked) return;

    const accounts = instance.getAllAccounts();
    if (!accounts.length) return;

    handleSSOAfterRedirect();
    sessionStorage.removeItem(LOGIN_CLICKED_KEY);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inProgress]);

  /* ------------------------------------------------------
     LOGOUT ONLY ON REAL TAB CLOSE (NOT REDIRECT)
  ------------------------------------------------------ */
  useEffect(() => {
    const handlePageHide = (event) => {
      // If redirecting to Microsoft, DO NOT logout
      if (sessionStorage.getItem(LOGIN_CLICKED_KEY)) return;

      sessionStorage.clear();
      localStorage.clear();
      instance.setActiveAccount(null);
    };

    window.addEventListener('pagehide', handlePageHide);
    return () => {
      window.removeEventListener('pagehide', handlePageHide);
    };
  }, [instance]);

  /* ------------------------------------------------------
     POST-REDIRECT PROCESSING
  ------------------------------------------------------ */
  const handleSSOAfterRedirect = async () => {
    try {
      const accounts = instance.getAllAccounts();
      if (!accounts.length) return;

      const userAccount = accounts[0];
      instance.setActiveAccount(userAccount);

      const response = await instance.acquireTokenSilent({
        scopes: ['User.Read'],
        account: userAccount,
      });

      localStorage.setItem('accessToken', response.accessToken);
      localStorage.setItem('email', userAccount.username);
      localStorage.setItem('name', userAccount.name);
      localStorage.setItem('logintype', 'sso');

      const backendResponse = await ssouserdataApi({
        name: userAccount.name,
        email: userAccount.username,
        accessToken: response.accessToken,
        expirationTime: response.expiresOn,
        lastLoggedIn: new Date().toISOString(),
      });

      if (backendResponse?.data?.status === 'success') {
        localStorage.setItem('role', backendResponse.data.role);
        navigate('/dashboard', { replace: true });
      }
    } catch (error) {
      console.error('Post-redirect SSO processing failed:', error);
    }
  };

  /* ------------------------------------------------------
     LOGIN BUTTON — ALWAYS EMAIL + PASSWORD
  ------------------------------------------------------ */
  const submitHandler = () => {
    sessionStorage.clear();
    localStorage.clear();
    instance.setActiveAccount(null);

    sessionStorage.setItem(LOGIN_CLICKED_KEY, 'true');

    instance.loginRedirect({
      scopes: ['User.Read'],
      prompt: 'login', // ALWAYS ask email + password
    });
  };

  return (
    <Grid
      container
      spacing={1}
      sx={{
        width: '100%',
        height: '100%',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 4,
        backgroundColor: '#f0f0f0',
      }}
    >
      {/* LEFT CARD */}
      <Grid
        item
        xs={12}
        md={6}
        sx={{
          width: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 2,
          height: '100%',
        }}
      >
        <Box
          sx={{
            position: 'relative',
            width: '100%',
            height: '105%',
            overflow: 'hidden',
            borderRadius: 2,
          }}
        >
          <Box
            component="img"
            src="/images/intertek_login_image.png"
            alt="Login Illustration"
            sx={{
              width: '90%',
              height: '100%',
              objectFit: 'fill',
              borderRadius: 2,
            }}
          />
        </Box>
      </Grid>

      {/* RIGHT CARD */}
      <Grid item xs={12} md={6} sx={{ width: '35%', height: '100%' }}>
        <Card
          sx={{
            width: '100%',
            height: '100%',
            borderRadius: '10px',
            backgroundColor: '#FFFFFF',
            paddingRight: '10%',
            paddingLeft: '2%',
          }}
        >
          <CardContent
            sx={{ width: '100%', height: '100%', paddingRight: '8%' }}
          >
            <Grid sx={{ textAlign: 'center' }}>
              <Box
                component="img"
                src="/images/intertek_logo.svg"
                alt="Logo"
                sx={{
                  width: '30%',
                  marginTop: '26px',
                }}
              />
            </Grid>

            <Grid sx={{ height: '100%', paddingTop: '30%' }}>
              <Typography
                sx={{
                  fontWeight: 550,
                  paddingBottom: '2%',
                  paddingTop: '3%',
                  fontSize: '1.3rem',
                  textAlign: 'center',
                }}
              >
                Log In
              </Typography>

              <Button
                fullWidth
                variant="contained"
                size="small"
                sx={{
                  mt: 2,
                  mb: 2,
                  py: 1,
                  fontWeight: 'bold',
                  backgroundColor: '#0c0c0cff',
                  '&:hover': { backgroundColor: '#212222ff' },
                }}
                onClick={submitHandler}
              >
                <Box
                  component="img"
                  src="/images/microsoft_logo.png"
                  alt="Microsoft Logo"
                  sx={{
                    width: '4%',
                    height: '4%',
                    pr: 1,
                  }}
                />
                Login with Microsoft SSO
              </Button>
            </Grid>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}
