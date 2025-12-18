/* eslint-disable */
import React from 'react';
import { Box, Typography, TextField } from '@mui/material';

/* ---------------- COMPONENT ---------------- */
const RenderSheetDefaultExcel = ({ sheet, editMode, updateField }) => {
  /* ✅ SAFETY GUARD */
  if (!sheet || !Array.isArray(sheet.Items)) {
    return null;
  }

  return (
    <>
      {sheet.Items.map((item, idx) => {
        const editable = editMode && item.user_editable;

        return (
          <Box key={idx} sx={{ display: 'flex', gap: 2, my: 1 }}>
            <Typography sx={{ flex: 1 }}>{item.field}</Typography>

            <Box sx={{ flex: 2 }}>
              {editable ? (
                <TextField
                  size="small"
                  fullWidth
                  value={item.value ?? ''}
                  onChange={(e) =>
                    updateField(
                      sheet.sheet_no,
                      item.answer_cell ?? item.field,
                      e.target.value
                    )
                  }
                />
              ) : (
                <Typography>{item.value ?? ''}</Typography>
              )}
            </Box>
          </Box>
        );
      })}
    </>
  );
};

export default RenderSheetDefaultExcel;
