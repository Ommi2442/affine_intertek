/* eslint-disable */
import React from 'react';
import { Box, Typography, TextField, Divider } from '@mui/material';

/* ---------------- COMPONENT ---------------- */
const RenderSheet6Excel = ({ sheet, editMode, updateField }) => {
  /* ✅ SAFETY GUARD */
  if (!sheet || !Array.isArray(sheet.Items)) {
    return null;
  }

  const renderTextWithInputs = (text, item) => {
    if (!text) return null;

    const parts = text.split('___');

    return parts.map((part, idx) => (
      <React.Fragment key={idx}>
        <Typography component="span">{part}</Typography>

        {idx < parts.length - 1 && (
          <TextField
            size="small"
            sx={{ mx: 1, width: 120 }}
            value={item[`val${idx + 1}`] ?? ''}
            disabled={!(editMode && item.user_editable)}
            onChange={(e) =>
              updateField(
                sheet.sheet_no,
                `${item.question_cell}_val${idx + 1}`,
                e.target.value
              )
            }
          />
        )}
      </React.Fragment>
    ));
  };

  return (
    <Box>
      {sheet.Items.map((item, idx) => {
        let content = null;

        /* -------- CASE 1: NO CHECKBOX -------- */
        if (item.checkbox === undefined || item.checkbox === null) {
          content = (
            <Typography
              sx={{
                fontWeight: item.task_type === 'title' ? 700 : 400,
                fontSize: item.task_type === 'title' ? 16 : 14,
              }}
            >
              {item.field}
            </Typography>
          );
        }

        /* -------- CASE 2: CHECKBOX LOGIC -------- */
        if (item.checkbox !== undefined) {
          const statement = item.checkbox === true ? item.st1 : item.st2;

          content = (
            <Typography component="div">
              <strong>{item.field}</strong>{' '}
              {renderTextWithInputs(statement, item)}
            </Typography>
          );
        }

        return (
          <Box key={idx} sx={{ py: 1 }}>
            {content}

            {/* ✅ PARTITION LINE */}
            <Divider sx={{ mt: 2 }} />
          </Box>
        );
      })}
    </Box>
  );
};

export default RenderSheet6Excel;
