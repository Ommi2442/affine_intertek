/* eslint-disable */
import React, { useState, useEffect } from 'react';
import { Box, Typography, TextField } from '@mui/material';
import HoverActionWrapper from '../Common/HoverActionsWrapper';
import CommentDialog from '../CommentDialog';
import { useCommentActions } from '../Common/useCommentActions';
import { renderConfidenceColor } from '../../utils/renderConfidenceColor';

/* ---------------- COMPONENT ---------------- */
const RenderSheetDefaultExcel = ({
  sheet,
  editMode,
  updateField,
  handleApprove,
  onBookmarkClick,
  pdfLoaded,
}) => {
  if (!sheet || !Array.isArray(sheet.Items)) return null;

  /* ---------------- LOCAL EDIT STATE ---------------- */
  const [localItems, setLocalItems] = useState(sheet.Items);

  // Sync only when switching sheets, NOT on every keystroke
  useEffect(() => {
    setLocalItems(sheet.Items.map((i) => ({ ...i })));
  }, [sheet.sheet_no]);

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
      {localItems.map((item, idx) => {
        const isEditable = editMode && item.user_editable;

        const normalizeConfidence = (value) => {
          const num = Number(value);
          if (Number.isNaN(num)) return null;
          return num <= 1 ? Math.round(num * 100) : Math.round(num);
        };

        const hasValue =
          item.value !== null &&
          item.value !== undefined &&
          String(item.value).trim() !== '';

        const canApprove =
          item.ai_fillable === true &&
          item.accuracy_level === true &&
          normalizeConfidence(item.confidence) !== null;

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
              sx={{ flex: 2, position: 'relative' }}
              onMouseEnter={() => setHovered({ i: idx })}
              onMouseLeave={() => setHovered({ i: null })}
            >
              {item.user_editable && (
                <Box sx={{ display: 'flex' }}>
                  <TextField
                    size="small"
                    fullWidth
                    value={item.value ?? ''}
                    InputProps={{
                      readOnly: !isEditable,
                    }}
                    onChange={(e) => {
                      if (!isEditable) return;
                      const value = e.target.value;

                      // Fast local update
                      setLocalItems((prev) =>
                        prev.map((it, i) =>
                          i === idx
                            ? { ...it, value, is_user_edited: true }
                            : it
                        )
                      );
                    }}
                    sx={{
                      backgroundColor: isEditable ? '#fff' : '#f5f5f5',
                      cursor: isEditable ? 'text' : 'default',
                    }}
                  />

                  <HoverActionWrapper
                    show={hovered.i === idx}
                    onApprove={
                      canApprove
                        ? () => {
                            const item = localItems[idx];

                            updateField(
                              sheet.sheet_no,
                              item.answer_cell ?? item.field,
                              item.value
                            );

                            handleApprove?.(idx);
                          }
                        : null
                    }
                    onComment={() => openComment(sheet.sheet_no, idx)}
                    onBookmark={
                      hasValue ? () => onBookmarkClick?.(localItems[idx]) : null
                    }
                    bookmarkDisabled={!pdfLoaded}
                  />

                  {item.ai_fillable === true &&
                    item.accuracy_level === true &&
                    renderConfidenceColor(
                      item.confidence,
                      item.is_user_edited,
                      item.ai_fillable,
                      item.accuracy_level
                    )}
                </Box>
              )}
            </Box>
          </Box>
        );
      })}

      {/* COMMENT DIALOG */}
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
