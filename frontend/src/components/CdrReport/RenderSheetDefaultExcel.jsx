/* eslint-disable */
import React, { useState } from 'react';
import { Box, Typography, TextField } from '@mui/material';
import HoverActionWrapper from '../Common/HoverActionsWrapper';
import CommentDialog from '../CommentDialog';
import { useCommentActions } from '../Common/useCommentActions';

/* ---------------- COMPONENT ---------------- */
const RenderSheetDefaultExcel = ({
  sheet,
  editMode,
  updateField,
  handleApprove,
  onBookmarkClick,
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
    <>
      {sheet.Items.map((item, idx) => {
        const editable = editMode && item.user_editable;

        return (
          <Box
            key={idx}
            sx={{
              display: 'flex',
              gap: 2,
              my: 1,
              alignItems: 'flex-start',
            }}
          >
            {/* FIELD */}
            <Typography sx={{ flex: 1 }}>{item.field}</Typography>

            {/* VALUE */}
            <Box
              sx={{
                flex: 2,
                position: 'relative', // ✅ REQUIRED
              }}
              onMouseEnter={() => setHovered({ i: idx })}
              onMouseLeave={() => setHovered({ i: null })}
            >
              {editable ? (
                <>
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

                  <HoverActionWrapper
                    show={hovered.i === idx}
                    onApprove={() => handleApprove?.(idx)}
                    onComment={() => openComment(sheet.sheet_no, idx)}
                    onBookmark={() => {
                      const row = sheet.Items[idx];
                      onBookmarkClick?.(row ?? { __i: idx });
                    }}
                  />
                </>
              ) : (
                <Typography>{item.value ?? ''}</Typography>
              )}
            </Box>
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
    </>
  );
};

export default RenderSheetDefaultExcel;
