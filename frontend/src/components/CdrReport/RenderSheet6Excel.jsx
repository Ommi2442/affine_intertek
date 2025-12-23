/* eslint-disable */
import React from 'react';
import { Box, Typography, TextField, Divider } from '@mui/material';

/* ---------------- COMPONENT ---------------- */
const RenderSheet6Excel = ({ sheet, editMode, updateField }) => {
  if (!sheet || !Array.isArray(sheet.Items)) return null;

  return (
    <Box>
      {sheet.Items.map((item, idx) => {
        /* ---------------- LABEL LOGIC ---------------- */
        let label = item.prefix || item.field || '';

        // ✅ Take value AFTER dash only
        if (label.includes('-')) {
          label = label.split('-').slice(1).join('-').trim();
        }

        const valueText = item.value ?? '';
        const isLongText = valueText.length > 80 || valueText.includes('\n');

        return (
          <Box key={idx} sx={{ py: 1 }}>
            {/* ================= READ ONLY ================= */}
            {!item.user_editable ? (
              <>
                <Typography
                  sx={{
                    fontSize: 14,
                    fontWeight: 500,
                    mb: 0.5,
                  }}
                >
                  {label}
                </Typography>

                <Typography
                  sx={{
                    fontSize: 14,
                    whiteSpace: 'pre-wrap',
                    width: '100%',
                  }}
                >
                  {valueText}
                </Typography>
              </>
            ) : (
              /* ================= EDITABLE ================= */
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  width: '100%',
                  gap: 2,
                }}
              >
                {/* -------- LABEL (20%) -------- */}
                <Box sx={{ width: '20%' }}>
                  <Typography
                    sx={{
                      fontSize: 14,
                      fontWeight: 500,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {label}
                  </Typography>
                </Box>

                {/* -------- VALUE (80%) -------- */}
                <Box sx={{ width: '80%' }}>
                  <TextField
                    size="small"
                    fullWidth
                    multiline={isLongText}
                    minRows={isLongText ? 3 : 1}
                    maxRows={12}
                    value={valueText}
                    disabled={!editMode}
                    onChange={(e) =>
                      updateField(
                        sheet.sheet_no,
                        item.question_cell,
                        e.target.value
                      )
                    }
                  />
                </Box>
              </Box>
            )}

            <Divider sx={{ mt: 2 }} />
          </Box>
        );
      })}
    </Box>
  );
};

export default RenderSheet6Excel;
