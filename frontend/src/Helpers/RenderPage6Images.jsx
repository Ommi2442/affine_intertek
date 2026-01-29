import { Box, Button, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { uploadReportImage } from '../redux/api/uploadReportImage';

export const RenderPage6Images = ({
  item,
  tIdx,
  iIdx,
  editMode,
  setTables,
}) => {
  const images = Array.isArray(item.marking_urls) ? item.marking_urls : [];
  const MAX_IMAGES = 2;
  const [project_id, setProjectId] = useState('');

  useEffect(() => {
    setProjectId(localStorage.getItem('projectId'));
  }, []);

  const updateImages = (newImages) => {
    setTables((prev) => {
      const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
      next[tIdx].Items[iIdx] = {
        ...next[tIdx].Items[iIdx],
        marking_urls: newImages,
        is_user_modified: true,
      };
      return next;
    });
  };

  // REPLACE IMAGE

  const handleReplaceImage = async (imgIdx, file) => {
    if (!file) return;

    const existingImage = images[imgIdx];
    if (!existingImage) return;

    try {
      const res = await uploadReportImage(project_id, 'trf', [file]);

      const uploadedUrl = res?.blob_url;
      if (!uploadedUrl) return;

      // Replace ONLY the clicked index
      const updatedImages = images.map((img, i) =>
        i === imgIdx ? { id: img.id ?? Date.now(), url: uploadedUrl } : img
      );

      updateImages(updatedImages);
    } catch (err) {
      console.error('Replace image upload failed', err);
    }
  };

  //  DELETE IMAGE

  const handleDeleteImage = (imgIdx) => {
    updateImages(images.filter((_, i) => i !== imgIdx));
  };

  // ADD IMAGE

  const handleAddImage = async (file) => {
    if (!file || images.length >= MAX_IMAGES) return;

    const tempId = Date.now();

    try {
      const res = await uploadReportImage(project_id, 'trf', [file]);
      console.log('res', res);
      const uploadedUrl = res?.blob_url;

      if (!uploadedUrl) return;

      updateImages([...images, { id: tempId, url: uploadedUrl }]);
    } catch (err) {
      console.error('Image upload failed', err);
    }
  };

  const canAddImage = editMode && images.length < MAX_IMAGES;

  return (
    <Box sx={{ mt: 2 }}>
      {/* EXISTING IMAGES */}
      {images.map((img, imgIdx) => (
        <Box key={img.id ?? imgIdx} sx={{ mb: 3 }}>
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

      {/* ADD IMAGE */}
      {editMode && (
        <Box sx={{ mt: 1 }}>
          <Button
            variant="contained"
            component="label"
            size="small"
            disabled={!canAddImage}
          >
            Add Image
            <input
              type="file"
              hidden
              accept="image/*"
              onChange={(e) =>
                e.target.files && handleAddImage(e.target.files[0])
              }
            />
          </Button>

          {images.length >= MAX_IMAGES && (
            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
              Maximum 2 images allowed
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
};
