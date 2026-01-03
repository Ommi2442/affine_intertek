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
  Box,
  IconButton,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

import HoverActionWrapper from '../Common/HoverActionsWrapper';
import CommentDialog from '../CommentDialog';
import { useCommentActions } from '../Common/useCommentActions';
import { renderConfidenceColor } from '../../utils/renderConfidenceColor';

/* ---------------- HELPERS ---------------- */
const colLetterToIndex = (cell = '') => (cell ? cell.charCodeAt(0) - 65 : 0);

const colSpanFromRange = (startCell, endCell) => {
  if (!startCell || !endCell) return 1;
  return colLetterToIndex(endCell) - colLetterToIndex(startCell) + 1;
};

const rowNumberFromCell = (cell = '') =>
  Number(cell.replace(/[A-Z]/g, '')) || 0;

/* ---------------- STATIC FIELDS ---------------- */
const MANUFACTURER_FIELDS = [
  'Manufacturer',
  'Address',
  'Country',
  'Contact',
  'Phone',
  'FAX',
  'Email',
];

/* ---------------- PREFIX HELPERS ---------------- */
const isApplicant = (item) => item.prefix === 'Applicant';
const isManufacturer1 = (item) => item.prefix === 'Manufacturer 1';

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
  const [extraManufacturers, setExtraManufacturers] = useState([]);

  const {
    isCommentOpen,
    setIsCommentOpen,
    commentHistory,
    currentCommentText,
    setCurrentCommentText,
    openComment,
    saveComment,
  } = useCommentActions(sheet);

  const border = { border: '1px solid #838181ff' };

  /* ---------------- GROUP ITEMS BY ROW ---------------- */
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

  /* ---------------- VALUE CELL (UNCHANGED) ---------------- */
  const renderValue = (item, itemIndex, colSpan = 1) => {
    const isEditable = editMode && item.user_editable;

    return (
      <TableCell
        sx={{ ...border, position: 'relative' }}
        colSpan={colSpan}
        onMouseEnter={() => setHovered({ i: itemIndex })}
        onMouseLeave={() => setHovered({ i: null })}
      >
        <div style={{ display: 'flex' }}>
          <TextField
            size="small"
            fullWidth
            value={item.value ?? ''}
            InputProps={{ readOnly: !isEditable }}
            onChange={(e) => {
              if (!isEditable) return;
              updateField(
                sheet.sheet_no,
                item.answer_cell ?? item.field,
                e.target.value
              );
            }}
            sx={{
              backgroundColor: isEditable ? '#fff' : '#f5f5f5',
              mr: '4%',
            }}
          />

          <Box sx={{ position: 'relative', zIndex: 2 }}>
            <HoverActionWrapper
              show={hovered.i === itemIndex}
              onApprove={() => handleApprove?.(itemIndex)}
              onComment={() => openComment(sheet.sheet_no, itemIndex)}
              onBookmark={() => onBookmarkClick?.(item)}
            />
          </Box>

          {item.ai_fillable &&
            item.accuracy_level &&
            renderConfidenceColor(item.confidence, item.is_user_edited)}
        </div>
      </TableCell>
    );
  };

  /* ---------------- GENERIC TABLE RENDER ---------------- */
  const renderTable = (filterFn) => (
    <TableContainer component={Paper} sx={{ width: '100%' }}>
      <Table size="small" sx={{ borderCollapse: 'collapse' }}>
        <TableBody>
          {sortedRows.map((rowNo) => {
            const rowItems = rows[rowNo].filter(filterFn);
            if (!rowItems.length) return null;

            return (
              <TableRow key={rowNo}>
                {rowItems.map((item) => {
                  const itemIndex = sheet.Items.indexOf(item);

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

                  return (
                    <React.Fragment key={itemIndex}>
                      <TableCell sx={border}>{item.field}</TableCell>
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
  );

  /* ---------------- EMPTY MANUFACTURER (WITH DELETE) ---------------- */
  const renderEmptyManufacturer = (idx) => (
    <TableContainer component={Paper} sx={{ width: '100%' }}>
      <Table size="small" sx={{ borderCollapse: 'collapse' }}>
        <TableBody>
          <TableRow>
            <TableCell
              colSpan={2}
              sx={{
                ...border,
                fontWeight: 700,
                background: '#f5f5f5',
                position: 'relative',
              }}
            >
              Manufacturer {idx + 2}
              {/* ❌ DELETE BUTTON */}
              <IconButton
                size="small"
                sx={{ position: 'absolute', right: 4, top: 4 }}
                onClick={() =>
                  setExtraManufacturers((prev) =>
                    prev.filter((_, i) => i !== idx)
                  )
                }
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </TableCell>
          </TableRow>

          {MANUFACTURER_FIELDS.map((field) => (
            <TableRow key={field}>
              <TableCell sx={border}>{field}</TableCell>
              <TableCell sx={border}>
                <TextField
                  size="small"
                  fullWidth
                  value={extraManufacturers[idx]?.[field] ?? ''}
                  onChange={(e) => {
                    const copy = [...extraManufacturers];
                    copy[idx] = { ...copy[idx], [field]: e.target.value };
                    setExtraManufacturers(copy);
                  }}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <>
      {/* ===== TOP DATA ===== */}
      {renderTable((item) => !isApplicant(item) && !isManufacturer1(item))}

      {/* ===== APPLICANT + MANUFACTURER 1 ===== */}
      <Box
        sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mt: 2 }}
      >
        {renderTable(isApplicant)}
        {renderTable(isManufacturer1)}
      </Box>

      {/* ===== EXTRA MANUFACTURERS ===== */}
      <Box mt={3}>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          {extraManufacturers.map((_, idx) => (
            <Box key={idx}>{renderEmptyManufacturer(idx)}</Box>
          ))}

          {/* ➕ ADD BUTTON */}
          <Box
            sx={{
              border: '1px dashed #999',
              minHeight: 180,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
            onClick={() => setExtraManufacturers((m) => [...m, {}])}
          >
            <Typography fontWeight={600}>+ Add Manufacturer</Typography>
          </Box>
        </Box>
      </Box>

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
