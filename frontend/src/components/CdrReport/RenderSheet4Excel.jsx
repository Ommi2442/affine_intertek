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

/* ---------------- COMPONENT ---------------- */
const RenderSheet4Excel = ({ sheet, editMode, updateField }) => {
  /* ✅ SAFETY GUARD */
  if (!sheet || !Array.isArray(sheet.Rows)) {
    return null;
  }

  const titleItem = sheet.Items?.[0] ?? null;
  const headerRow = sheet.Rows.find((r) => r.row_type === 'column_headings');
  const dataRows = sheet.Rows.filter((r) => r.row_type === 'table_data');

  const border = { border: '1px solid #000' };

  const renderCell = (value, editable, onChange) => (
    <TableCell
      sx={{
        ...border,
        whiteSpace: 'normal',
        wordBreak: 'break-word',
        overflowWrap: 'anywhere',
        verticalAlign: 'middle',
      }}
    >
      {editable ? (
        <TextField
          size="small"
          fullWidth
          value={value ?? ''}
          onChange={onChange}
        />
      ) : (
        <Typography>{value ?? ''}</Typography>
      )}
    </TableCell>
  );

  return (
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
                {renderCell(row.marks_of_conf, editable, (e) =>
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
  );
};

export default RenderSheet4Excel;
