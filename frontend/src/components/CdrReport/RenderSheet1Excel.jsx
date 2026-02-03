/* eslint-disable */
import React, { useEffect, useState } from 'react';
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
import HoverActionWrapperSheet1 from '../Common/HoverActionsWrapperSheet1';

/* ---------------- HELPERS ---------------- */
const colLetterToIndex = (cell = '') => (cell ? cell.charCodeAt(0) - 65 : 0);

const colSpanFromRange = (startCell, endCell) => {
  if (!startCell || !endCell) return 1;
  return colLetterToIndex(endCell) - colLetterToIndex(startCell) + 1;
};

const rowNumberFromCell = (cell = '') =>
  Number(cell.replace(/[A-Z]/g, '')) || 0;

/* ---------------- PREFIX HELPERS ---------------- */
const isApplicant = (item) => item.prefix === 'Applicant';
const isManufacturer1 = (item) => item.prefix === 'Manufacturer 1';

const isManufacturer2Plus = (item) =>
  typeof item.prefix === 'string' &&
  item.prefix.startsWith('Manufacturer ') &&
  item.prefix !== 'Manufacturer 1';

const isAnyManufacturer = (item) =>
  typeof item.prefix === 'string' && item.prefix.startsWith('Manufacturer');

const getManufacturerIndex = (prefix = '') => {
  const n = parseInt(prefix.replace('Manufacturer ', ''), 10);
  return isNaN(n) ? 0 : n;
};

/* ---------------- COMPONENT ---------------- */
const RenderSheet1Excel = ({
  sheet,
  editMode,
  updateField,
  handleApprove,
  onBookmarkClick,
  pdfLoaded,
}) => {
  const [localItems, setLocalItems] = useState(sheet.Items);

  if (!sheet || !Array.isArray(localItems)) return null;

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

  const border = { border: '1px solid #838181ff' };

  /* ---------------- GROUP ITEMS BY ROW ---------------- */
  const rows = {};
  const toUiContact = (value) => {
    if (typeof value !== 'string') return value;
    return value.replace(/\n+/g, ', ');
  };

  useEffect(() => {
    setLocalItems(sheet.Items);
  }, [sheet.Items]);

  const toBackendContact = (value) => {
    if (typeof value !== 'string') return value;
    return value
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean)
      .join('\n');
  };

  localItems.forEach((item) => {
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

  /* ---------------- VALUE CELL ---------------- */
  const renderValue = (item, itemIndex, colSpan = 1) => {
    const isEditable = editMode && item.user_editable;
    const isContactField =
      typeof item.field === 'string' &&
      item.field.toLowerCase().includes('contact');

    const normalizeConfidence = (value) => {
      const num = Number(value);
      if (Number.isNaN(num)) return null;
      return num <= 1 ? Math.round(num * 100) : Math.round(num);
    };

    const canApprove =
      item.ai_fillable === true &&
      item.accuracy_level === true &&
      normalizeConfidence(item.confidence) !== null;

    const hasValue =
      item.value !== null &&
      item.value !== undefined &&
      String(item.value).trim() !== '';

    return (
      <TableCell
        sx={{ ...border, position: 'relative' }}
        colSpan={colSpan}
        onMouseEnter={() => setHovered({ i: itemIndex })}
        onMouseLeave={() => setHovered({ i: null })}
      >
        <Box sx={{ display: 'flex' }}>
          <TextField
            size="small"
            fullWidth
            value={
              isContactField
                ? toUiContact(item.value ?? '')
                : (item.value ?? '')
            }
            InputProps={{ readOnly: !isEditable }}
            onChange={(e) => {
              if (!isEditable) return;

              const uiValue = e.target.value;
              const backendValue = isContactField
                ? toBackendContact(uiValue)
                : uiValue;

              // Update UI
              setLocalItems((prev) =>
                prev.map((it, idx) =>
                  idx === itemIndex ? { ...it, value: backendValue } : it
                )
              );

              // Commit to CDR (this sets is_user_edited + fires onConfidenceChange)
              updateField(
                sheet.sheet_no,
                item.answer_cell ?? item.field,
                backendValue
              );
            }}
            sx={{
              backgroundColor: isEditable ? '#fff' : '#f5f5f5',
              mr: '4%',
            }}
          />

          <Box sx={{ position: 'relative', zIndex: 2 }}>
            <HoverActionWrapperSheet1
              show={hovered.i === itemIndex}
              onApprove={
                canApprove
                  ? () => {
                      handleApprove?.(itemIndex); //  ONLY approve
                    }
                  : null
              }
              onComment={() => openComment(sheet.sheet_no, itemIndex)}
              onBookmark={hasValue ? () => onBookmarkClick?.(item) : null}
              bookmarkDisabled={!pdfLoaded}
            />
          </Box>

          {item.ai_fillable &&
            item.accuracy_level &&
            renderConfidenceColor(
              item.confidence,
              item.is_user_edited,
              item.ai_fillable,
              item.accuracy_level
            )}
        </Box>
      </TableCell>
    );
  };

  const isBlankRow = (items) =>
    items.every((i) => i.task_type === 'blank' || i.field === null);

  /* ---------------- GENERIC TABLE ---------------- */
  const renderTable = (filterFn) => {
    let lastWasBlank = false;

    return (
      <TableContainer component={Paper} sx={{ width: '100%' }}>
        <Table size="small" sx={{ borderCollapse: 'collapse' }}>
          <TableBody>
            {sortedRows.map((rowNo) => {
              const rowItems = rows[rowNo].filter(filterFn);
              if (!rowItems.length) return null;

              const blank = isBlankRow(rowItems);

              // Skip consecutive blank rows
              if (blank && lastWasBlank) {
                return null;
              }

              lastWasBlank = blank;

              // Render a divider instead of empty rows
              if (blank) {
                return (
                  <TableRow key={rowNo}>
                    <TableCell colSpan={6} sx={{ p: 0 }}>
                      <Box sx={{ height: 1, background: '#ccc', my: 1 }} />
                    </TableCell>
                  </TableRow>
                );
              }

              return (
                <TableRow key={rowNo}>
                  {rowItems.map((item) => {
                    const itemIndex = localItems.indexOf(item);

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
                        {renderValue(item, itemIndex)}
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
  };

  /* ---------------- ADD MANUFACTURER ---------------- */
  const handleAddManufacturer = async () => {
    const MANUFACTURER_FIELDS = [
      'Manufacturer',
      'Address',
      'Country',
      'Contact',
      'Phone',
      'FAX',
      'Email',
    ];

    // Find highest manufacturer index
    let maxIndex = 1;
    localItems.forEach((i) => {
      if (i.prefix?.startsWith('Manufacturer ')) {
        const n = parseInt(i.prefix.replace('Manufacturer ', ''), 10);
        if (!isNaN(n)) maxIndex = Math.max(maxIndex, n);
      }
    });

    const nextIndex = maxIndex + 1;
    const prefix = `Manufacturer ${nextIndex}`;

    // Find last question_cell row in entire sheet
    const sorted = [...localItems]
      .filter((i) => i.question_cell)
      .sort(
        (a, b) =>
          rowNumberFromCell(a.question_cell) -
          rowNumberFromCell(b.question_cell)
      );

    const lastItem = sorted[sorted.length - 1];
    if (!lastItem) return;

    const lastColumn = lastItem.question_cell.charAt(0);
    const lastRow = rowNumberFromCell(lastItem.question_cell);

    let targetColumn;
    let startRow;

    // If last row is blank → continue same column
    if (lastItem.task_type === 'blank') {
      targetColumn = lastColumn;
      startRow = lastRow + 1;
    } else {
      // Switch column (A ↔ D)
      targetColumn = lastColumn === 'A' ? 'D' : 'A';

      const lastRowInTarget = Math.max(
        ...localItems
          .filter((i) => i.question_cell?.startsWith(targetColumn))
          .map((i) => rowNumberFromCell(i.question_cell)),
        0
      );

      startRow = lastRowInTarget + 1;
    }

    const answerColumn = targetColumn === 'A' ? 'B' : 'E';

    // vm_range mapping
    const vmColumn =
      targetColumn === 'A' ? 'C' : targetColumn === 'D' ? 'F' : null;

    // Create new rows
    const newRows = MANUFACTURER_FIELDS.map((fieldName, idx) => {
      const rowNo = startRow + idx;

      return {
        question_cell: `${targetColumn}${rowNo}`,
        prefix,

        //  ONLY first row gets "Manufacturer X"
        field:
          fieldName === 'Manufacturer'
            ? `Manufacturer ${nextIndex}`
            : fieldName,

        answer_cell: `${answerColumn}${rowNo}`,
        value: '',

        field_merged: false,
        fm_range: null,

        value_merged: true,

        //  vm_range logic
        vm_range: vmColumn ? `${vmColumn}${rowNo}` : null,

        task_type: 'extraction',
        user_editable: true,
        ai_fillable: false,
        accuracy_level: false,
        confidence: null,
        is_user_modified: true,
        is_user_edited: false,
        text_support: [],
      };
    });

    // Update UI
    const updatedItems = [...localItems, ...newRows];
    setLocalItems(updatedItems);

    // Update actual sheet source
    sheet.Items = [...sheet.Items, ...newRows];

    // Persist to IndexedDB
    await updateField(sheet.sheet_no, null, null, {
      replaceFullSheet: true,
      newItems: sheet.Items,
    });
  };

  /* ---------------- MANUFACTURER BLOCK ---------------- */
  const manufacturer2Plus = localItems.filter(isManufacturer2Plus);

  const manufacturerGroups = {};
  manufacturer2Plus.forEach((item) => {
    if (!manufacturerGroups[item.prefix]) {
      manufacturerGroups[item.prefix] = [];
    }
    manufacturerGroups[item.prefix].push(item);
  });

  const manufacturerBlocks = Object.values(manufacturerGroups);

  const renderManufacturerBlock = (items) => {
    if (!items.length) return null;
    const prefix = items[0].prefix;
    const manufacturerNo = getManufacturerIndex(prefix);

    const localRows = {};
    items.forEach((item) => {
      const row =
        rowNumberFromCell(item.question_cell) ||
        rowNumberFromCell(item.answer_cell);
      if (!localRows[row]) localRows[row] = [];
      localRows[row].push(item);
    });

    const sorted = Object.keys(localRows)
      .map(Number)
      .sort((a, b) => a - b);

    const handleDelete = async () => {
      //  Remove from local UI state
      const updatedItems = localItems.filter((i) => i.prefix !== prefix);
      setLocalItems(updatedItems);

      //  Remove from sheet.Items
      sheet.Items = sheet.Items.filter((i) => i.prefix !== prefix);

      //  Persist to IndexedDB
      await updateField(sheet.sheet_no, null, null, {
        replaceFullSheet: true,
        newItems: sheet.Items,
      });
    };

    return (
      <TableContainer component={Paper} sx={{ width: '100%' }}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            px: 1,
            py: 0.5,
            borderBottom: '1px solid #ccc',
            background: '#f5f5f5',
            fontWeight: 600,
          }}
        >
          <Typography>Manufacturer {manufacturerNo}</Typography>
          {editMode && (
            <IconButton size="small" onClick={handleDelete}>
              <CloseIcon fontSize="small" />
            </IconButton>
          )}
        </Box>

        <Table size="small">
          <TableBody>
            {sorted.map((rowNo) => (
              <TableRow key={rowNo}>
                {localRows[rowNo].map((item) => {
                  const itemIndex = localItems.indexOf(item);
                  return (
                    <React.Fragment key={itemIndex}>
                      <TableCell sx={border}>{item.field}</TableCell>
                      {renderValue(item, itemIndex)}
                    </React.Fragment>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  /* ---------------- RENDER ---------------- */
  return (
    <>
      {renderTable((item) => !isApplicant(item) && !isAnyManufacturer(item))}

      <Box
        sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mt: 2 }}
      >
        {renderTable(isApplicant)}
        {renderTable(isManufacturer1)}
      </Box>

      <Box mt={3}>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          {manufacturerBlocks.map((block, idx) => (
            <Box key={idx}>{renderManufacturerBlock(block)}</Box>
          ))}

          <Box
            sx={{
              border: '1px dashed #999',
              minHeight: 180,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
            onClick={() => editMode && handleAddManufacturer()}
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
