import { Box, Button, Typography } from '@mui/material';
import React from 'react';
export const RenderPage6Images = ({
  item,
  tIdx,
  iIdx,
  editMode,
  setTables,
}) => {
  console.log('item', item);
  const images = Array.isArray(item.image_upload_url)
    ? item.image_upload_url
    : [];

  const updateImages = (newImages) => {
    setTables((prev) => {
      const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
      next[tIdx].Items[iIdx] = {
        ...next[tIdx].Items[iIdx],
        image_upload_url: newImages,
      };
      return next;
    });
  };

  const handleTitleChange = (imgIdx, value) => {
    const updated = images.map((img, i) =>
      i === imgIdx ? { ...img, title: value } : img
    );
    updateImages(updated);
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
          {/* TITLE */}
          {editMode ? (
            <input
              type="text"
              value={img.title || ''}
              onChange={(e) => handleTitleChange(imgIdx, e.target.value)}
              className="dt-textarea"
              style={{ width: '100%', marginBottom: 6 }}
            />
          ) : (
            <Typography sx={{ fontWeight: 600, mb: 1 }}>{img.title}</Typography>
          )}

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
