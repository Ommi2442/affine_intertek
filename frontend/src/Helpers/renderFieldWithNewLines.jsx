import React from 'react';
import { Typography } from '@mui/material';

export const renderFieldWithNewLines = (text) => {
  if (!text) return null;

  return text.split('\n').map((line, idx) => (
    <Typography
      key={idx}
      sx={{
        fontSize: 14,
        mb: 2, // 1 line gap
        whiteSpace: 'pre-wrap',
      }}
    >
      {line}
    </Typography>
  ));
};
