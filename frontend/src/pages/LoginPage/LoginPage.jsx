import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  TextField,
  Button,
  Divider,
} from '@mui/material';

export default function LoginPage() {
  return (
    <Grid
      container
      spacing={2}
      sx={{
        width: '100%',
        height: '100%',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 4,
      }}
    >
      {/* LEFT CARD */}
      <Grid
        item
        xs={12}
        md={6}
        sx={{
          width: '60%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 2,
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
            src="/images/writing_image.jpg" // big image
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
            src="/images/intertek_square_logo.png" // small image
            alt="Overlay"
            sx={{
              position: 'absolute',
              top: 0, // distance from bottom
              left: 35, // distance from right
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
          <CardContent
            sx={{ width: '100%', height: '100%', paddingRight: '8%' }}
          >
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

            <Grid sx={{ height: '100%' }}>
              <Typography
                sx={{
                  fontWeight: 550,
                  paddingBottom: '10%',
                  paddingTop: '10%',
                  fontSize: '1.3rem',
                }}
              >
                Log In
              </Typography>
              <TextField
                fullWidth
                label="Email ID"
                variant="outlined"
                margin="normal"
                size="small"
              />
              <Typography
                sx={{
                  color: 'red',
                  textAlign: 'left',
                  paddingLeft: '2%',
                  mb: 2,
                  fontSize: '0.7rem',
                }}
              >
                Please enter your email address using the format
                name@example.com
              </Typography>
              <Button
                fullWidth
                variant="contained"
                size="small"
                sx={{
                  mt: 2,
                  mb: 2,
                  py: 1.2,
                  fontWeight: 'bold',
                  backgroundColor: '#0d99ff',
                  '&:hover': { backgroundColor: '#125ea3' },
                }}
              >
                Sign In
              </Button>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  width: '100%',
                  my: 1.5, // margin top & bottom
                }}
              >
                <Divider sx={{ flexGrow: 1 }} />
                <Typography
                  sx={{
                    mx: 2, // space between lines and text
                    color: 'gray',
                    fontSize: '14px',
                    fontWeight: 500,
                  }}
                >
                  or
                </Typography>
                <Divider sx={{ flexGrow: 1 }} />
              </Box>
              <Typography
                variant="body2"
                sx={{ textAlign: 'center', color: 'gray', paddingBottom: '5%' }}
              >
                Continue with your{' '}
                <a
                  href="#"
                  style={{ color: '#1976d2', textDecoration: 'underline' }}
                >
                  work email - SSO login
                </a>
              </Typography>
            </Grid>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}
