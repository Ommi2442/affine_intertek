import React from 'react';
import { Box } from '@mui/material';

export const RenderImageThumbnails = ({ images, onClick }) => {
  if (!Array.isArray(images) || images.length === 0) return null;

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1,
        flexWrap: 'wrap',
        mt: 1,
      }}
    >
      {images.map((img, idx) => (
        <Box
          key={idx}
          component="img"
          src={img}
          alt={`thumb-${idx}`}
          onClick={() => onClick(img)}
          sx={{
            width: 70,
            height: 70,
            objectFit: 'cover',
            borderRadius: 1,
            cursor: 'pointer',
            border: '1px solid #ddd',
            transition: '0.2s',
            '&:hover': {
              transform: 'scale(1.05)',
            },
          }}
        />
      ))}
    </Box>
  );
};
