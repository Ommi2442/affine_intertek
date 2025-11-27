import React from 'react';
import { useSnapshot } from 'valtio';
import { loaderStore } from './loaderStore';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';

export default function GlobalLoader() {
  const snap = useSnapshot(loaderStore);

  if (!snap.loading) return null;

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'rgba(255,255,255,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
    >
      <CircularProgress size={60} />
    </Box>
  );
}
