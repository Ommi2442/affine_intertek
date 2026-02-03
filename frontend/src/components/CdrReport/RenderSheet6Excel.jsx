/* eslint-disable */
import React, { useState, useEffect } from 'react';
import { Box, Typography, TextField, Divider } from '@mui/material';
import HoverActionWrapper from '../Common/HoverActionsWrapper';
import CommentDialog from '../CommentDialog';
import { useCommentActions } from '../Common/useCommentActions';
import { renderConfidenceColor } from '../../utils/renderConfidenceColor';
import { useRef } from 'react';

/* ---------------- COMPONENT ---------------- */
const RenderSheet6Excel = ({
  sheet,
  editMode,
  updateField,
  onBookmarkClick,
  handleApprove,
  onConfidenceChange,
  pdfLoaded,
}) => {
  if (!sheet || !Array.isArray(sheet.Items)) return null;

  /* ---------------- LOCAL EDIT STATE ---------------- */
  const [localItems, setLocalItems] = useState(sheet.Items);
  const editedOnceRef = useRef(new Set());

  // Sync only when sheet changes (NOT on every keystroke)
  useEffect(() => {
    setLocalItems(sheet.Items.map((i) => ({ ...i })));
  }, [sheet.Items]);

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

  /* ---------------- LOCAL UPDATE ---------------- */
  const updateLocal = (idx, value) => {
    setLocalItems((prev) =>
      prev.map((it, i) => {
        if (i !== idx) return it;

        //  Fire confidence ONLY first time this field is edited
        if (!editedOnceRef.current.has(idx)) {
          editedOnceRef.current.add(idx);
          onConfidenceChange?.();
        }

        return {
          ...it,
          value,
          is_user_edited: true,
        };
      })
    );
  };

  /* ---------------- COMMIT ON APPROVE ---------------- */
  const commit = (idx) => {
    const item = localItems[idx];
    if (!item) return;

    updateField(sheet.sheet_no, item.question_cell, item.value);
    handleApprove?.(idx);
  };

  return (
    <Box>
      {localItems.map((item, idx) => {
        // Removes only "Label - " or "Label – " from the start of the value
        const stripLeadingLabel = (value, label) => {
          if (!value || !label) return value;

          // Escape special regex chars in label
          const safeLabel = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

          // Match:  ^Label -   OR   ^Label –
          const regex = new RegExp(`^${safeLabel}\\s*[–-]\\s*`, 'i');

          return value.replace(regex, '');
        };
        let label = item.prefix || item.field || '';
        let valueText = item.value ?? '';

        valueText = stripLeadingLabel(valueText, label);

        //  value existence
        const hasValue =
          item.value !== null &&
          item.value !== undefined &&
          String(item.value).trim() !== '';

        //  normalize confidence
        const normalizeConfidence = (value) => {
          const num = Number(value);
          if (Number.isNaN(num)) return null;
          return num <= 1 ? Math.round(num * 100) : Math.round(num);
        };

        //  approve allowed only when AI confidence exists
        const canApprove =
          item.ai_fillable === true &&
          item.accuracy_level === true &&
          normalizeConfidence(item.confidence) !== null;

        const isLongText = valueText.length > 80 || valueText.includes('\n');
        const isEditable = editMode && item.user_editable;

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
                    style={{ display: 'flex' }}
                  >
                    <TextField
                      size="small"
                      style={{ marginRight: '2%' }}
                      fullWidth
                      multiline={isLongText}
                      minRows={isLongText ? 3 : 1}
                      maxRows={12}
                      value={valueText}
                      disabled={!isEditable}
                      onChange={(e) => updateLocal(idx, e.target.value)}
                    />

                    <HoverActionWrapper
                      show={hovered.i === idx}
                      onApprove={canApprove ? () => commit(idx) : null}
                      onComment={() => openComment(sheet.sheet_no, idx)}
                      onBookmark={
                        hasValue
                          ? () => onBookmarkClick?.(localItems[idx])
                          : null
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
                  </div>
                </Box>
              </Box>
            )}

            <Divider sx={{ mt: 2 }} />
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
    </Box>
  );
};

export default RenderSheet6Excel;
