import React from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';

const CdrLoader = () => {
  return (
    <Box
      sx={{
        minHeight: '300px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        background: '#f9fafb',
        borderRadius: 2,
        border: '1px dashed #d0d7de',
      }}
    >
      <CircularProgress size={48} thickness={4} />

      <Typography sx={{ fontWeight: 600, fontSize: 16 }}>
        Generating CDR Report
      </Typography>

      <Typography sx={{ fontSize: 13, color: 'text.secondary' }}>
        This may take a few moments. Please don’t refresh the page.
      </Typography>
    </Box>
  );
};

export default CdrLoader;
