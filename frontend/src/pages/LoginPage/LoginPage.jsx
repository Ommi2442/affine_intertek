import React, { useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Button,
} from '@mui/material';

import { useMsal, useIsAuthenticated } from '@azure/msal-react';

import {
  InteractionStatus,
  InteractionRequiredAuthError,
} from '@azure/msal-browser';

import { useNavigate } from 'react-router-dom';
import { ssouserdataApi } from '../../redux/api/loginApi';

export default function LoginPage() {
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const navigate = useNavigate();

  // ------------------------------------------------------
  //  SAFE POST-REDIRECT PROCESSING
  // ------------------------------------------------------
  useEffect(() => {
    if (inProgress === InteractionStatus.None && isAuthenticated) {
      handleSSOAfterRedirect();
    }
  }, [inProgress, isAuthenticated]);

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

      //  Store values (kept as you requested)
      localStorage.setItem('accessToken', response.accessToken);
      localStorage.setItem('email', userAccount.username);
      localStorage.setItem('name', userAccount.name);
      localStorage.setItem('logintype', 'sso');

      const userInfo = {
        name: userAccount.name,
        email: userAccount.username,
        accessToken: response.accessToken,
        expirationTime: response.expiresOn,
        lastLoggedIn: new Date().toISOString(),
      };

      const backendResponse = await ssouserdataApi(userInfo);

      if (backendResponse?.data?.status === 'success') {
        localStorage.setItem('role', backendResponse.data.role);
        navigate('/dashboard');
      }
    } catch (error) {
      console.error('Post-redirect SSO processing failed:', error);

      //  REQUIRED fallback
      if (error instanceof InteractionRequiredAuthError) {
        instance.loginRedirect({ scopes: ['User.Read'] });
      }
    }
  };

  // ------------------------------------------------------
  //  LOGIN BUTTON HANDLER
  // ------------------------------------------------------
  // const submitHandler = () => {
  //   const accounts = instance.getAllAccounts();

  //   if (accounts.length > 0) {
  //     instance.setActiveAccount(accounts[0]);
  //     navigate("/dashboard");
  //     return;
  //   }

  //   instance.loginRedirect({
  //     scopes: ["User.Read"],
  //   });
  // };

  const submitHandler = async () => {
    const accounts = instance.getAllAccounts();

    if (accounts.length > 0) {
      const account = accounts[0];
      instance.setActiveAccount(account);

      try {
        const response = await instance.acquireTokenSilent({
          scopes: ['User.Read'],
          account,
        });

        // Store values (same as post-redirect flow)
        localStorage.setItem('accessToken', response.accessToken);
        localStorage.setItem('email', account.username);
        localStorage.setItem('name', account.name);
        localStorage.setItem('logintype', 'sso');

        navigate('/dashboard');
        return;
      } catch (error) {
        if (error instanceof InteractionRequiredAuthError) {
          return instance.loginRedirect({ scopes: ['User.Read'] });
        }
        console.error('Silent login failed:', error);
      }
    }

    instance.loginRedirect({ scopes: ['User.Read'] });
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
              width: '100%',
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
