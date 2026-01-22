/* eslint-disable */
import React from 'react';
import {
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  IconButton,
  Button,
  Box,
  TextField,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { renderConfidenceColor } from '../../../utils/renderConfidenceColor';

const makeEmptyRow = (headers) => {
  const row = {};
  headers.forEach((h) => {
    row[h] = '';
  });
  row.__isNew = true;
  return row;
};

const LetterCriticalDataFrameTable = ({
  item,
  editMode,
  onChange,
  renderHoverActions,
}) => {
  if (!item || !Array.isArray(item.value)) return null;

  const rows = item.value;

  // 🔹 Matrix-style headers: use all numeric keys
  const HEADERS = React.useMemo(() => {
    if (!rows.length) return [];
    const colSet = new Set();
    rows.forEach((r) => Object.keys(r).forEach((k) => colSet.add(String(k))));
    return Array.from(colSet).sort((a, b) => Number(a) - Number(b));
  }, [rows]);

  const [hoveredRow, setHoveredRow] = React.useState(null);

  /* -------- UPDATE CELL -------- */
  const updateCell = (rowIndex, key, value) => {
    const next = [...rows];
    next[rowIndex] = {
      ...next[rowIndex],
      [key]: value,
    };
    item.value = next;
    onChange?.();
  };

  /* -------- ADD ROW -------- */
  const addRow = () => {
    const next = [...rows, makeEmptyRow(HEADERS)];
    item.value = next;
    onChange?.();
  };

  /* -------- DELETE ROW -------- */
  const deleteRow = (rowIndex) => {
    const next = rows.filter((_, i) => i !== rowIndex);
    item.value = next;
    onChange?.();
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Table
        size="small"
        sx={{ border: '1px solid #ccc', tableLayout: 'fixed', width: '100%' }}
      >
        {/* ================= HEADERS (0,1,2,3...) ================= */}
        <TableHead>
          <TableRow sx={{ backgroundColor: '#ffeb3b' }}>
            {HEADERS.map((h) => (
              <TableCell
                key={h}
                sx={{ fontWeight: 700, border: '1px solid #ccc' }}
              >
                {h}
              </TableCell>
            ))}
            <TableCell
              align="center"
              sx={{
                width: 78,
                minWidth: 78,
                maxWidth: 78,
                fontWeight: 700,
                border: '1px solid #ccc',
                backgroundColor: '#ffeb3b',
              }}
            >
              Confidence
            </TableCell>
            {editMode && (
              <TableCell
                sx={{
                  width: '7%',
                  textAlign: 'center',
                  backgroundColor: '#ffeb3b',
                  fontWeight: 600,
                }}
              >
                Action
              </TableCell>
            )}
          </TableRow>
        </TableHead>

        {/* ================= BODY ================= */}
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {HEADERS.map((key) => (
                <TableCell key={key} sx={{ border: '1px solid #ccc' }}>
                  <TextField
                    fullWidth
                    size="small"
                    value={row[key] ?? ''}
                    InputProps={{ readOnly: !editMode }}
                    onChange={(e) => updateCell(rowIndex, key, e.target.value)}
                  />
                </TableCell>
              ))}

              {/* Confidence + Hover */}
              <TableCell
                align="center"
                sx={{
                  border: '1px solid #ccc',
                  width: '6%',
                  position: 'relative',
                }}
                onMouseEnter={() => setHoveredRow(rowIndex)}
                onMouseLeave={() => setHoveredRow(null)}
              >
                {!row.__isNew &&
                  renderConfidenceColor(item.confidence, false, true, true)}

                {hoveredRow === rowIndex &&
                  typeof renderHoverActions === 'function' &&
                  renderHoverActions(null, null, true, item)}
              </TableCell>

              {editMode && (
                <TableCell sx={{ border: '1px solid #ccc' }}>
                  <IconButton size="small" onClick={() => deleteRow(rowIndex)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {editMode && (
        <Box sx={{ mt: 1 }}>
          <Button size="small" variant="outlined" onClick={addRow}>
            + Add Row
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default LetterCriticalDataFrameTable;
