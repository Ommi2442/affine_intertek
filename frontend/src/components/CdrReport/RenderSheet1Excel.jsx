/* eslint-disable */
import React from 'react';
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

/* ---------------- HELPERS (LOCAL) ---------------- */
const colLetterToIndex = (cell = '') => (cell ? cell.charCodeAt(0) - 65 : 0);

const colSpanFromRange = (startCell, endCell) => {
  if (!startCell || !endCell) return 1;
  return colLetterToIndex(endCell) - colLetterToIndex(startCell) + 1;
};

const rowNumberFromCell = (cell = '') =>
  Number(cell.replace(/[A-Z]/g, '')) || 0;

/* ---------------- COMPONENT ---------------- */
const RenderSheet1Excel = ({ sheet, editMode, updateField }) => {
  /* ✅ SAFETY GUARD */
  if (!sheet || !Array.isArray(sheet.Items)) {
    return null;
  }

  const border = { border: '1px solid #000' };

  /* group items by row number */
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

  const renderValue = (item, colSpan = 1) => {
    const editable = editMode && item.user_editable;

    return (
      <TableCell sx={border} colSpan={colSpan}>
        {editable ? (
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
        ) : (
          <Typography>{item.value ?? ''}</Typography>
        )}
      </TableCell>
    );
  };

  return (
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
                {rowItems.map((item, idx) => {
                  /* FIELD MERGE (TITLE ROW) */
                  if (item.field_merged && item.fm_range) {
                    const span = colSpanFromRange(
                      item.question_cell,
                      item.fm_range
                    );
                    return (
                      <TableCell
                        key={idx}
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

                  /* NORMAL FIELD CELL */
                  const fieldCell = (
                    <TableCell key={`${idx}-f`} sx={border}>
                      {item.field}
                    </TableCell>
                  );

                  /* VALUE MERGE */
                  if (item.value_merged && item.vm_range) {
                    const span = colSpanFromRange(
                      item.answer_cell,
                      item.vm_range
                    );
                    return (
                      <React.Fragment key={idx}>
                        {fieldCell}
                        {renderValue(item, span)}
                      </React.Fragment>
                    );
                  }

                  /* NORMAL FIELD + VALUE */
                  return (
                    <React.Fragment key={idx}>
                      {fieldCell}
                      {renderValue(item, 1)}
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

export default RenderSheet1Excel;
