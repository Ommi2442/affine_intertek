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

  /* ---------------- CELL RENDER ---------------- */
  const renderCell = (value, editable, itemIndex, onChange = () => {}) => (
    <TableCell
      sx={{
        ...border,
        whiteSpace: 'normal',
        wordBreak: 'break-word',
        overflowWrap: 'anywhere',
        verticalAlign: 'middle',
        position: 'relative', // ✅ REQUIRED
      }}
      onMouseEnter={() => editable && setHovered({ i: itemIndex })}
      onMouseLeave={() => editable && setHovered({ i: null })}
    >
      {editable ? (
        <>
          <TextField
            size="small"
            fullWidth
            value={value ?? ''}
            onChange={onChange}
          />

          <HoverActionWrapper
            show={hovered.i === itemIndex}
            onApprove={() => handleApprove?.(itemIndex)}
            onComment={() => openComment(sheet.sheet_no, itemIndex)}
            onBookmark={() => {
              const row = sheet.Rows[itemIndex];
              onBookmarkClick?.(row ?? { __i: itemIndex });
            }}
          />
        </>
      ) : (
        <Typography>{value ?? ''}</Typography>
      )}
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
                <TableRow key={idx}>
                  {renderCell(row.photo_no, false, null)}
                  {renderCell(row.item_no, false, null)}

                  {renderCell(row.name, editable, idx, (e) =>
                    updateField(sheet.sheet_no, `name_${idx}`, e.target.value)
                  )}

                  {renderCell(row.manufacturer, editable, idx, (e) =>
                    updateField(
                      sheet.sheet_no,
                      `manufacturer_${idx}`,
                      e.target.value
                    )
                  )}

                  {renderCell(row.type_model, editable, idx, (e) =>
                    updateField(
                      sheet.sheet_no,
                      `type_model_${idx}`,
                      e.target.value
                    )
                  )}

                  {renderCell(row.technical_data, editable, idx, (e) =>
                    updateField(
                      sheet.sheet_no,
                      `technical_data_${idx}`,
                      e.target.value
                    )
                  )}

                  {renderCell(row.marks_of_conf, editable, idx, (e) =>
                    updateField(
                      sheet.sheet_no,
                      `marks_of_conf_${idx}`,
                      e.target.value
                    )
                  )}
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

export default RenderSheet4Excel;
