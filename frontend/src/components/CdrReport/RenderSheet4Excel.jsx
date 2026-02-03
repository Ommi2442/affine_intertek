/* eslint-disable */
import React, { useState, useEffect } from 'react';
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
  Button,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';

import HoverActionWrapper from '../Common/HoverActionsWrapper';
import CommentDialog from '../CommentDialog';
import { useCommentActions } from '../Common/useCommentActions';
import { renderConfidenceColor } from '../../utils/renderConfidenceColor';

/* ---------------- COMPONENT ---------------- */
const RenderSheet4Excel = ({
  sheet,
  editMode,
  updateField,
  handleApprove,
  onBookmarkClick,
  pdfLoaded,
}) => {
  if (!sheet || !Array.isArray(sheet.Rows)) return null;

  const [hoveredRow, setHoveredRow] = useState(null);
  const [rowsState, setRowsState] = useState([]);

  const {
    isCommentOpen,
    setIsCommentOpen,
    commentHistory,
    currentCommentText,
    setCurrentCommentText,
    openComment,
    saveComment,
  } = useCommentActions(sheet);

  const titleItem = sheet.Items?.[0] ?? null;
  const headerRow = sheet.Rows.find((r) => r.row_type === 'column_headings');

  // Sync only when sheet changes (NOT on every keystroke)
  useEffect(() => {
    const data = sheet.Rows.filter((r) => r.row_type === 'table_data');
    setRowsState(data.map((r) => ({ ...r })));
  }, [sheet.sheet_no]);

  const border = { border: '1px solid #000' };

  /* ---------------- ADD / DELETE ROW ---------------- */
  const addRow = () => {
    setRowsState((prev) => [
      ...prev,
      {
        row_type: 'table_data',
        photo_no: '',
        item_no: String(prev.length + 1),
        name: '',
        manufacturer: '',
        type_model: '',
        technical_data: '',
        marks_of_conf: '',
        user_editable: true,
        ai_fillable: false,
        accuracy_level: false,
        confidence: null,
        is_user_edited: true,
      },
    ]);
  };

  const deleteRow = (idx) => {
    setRowsState((prev) => prev.filter((_, i) => i !== idx));
  };

  /* ---------------- LOCAL EDIT ---------------- */
  const updateLocal = (idx, key, value) => {
    setRowsState((prev) =>
      prev.map((r, i) =>
        i === idx ? { ...r, [key]: value, is_user_edited: true } : r
      )
    );
  };

  /* ---------------- COMMIT ON APPROVE ---------------- */
  const commitRow = (idx) => {
    const row = rowsState[idx];
    if (!row) return;

    const shouldBoost =
      row.accuracy_level === true &&
      typeof row.confidence === 'number' &&
      row.confidence < 100;

    /*  Update local UI immediately */
    if (shouldBoost) {
      setRowsState((prev) =>
        prev.map((r, i) => (i === idx ? { ...r, confidence: 100 } : r))
      );
    }

    /* Push boosted confidence into parent JSON */
    if (shouldBoost) {
      updateField(sheet.sheet_no, `confidence_${idx}`, 100);
    }

    /* Push all other row values */
    Object.entries(row).forEach(([key, value]) => {
      if (
        !['row_type', 'accuracy_level', 'ai_fillable', 'confidence'].includes(
          key
        )
      ) {
        updateField(sheet.sheet_no, `${key}_${idx}`, value);
      }
    });

    /* Trigger IndexedDB + ConfidenceScore */
    handleApprove?.(idx);
  };

  /* ---------------- CELL ---------------- */
  const renderCell = (value, editable, onChange) => (
    <TableCell sx={border}>
      <TextField
        size="small"
        fullWidth
        value={value ?? ''}
        InputProps={{ readOnly: !editable }}
        onChange={(e) => editable && onChange(e.target.value)}
        sx={{ backgroundColor: editable ? '#fff' : '#f5f5f5' }}
      />
    </TableCell>
  );

  return (
    <>
      <TableContainer component={Paper}>
        <Table size="small" sx={{ borderCollapse: 'collapse' }}>
          <TableBody>
            {/* ---------- TITLE ---------- */}
            {titleItem && (
              <TableRow>
                <TableCell colSpan={8} sx={{ ...border, fontWeight: 700 }}>
                  {titleItem.field}
                </TableCell>
              </TableRow>
            )}

            {/* ---------- HEADER ---------- */}
            {headerRow && (
              <TableRow>
                {[
                  headerRow.photo_no,
                  headerRow.item_no,
                  headerRow.name,
                  headerRow.manufacturer,
                  headerRow.type_model,
                  headerRow.technical_data,
                  headerRow.marks_of_conf,
                  'Action',
                ].map((h, i) => (
                  <TableCell
                    key={i}
                    sx={{
                      ...border,
                      fontWeight: 600,
                      whiteSpace: 'normal',
                      wordBreak: 'break-word',
                      overflowWrap: 'break-word',
                      lineHeight: 1.2,
                    }}
                  >
                    {h}
                  </TableCell>
                ))}
              </TableRow>
            )}

            {/* ---------- DATA ---------- */}
            {rowsState.map((row, idx) => {
              const editable = editMode && row.user_editable;

              return (
                <TableRow key={idx}>
                  {renderCell(row.photo_no, false)}
                  {renderCell(row.item_no, false)}

                  {renderCell(row.name, editable, (v) =>
                    updateLocal(idx, 'name', v)
                  )}

                  {renderCell(row.manufacturer, editable, (v) =>
                    updateLocal(idx, 'manufacturer', v)
                  )}

                  {renderCell(row.type_model, editable, (v) =>
                    updateLocal(idx, 'type_model', v)
                  )}

                  {renderCell(row.technical_data, editable, (v) =>
                    updateLocal(idx, 'technical_data', v)
                  )}

                  {/* ----- MARKS OF CONF ----- */}
                  <TableCell
                    sx={{ ...border, position: 'relative' }}
                    onMouseEnter={() => setHoveredRow(idx)}
                    onMouseLeave={() => setHoveredRow(null)}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <TextField
                        size="small"
                        fullWidth
                        value={row.marks_of_conf ?? ''}
                        InputProps={{ readOnly: !editable }}
                        onChange={(e) =>
                          editable &&
                          updateLocal(idx, 'marks_of_conf', e.target.value)
                        }
                      />

                      {row.accuracy_level &&
                        renderConfidenceColor(
                          row.confidence,
                          row.is_user_edited,
                          row.ai_fillable,
                          row.accuracy_level
                        )}
                    </Box>

                    <Box
                      sx={{
                        position: 'absolute',
                        right: -38,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        zIndex: 10,
                      }}
                    >
                      <HoverActionWrapper
                        show={hoveredRow === idx}
                        sheetNo={sheet?.sheet_no}
                        onApprove={() => commitRow(idx)}
                        onComment={() => openComment(sheet.sheet_no, idx)}
                        onBookmark={() => onBookmarkClick?.(row)}
                        bookmarkDisabled={!pdfLoaded}
                      />
                    </Box>
                  </TableCell>

                  {/* ----- DELETE ----- */}
                  <TableCell sx={{ ...border, textAlign: 'center' }}>
                    <IconButton color="error" onClick={() => deleteRow(idx)}>
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* ---------- ADD ROW ---------- */}
      <Box mt={2} display="flex" justifyContent="flex-end">
        <Button variant="outlined" onClick={addRow}>
          + Add Row
        </Button>
      </Box>

      {/* ---------- COMMENTS ---------- */}
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

export default RenderSheet4Excel;
