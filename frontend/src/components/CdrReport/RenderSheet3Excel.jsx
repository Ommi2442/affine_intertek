/* eslint-disable */
import React from 'react';
import { Box, Typography } from '@mui/material';

/* ---------------- COMPONENT ---------------- */
const RenderSheet3Excel = ({ sheet }) => {
  /* ✅ SAFETY GUARD */
  if (!sheet || !Array.isArray(sheet.Items)) {
    return null;
  }

  return (
    <Box>
      {sheet.Items.map((item, idx) => (
        <Box key={idx} sx={{ mb: 3 }}>
          <Typography fontWeight={600}>{item.field}</Typography>

          {item.photo_path && (
            <Box
              component="img"
              src={item.photo_path}
              sx={{
                maxWidth: '100%',
                maxHeight: 300,
                border: '1px solid #ccc',
                mt: 1,
              }}
            />
          )}
        </Box>
      ))}
    </Box>
  );
};

export default RenderSheet3Excel;
