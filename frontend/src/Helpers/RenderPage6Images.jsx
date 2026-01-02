import { Box, Button } from '@mui/material';
import React from 'react';

export const RenderPage6Images = ({
  item,
  tIdx,
  iIdx,
  editMode,
  setTables,
}) => {
  const images = Array.isArray(item.marking_urls) ? item.marking_urls : [];

  const updateImages = (newImages) => {
    setTables((prev) => {
      const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
      next[tIdx].Items[iIdx] = {
        ...next[tIdx].Items[iIdx],
        marking_urls: newImages,
      };
      return next;
    });
  };

  const handleReplaceImage = (imgIdx, file) => {
    const newUrl = URL.createObjectURL(file);
    const updated = images.map((img, i) =>
      i === imgIdx ? { ...img, url: newUrl } : img
    );
    updateImages(updated);
  };

  const handleDeleteImage = (imgIdx) => {
    const updated = images.filter((_, i) => i !== imgIdx);
    updateImages(updated);
  };

  return (
    <Box sx={{ mt: 2 }}>
      {images.map((img, imgIdx) => (
        <Box key={img.id ?? imgIdx} sx={{ mb: 3 }}>
          {/* IMAGE */}
          <Box
            component="img"
            src={img.url}
            sx={{
              maxWidth: '100%',
              maxHeight: 280,
              border: '1px solid #ccc',
              borderRadius: 1,
            }}
          />

          {/* ACTIONS */}
          {editMode && (
            <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
              <Button variant="outlined" component="label" size="small">
                Browse
                <input
                  type="file"
                  hidden
                  accept="image/*"
                  onChange={(e) =>
                    e.target.files &&
                    handleReplaceImage(imgIdx, e.target.files[0])
                  }
                />
              </Button>

              <Button
                variant="outlined"
                color="error"
                size="small"
                onClick={() => handleDeleteImage(imgIdx)}
              >
                Delete
              </Button>
            </Box>
          )}
        </Box>
      ))}
    </Box>
  );
};
