/* eslint-disable */
import React, { useState } from 'react';
import {
  Typography,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Paper,
} from '@mui/material';
import HoverActionWrapper from '../Common/HoverActionsWrapper';
import CommentDialog from '../CommentDialog';
import { useCommentActions } from '../Common/useCommentActions';

/* ---------------- HELPERS ---------------- */
const colLetterToIndex = (cell = '') => (cell ? cell.charCodeAt(0) - 65 : 0);

const colSpanFromRange = (startCell, endCell) => {
  if (!startCell || !endCell) return 1;
  return colLetterToIndex(endCell) - colLetterToIndex(startCell) + 1;
};

const rowNumberFromCell = (cell = '') =>
  Number(cell.replace(/[A-Z]/g, '')) || 0;

/* ---------------- COMPONENT ---------------- */
const RenderSheet1Excel = ({
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

  const border = { border: '1px solid #000' };

  /* group items by row */
  const rows = {};
  sheet.Items.forEach((item) => {
    const row =
      rowNumberFromCell(item.question_cell) ||
      rowNumberFromCell(item.answer_cell);

    if (!row) return;
    if (!rows[row]) rows[row] = [];
    rows[row].push(item);
  });

  const sortedRows = Object.keys(rows)
    .map(Number)
    .sort((a, b) => a - b);

  const renderValue = (item, itemIndex, colSpan = 1) => {
    const editable = editMode && item.user_editable;

    return (
      <TableCell
        sx={{ ...border, position: 'relative' }} // ✅ REQUIRED
        colSpan={colSpan}
        onMouseEnter={() => setHovered({ i: itemIndex })}
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
              show={hovered.i === itemIndex}
              onApprove={() => handleApprove?.(itemIndex)}
              onComment={() => openComment(sheet.sheet_no, itemIndex)}
              onBookmark={() => {
                const row = sheet.Items[itemIndex];
                onBookmarkClick?.(row ?? { __i: itemIndex });
              }}
            />
          </>
        ) : (
          <Typography>{item.value ?? ''}</Typography>
        )}
      </TableCell>
    );
  };

  return (
    <>
      <TableContainer component={Paper}>
        <Table size="small" sx={{ borderCollapse: 'collapse' }}>
          <TableBody>
            {sortedRows.map((rowNo) => {
              const rowItems = rows[rowNo].sort(
                (a, b) =>
                  colLetterToIndex(a.question_cell) -
                  colLetterToIndex(b.question_cell)
              );

              return (
                <TableRow key={rowNo}>
                  {rowItems.map((item) => {
                    const itemIndex = sheet.Items.indexOf(item);

                    /* FIELD MERGED */
                    if (item.field_merged && item.fm_range) {
                      const span = colSpanFromRange(
                        item.question_cell,
                        item.fm_range
                      );
                      return (
                        <TableCell
                          key={itemIndex}
                          colSpan={span}
                          sx={{
                            ...border,
                            fontWeight: 700,
                            background: '#f5f5f5',
                          }}
                        >
                          {item.field}
                        </TableCell>
                      );
                    }

                    const fieldCell = (
                      <TableCell key={`${itemIndex}-f`} sx={border}>
                        {item.field}
                      </TableCell>
                    );

                    /* VALUE MERGED */
                    if (item.value_merged && item.vm_range) {
                      const span = colSpanFromRange(
                        item.answer_cell,
                        item.vm_range
                      );
                      return (
                        <React.Fragment key={itemIndex}>
                          {fieldCell}
                          {renderValue(item, itemIndex, span)}
                        </React.Fragment>
                      );
                    }

                    return (
                      <React.Fragment key={itemIndex}>
                        {fieldCell}
                        {renderValue(item, itemIndex, 1)}
                      </React.Fragment>
                    );
                  })}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

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

export default RenderSheet1Excel;
