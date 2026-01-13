/* eslint-disable */
import React, { useState, useEffect } from 'react';
import { Box, Typography, TextField, Button, IconButton } from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';

/* ================= HELPERS ================= */

const fileToBase64 = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

const getCellRow = (cell) => parseInt(cell?.replace(/[A-Z]/g, '') || 0, 10);
const getCellCol = (cell) => (cell ? cell.replace(/[0-9]/g, '') : 'A');
const makeCell = (col, row) => `${col}${row}`;

/* ================= COMPONENT ================= */

const RenderSheet3Excel = ({ sheet, editMode, isFinalised, onChange }) => {
  if (!sheet || !Array.isArray(sheet.Items)) return null;

  const [items, setItems] = useState(sheet.Items);

  useEffect(() => {
    setItems(sheet.Items.map((i) => ({ ...i })));
  }, [sheet.Items]);

  /* -------- Find next question_cell & answer_cell -------- */
  const getNextCells = () => {
    let lastQ = 0;
    let lastA = 0;
    let colQ = 'A';
    let colA = 'A';

    items.forEach((it) => {
      if (it.question_cell) {
        lastQ = Math.max(lastQ, getCellRow(it.question_cell));
        colQ = getCellCol(it.question_cell);
      }
      if (it.answer_cell) {
        lastA = Math.max(lastA, getCellRow(it.answer_cell));
        colA = getCellCol(it.answer_cell);
      }
    });

    return {
      question_cell: makeCell(colQ, lastQ + 8),
      answer_cell: makeCell(colA, lastA + 8),
    };
  };

  /* ---------- UPDATE FIELD ---------- */
  const handleFieldChange = (idx, value) => {
    if (!editMode || isFinalised) return;

    const updated = items.map((it, i) =>
      i === idx ? { ...it, field: value, is_user_edited: true } : it
    );

    setItems(updated);
    onChange?.(updated);
  };

  /* ---------- ADD IMAGE ---------- */
  const handleAddImage = async (e) => {
    if (!editMode || isFinalised) return;

    const file = e.target.files[0];
    if (!file) return;

    const base64 = await fileToBase64(file);
    const { question_cell, answer_cell } = getNextCells();

    const newItem = {
      question_cell,
      answer_cell,
      prefix: 'Product',
      field: 'Photo',
      photo_path: base64, // ✅ BASE64 stored
      field_merged: false,
      fm_range: null,
      value_merged: false,
      vm_range: null,
      task_type: 'photo',
      user_editable: true,
      ai_fillable: true,
      accuracy_level: false,
      is_user_edited: true,
    };

    const updated = [...items, newItem];
    setItems(updated);
    onChange?.(updated);
  };

  /* ---------- REPLACE IMAGE ---------- */
  const handleReplaceImage = async (idx, e) => {
    if (!editMode || isFinalised) return;

    const file = e.target.files[0];
    if (!file) return;

    const base64 = await fileToBase64(file);

    const updated = items.map((it, i) =>
      i === idx ? { ...it, photo_path: base64, is_user_edited: true } : it
    );

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
                  <Button
                    variant="contained"
                    size="small"
                    component="label"
                    sx={{ minWidth: 'auto', px: 1, fontSize: 12 }}
                  >
                    Browse
                    <input
                      type="file"
                      hidden
                      accept="image/*"
                      onChange={(e) => handleReplaceImage(idx, e)}
                    />
                  </Button>

                  <IconButton
                    size="small"
                    onClick={() => handleDeleteImage(idx)}
                    sx={{ background: 'rgba(255,255,255,0.9)' }}
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
