import React, { useState } from 'react';
import {
  Box,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

export const RenderImageThumbnails = ({ images = [] }) => {
  const [openImagePreview, setOpenImagePreview] = useState(false);
  const [activeImageUrl, setActiveImageUrl] = useState(null);

  if (!Array.isArray(images) || images.length === 0) return null;

  return (
    <>
      <Box
        sx={{
          display: 'flex',
          gap: '6px',
          mb: 1,
          flexWrap: 'wrap',
        }}
      >
        {images.slice(0, 5).map((img, idx) => (
          <Box
            key={idx}
            sx={{
              width: 30,
              height: 30,
              borderRadius: 1,
              overflow: 'hidden',
              border: '1px solid #ddd',
              cursor: 'pointer',
              flexShrink: 0,
            }}
            title={`Image ${idx + 1}`}
            onClick={() => {
              setActiveImageUrl(img.url);
              setOpenImagePreview(true);
            }}
          >
            <img
              src={img.url}
              alt={`support-${idx}`}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                display: 'block',
              }}
            />
          </Box>
        ))}
      </Box>

      {/* 🔍 Image Preview Modal */}
      <Dialog
        open={openImagePreview}
        onClose={() => {
          setOpenImagePreview(false);
          setActiveImageUrl(null);
        }}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          Image Preview
          <IconButton
            onClick={() => {
              setOpenImagePreview(false);
              setActiveImageUrl(null);
            }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        <DialogContent
          dividers
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            background: '#000',
            p: 2,
          }}
        >
          {activeImageUrl && (
            <img
              src={activeImageUrl}
              alt="preview"
              style={{
                maxWidth: '100%',
                maxHeight: '70vh',
                objectFit: 'contain',
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};
