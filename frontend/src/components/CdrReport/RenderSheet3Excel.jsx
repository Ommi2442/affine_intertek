/* eslint-disable */
import React, { useState, useEffect } from 'react';
import { Box, Typography, TextField, Button, IconButton } from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';

const RenderSheet3Excel = ({ sheet, editMode, isFinalised, onChange }) => {
  if (!sheet || !Array.isArray(sheet.Items)) return null;

  const [items, setItems] = useState(sheet.Items);

  // keep local state in sync
  useEffect(() => {
    setItems(sheet.Items);
  }, [sheet.Items]);

  /* ---------- UPDATE FIELD ---------- */
  const handleFieldChange = (idx, value) => {
    if (!editMode || isFinalised) return;

    const updated = [...items];
    updated[idx] = { ...updated[idx], field: value };
    setItems(updated);
    onChange?.(updated);
  };

  /* ---------- ADD IMAGE ---------- */
  const handleAddImage = (e) => {
    if (!editMode || isFinalised) return;

    const file = e.target.files[0];
    if (!file) return;

    const imageUrl = URL.createObjectURL(file);

    const newItem = {
      question_cell: null,
      prefix: 'Product',
      field: '',
      photo_path: imageUrl,
      task_type: 'photo',
      user_editable: true,
      ai_fillable: false,
    };

    const updated = [...items, newItem];
    setItems(updated);
    onChange?.(updated);
  };

  /* ---------- DELETE IMAGE ---------- */
  const handleDeleteImage = (idx) => {
    if (!editMode || isFinalised) return;

    const updated = items.filter((_, i) => i !== idx);
    setItems(updated);
    onChange?.(updated);
  };

  /* ---------- REPLACE IMAGE ---------- */
  const handleReplaceImage = (idx, e) => {
    if (!editMode || isFinalised) return;

    const file = e.target.files[0];
    if (!file) return;

    const imageUrl = URL.createObjectURL(file);

    const updated = [...items];
    updated[idx] = {
      ...updated[idx],
      photo_path: imageUrl,
    };

    setItems(updated);
    onChange?.(updated);
  };

  return (
    <Box>
      {items.map((item, idx) => (
        <Box key={idx} sx={{ mb: 4 }}>
          {/* ---------- DESCRIPTION ---------- */}
          {item.user_editable && editMode && !isFinalised ? (
            <TextField
              fullWidth
              size="small"
              value={item.field || ''}
              onChange={(e) => handleFieldChange(idx, e.target.value)}
              placeholder="Enter photo description"
              sx={{ mb: 1 }}
            />
          ) : (
            <Typography fontWeight={600}>{item.field}</Typography>
          )}

          {/* ---------- IMAGE ---------- */}
          {item.photo_path && (
            <Box sx={{ position: 'relative', mt: 1 }}>
              <Box
                component="img"
                src={item.photo_path}
                sx={{
                  maxWidth: '100%',
                  maxHeight: 300,
                  border: '1px solid #ccc',
                  borderRadius: 1,
                }}
              />

              {/* ---------- ACTION BUTTONS ---------- */}
              {item.user_editable && editMode && !isFinalised && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: 6,
                    right: 6,
                    display: 'flex',
                    gap: 0.5,
                  }}
                >
                  {/* BROWSE / REPLACE */}
                  <Button
                    variant="contained"
                    size="small"
                    component="label"
                    sx={{
                      minWidth: 'auto',
                      px: 1,
                      fontSize: 12,
                    }}
                  >
                    Browse
                    <input
                      type="file"
                      hidden
                      accept="image/*"
                      onChange={(e) => handleReplaceImage(idx, e)}
                    />
                  </Button>

                  {/* DELETE */}
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteImage(idx)}
                    sx={{
                      background: 'rgba(255,255,255,0.9)',
                    }}
                  >
                    <DeleteOutlineIcon color="error" fontSize="small" />
                  </IconButton>
                </Box>
              )}
            </Box>
          )}
        </Box>
      ))}

      {/* ---------- ADD PHOTO ---------- */}
      {editMode && !isFinalised && (
        <Button variant="outlined" component="label">
          + Add Photo
          <input
            type="file"
            hidden
            accept="image/*"
            onChange={handleAddImage}
          />
        </Button>
      )}
    </Box>
  );
};

export default RenderSheet3Excel;
