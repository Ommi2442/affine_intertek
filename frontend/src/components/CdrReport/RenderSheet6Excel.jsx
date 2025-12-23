/* eslint-disable */
import React, { useState, useRef } from 'react';
import { Box, Typography, TextField, Divider } from '@mui/material';
import HoverActionWrapper from '../Common/HoverActionsWrapper';
import CommentDialog from '../CommentDialog';
import { useCommentActions } from '../Common/useCommentActions';

/* ---------------- COMPONENT ---------------- */
const RenderSheet6Excel = ({
  sheet,
  editMode,
  updateField,
  onBookmarkClick,
  handleApprove,
}) => {
  if (!sheet || !Array.isArray(sheet.Items)) return null;

  const [hovered, setHovered] = useState({ i: null });
  const {
    isCommentOpen,
    setIsCommentOpen,
    commentHistory,
    currentCommentText,
    setCurrentCommentText,
    openComment,
    saveComment,
  } = useCommentActions(sheet);

  return (
    <Box>
      {sheet.Items.map((item, idx) => {
        let label = item.prefix || item.field || '';

        if (label.includes('-')) {
          label = label.split('-').slice(1).join('-').trim();
        }

        const valueText = item.value ?? '';
        const isLongText = valueText.length > 80 || valueText.includes('\n');

        return (
          <Box key={idx} sx={{ py: 1 }}>
            {!item.user_editable ? (
              <>
                <Typography sx={{ fontSize: 14, fontWeight: 500 }}>
                  {label}
                </Typography>

                <Typography sx={{ fontSize: 14, whiteSpace: 'pre-wrap' }}>
                  {valueText}
                </Typography>
              </>
            ) : (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  width: '100%',
                  gap: 2,
                }}
              >
                <Box sx={{ width: '20%' }}>
                  <Typography sx={{ fontSize: 14, fontWeight: 500 }}>
                    {label}
                  </Typography>
                </Box>

                <Box sx={{ width: '80%' }}>
                  <div
                    className="dt-value-column dt-relative"
                    onMouseEnter={() => setHovered({ i: idx })}
                    onMouseLeave={() => setHovered({ i: null })}
                  >
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

                    <HoverActionWrapper
                      show={hovered.i === idx}
                      onApprove={() => handleApprove?.(idx)}
                      onComment={() => openComment(sheet.sheet_no, idx)}
                      onBookmark={() => {
                        const row = sheet.Items[idx];
                        onBookmarkClick?.(row ?? { __i: idx });
                      }}
                    />
                  </div>
                </Box>
              </Box>
            )}

            <Divider sx={{ mt: 2 }} />
          </Box>
        );
      })}

      {/* ✅ COMMENT DIALOG */}
      <CommentDialog
        open={isCommentOpen}
        onClose={() => setIsCommentOpen(false)}
        comments={commentHistory}
        currentComment={currentCommentText}
        setCurrentComment={setCurrentCommentText}
        onSubmit={saveComment}
      />
    </Box>
  );
};

export default RenderSheet6Excel;
