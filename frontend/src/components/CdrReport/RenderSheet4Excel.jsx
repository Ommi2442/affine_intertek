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
} from '@mui/material';
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
}) => {
  if (!sheet || !Array.isArray(sheet.Rows)) return null;

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

  const titleItem = sheet.Items?.[0] ?? null;
  const headerRow = sheet.Rows.find((r) => r.row_type === 'column_headings');
  const dataRows = sheet.Rows.filter((r) => r.row_type === 'table_data');

  const border = { border: '1px solid #000' };

  /* ---------------- CELL RENDER (NO HOVER HERE) ---------------- */
  const renderCell = (value, editable, onChange = () => {}) => (
    <TableCell
      sx={{
        ...border,
        whiteSpace: 'normal',
        wordBreak: 'break-word',
        overflowWrap: 'anywhere',
        verticalAlign: 'middle',
      }}
    >
      <TextField
        size="small"
        fullWidth
        value={value ?? ''}
        InputProps={{
          readOnly: !editable,
        }}
        onChange={(e) => {
          if (!editable) return;
          onChange(e);
        }}
        sx={{
          backgroundColor: editable ? '#fff' : '#f5f5f5',
          cursor: editable ? 'text' : 'default',
        }}
      />
    </TableCell>
  );

  return (
    <>
      <TableContainer component={Paper}>
        <Table size="small" sx={{ borderCollapse: 'collapse' }}>
          <TableBody>
            {/* ---------------- TITLE ---------------- */}
            {titleItem && (
              <TableRow>
                <TableCell
                  colSpan={7}
                  sx={{
                    ...border,
                    fontWeight: 700,
                    background: '#f5f5f5',
                    textAlign: 'left',
                  }}
                >
                  {titleItem.field}
                </TableCell>
              </TableRow>
            )}

            {/* ---------------- HEADERS ---------------- */}
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
                ].map((label, idx) => (
                  <TableCell
                    key={idx}
                    sx={{
                      ...border,
                      fontWeight: 600,
                      textAlign: 'center',
                      whiteSpace: 'normal',
                      wordBreak: 'break-word',
                      overflowWrap: 'anywhere',
                    }}
                  >
                    {label}
                  </TableCell>
                ))}
              </TableRow>
            )}

            {/* ---------------- DATA ROWS ---------------- */}
            {dataRows.map((row, idx) => {
              const editable = editMode && row.user_editable;

              return (
                <TableRow
                  key={idx}
                  onMouseEnter={() => setHovered({ i: idx })}
                  onMouseLeave={() => setHovered({ i: null })}
                  sx={{ position: 'relative' }}
                >
                  {renderCell(row.photo_no, false)}
                  {renderCell(row.item_no, false)}

                  {renderCell(row.name, editable, (e) =>
                    updateField(sheet.sheet_no, `name_${idx}`, e.target.value)
                  )}

                  {renderCell(row.manufacturer, editable, (e) =>
                    updateField(
                      sheet.sheet_no,
                      `manufacturer_${idx}`,
                      e.target.value
                    )
                  )}

                  {renderCell(row.type_model, editable, (e) =>
                    updateField(
                      sheet.sheet_no,
                      `type_model_${idx}`,
                      e.target.value
                    )
                  )}

                  {renderCell(row.technical_data, editable, (e) =>
                    updateField(
                      sheet.sheet_no,
                      `technical_data_${idx}`,
                      e.target.value
                    )
                  )}

                  {/* -------- LAST COLUMN: SINGLE ROW-LEVEL HOVER -------- */}
                  <TableCell
                    sx={{
                      ...border,
                      position: 'relative',
                      whiteSpace: 'normal',
                      verticalAlign: 'middle',
                    }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1, // space between textbox and dot
                      }}
                    >
                      {/* ✅ MARKS OF CONFORMITY TEXTBOX */}
                      <TextField
                        size="small"
                        fullWidth
                        value={row.marks_of_conf ?? ''}
                        InputProps={{
                          readOnly: !editable, // 🔥 disabled initially, editable on Edit
                        }}
                        onChange={(e) => {
                          if (!editable) return;
                          updateField(
                            sheet.sheet_no,
                            `marks_of_conf_${idx}`,
                            e.target.value
                          );
                        }}
                        sx={{
                          backgroundColor: editable ? '#fff' : '#f5f5f5',
                          cursor: editable ? 'text' : 'default',
                        }}
                      />

                      {/* ✅ CONFIDENCE DOT (ALWAYS TO THE RIGHT) */}
                      {row.user_editable === true &&
                        row.accuracy_level === true &&
                        renderConfidenceColor(row.confidence)}
                    </Box>

                    {/* ✅ ROW-LEVEL HOVER ACTIONS */}
                    <HoverActionWrapper
                      show={hovered.i === idx}
                      onApprove={() => handleApprove?.(idx)}
                      onComment={() => openComment(sheet.sheet_no, idx)}
                      onBookmark={() => onBookmarkClick?.(row)}
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* ---------------- COMMENT DIALOG ---------------- */}
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
