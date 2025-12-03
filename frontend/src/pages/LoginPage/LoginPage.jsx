import React, { useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Button,
} from '@mui/material';

import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { useNavigate } from "react-router-dom";
import LoginService from "./LoginService";

export default function LoginPage() {
  const { instance } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const Navigate = useNavigate();

  // ------------------------------------------------------
  // RUN AFTER MICROSOFT REDIRECT (FIRST TIME LOGIN)
  // ------------------------------------------------------
  useEffect(() => {
    if (isAuthenticated) {
      handleSSOAfterRedirect();
    }
  }, [isAuthenticated]);

  const handleSSOAfterRedirect = async () => {
    try {
      const accounts = instance.getAllAccounts();
      if (accounts.length === 0) return;

      const userAccount = accounts[0];

      const silentRequest = {
        scopes: ["User.Read"],
        account: userAccount,
      };

      const response = await instance.acquireTokenSilent(silentRequest);

      // Store everything in localStorage
      localStorage.setItem("msalResponse", JSON.stringify(response));
      localStorage.setItem("accessToken", response.accessToken);
      localStorage.setItem("email", response.account.username);
      localStorage.setItem("name", response.account.name);
      localStorage.setItem("logintype", "sso");

      const userInfo = {
        name: userAccount.name,
        email: userAccount.username,
        accessToken: response.accessToken,
        expirationTime: response.expiresOn,
        lastLoggedIn: new Date().toISOString(),
      };

      const backendResponse = await LoginService.ssouserdata(userInfo);

      if (backendResponse?.data?.status === "success") {
        localStorage.setItem("role", backendResponse.data.role);
        Navigate("/dashboard");
      }

    } catch (error) {
      console.error("Post-redirect SSO processing failed:", error);
    }
  };

  // ------------------------------------------------------
  // CLICKING LOGIN BUTTON (ALSO WORKS FOR 2nd LOGIN)
  // ------------------------------------------------------
  const submitHandler = async () => {
    try {
      const accounts = instance.getAllAccounts();

      if (accounts.length > 0) {
        const userAccount = accounts[0];

        const silentRequest = {
          scopes: ["User.Read"],
          account: userAccount,
        };

        try {
          const response = await instance.acquireTokenSilent(silentRequest);

          localStorage.setItem("msalResponse", JSON.stringify(response));
          localStorage.setItem("accessToken", response.accessToken);
          localStorage.setItem("email", response.account.username);
          localStorage.setItem("name", response.account.name);
          localStorage.setItem("logintype", "sso");

          const userInfo = {
            name: userAccount.name,
            email: userAccount.username,
            accessToken: response.accessToken,
            expirationTime: response.expiresOn,
            lastLoggedIn: new Date().toISOString(),
          };

          const backendResponse = await LoginService.ssouserdata(userInfo);

          if (backendResponse?.data?.status === "success") {
            localStorage.setItem("role", backendResponse.data.role);
            localStorage.setItem("email", backendResponse.data.email);
            Navigate("/dashboard");
          }

          return;

        } catch (silentError) {
          console.error("Silent login failed:", silentError);
          // DO NOT redirect on failure
          return;
        }
      }

      // First-time login
      await instance.loginRedirect({
        scopes: ["User.Read"],
      });

    } catch (error) {
      console.error("Login failed:", error);
    }
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
            height: '100%',
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
              objectFit: 'cover',
              borderRadius: 2,
            }}
          />

          <Box
            component="img"
            src="/images/intertek_square_logo.png"
            alt="Overlay"
            sx={{
              position: 'absolute',
              top: 0,
              left: 35,
              width: '25%',
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
            backgroundColor: '#FFFFFF',
            paddingRight: '10%',
            paddingLeft: '2%',
          }}
        >
          <CardContent sx={{ width: '100%', height: '100%', paddingRight: '8%' }}>
            <Grid sx={{ textAlign: 'left' }}>
              <Box
                component="img"
                src="/images/intertek_logo.svg"
                alt="Login Illustration"
                sx={{
                  width: '25%',
                  height: '25%',
                  objectFit: 'cover',
                  borderRadius: '1%',
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
                    objectFit: 'cover',
                    borderRadius: '1%',
                  }}
                />{" "}
                Login with Microsoft SSO
              </Button>
            </Grid>
          </CardContent>
        </Card>
      </Grid>

    </Grid>
  );
}
