/* eslint-disable */
import React, { useEffect, useState } from 'react';
import { Box, IconButton, Button, Typography } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import AddPhotoAlternateIcon from '@mui/icons-material/AddPhotoAlternate';
import { uploadReportImage } from '../../../redux/api/uploadReportImage';

const LetterPhotoSection = ({ item, editMode, onChange }) => {
  if (!item || item.is_photo !== true) return null;

  const [project_id, setProjectId] = useState('');
  const photos = Array.isArray(item.nonConforming_urls)
    ? item.nonConforming_urls
    : [];

  useEffect(() => {
    setProjectId(localStorage.getItem('projectId'));
  }, []);

  /* -------- ADD PHOTO -------- */
  const addPhoto = async (file) => {
    const res = await uploadReportImage(project_id, 'letter', [file]);

    const uploadedUrl = res?.blob_url;
    if (!uploadedUrl) return;

    item.nonConforming_urls = [...photos, { id: Date.now(), url: uploadedUrl }];
    onChange?.();
  };

  /* -------- REPLACE PHOTO -------- */
  const replacePhoto = async (index, file) => {
    const res = await uploadReportImage(project_id, 'letter', [file]);
    const uploadedUrl = res?.blob_url;
    if (!uploadedUrl) return;

    const next = [...photos];
    next[index] = { ...next[index], url: uploadedUrl };
    item.nonConforming_urls = next;
    onChange?.();
  };

  /* -------- DELETE PHOTO -------- */
  const deletePhoto = (index) => {
    item.nonConforming_urls = photos.filter((_, i) => i !== index);
    onChange?.();
  };

  /* -------- FILE PICKER -------- */
  const FileInput = ({ onPick }) => (
    <input
      hidden
      type="file"
      accept="image/*"
      onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) onPick(file);
        e.target.value = '';
      }}
    />
  );

  return (
    <Box sx={{ mt: 2 }}>
      <Typography fontWeight={600} sx={{ mb: 1 }}>
        Photographs
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        {photos.map((photo, index) => (
          <Box
            key={photo.id}
            sx={{
              position: 'relative',
              width: 180,
              height: 120,
              border: '1px solid #ccc',
              borderRadius: 1,
              overflow: 'hidden',
            }}
          >
            <img
              src={photo.url}
              alt={`photo-${index}`}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />

            {editMode && (
              <Box
                sx={{
                  position: 'absolute',
                  top: 4,
                  right: 4,
                  display: 'flex',
                  gap: 0.5,
                  background: 'rgba(255,255,255,0.8)',
                  borderRadius: 1,
                }}
              >
                {/* REPLACE */}
                <IconButton component="label" size="small">
                  <EditIcon fontSize="small" />
                  <FileInput onPick={(f) => replacePhoto(index, f)} />
                </IconButton>

                {/* DELETE */}
                <IconButton size="small" onClick={() => deletePhoto(index)}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            )}
          </Box>
        ))}

        {/* ADD PHOTO */}
        {editMode && (
          <Button
            component="label"
            variant="outlined"
            startIcon={<AddPhotoAlternateIcon />}
            sx={{
              width: 180,
              height: 120,
              borderStyle: 'dashed',
            }}
          >
            Add Photo
            <FileInput onPick={addPhoto} />
          </Button>
        )}
      </Box>
    </Box>
  );
};

export default LetterPhotoSection;
