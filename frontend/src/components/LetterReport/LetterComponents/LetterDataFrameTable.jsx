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

const HEADERS = ['Clause', 'Requirement of the Clause', 'Remark and Findings'];

const emptyRow = () => ({
  Clause: '',
  'Requirement of the Clause': '',
  'Remark and Findings': '',
  __isNew: true,
});

const LetterDataFrameTable = ({ item, editMode, onChange }) => {
  if (!item || !Array.isArray(item.value)) return null;

  const rows = item.value;

  /* -------- UPDATE CELL -------- */
  const updateCell = (rowIndex, key, value) => {
    const next = [...rows];
    next[rowIndex] = { ...next[rowIndex], [key]: value };
    item.value = next; // mutate source json (same as your LetterField pattern)
    onChange?.();
  };

  /* -------- ADD ROW -------- */
  const addRow = () => {
    item.value = [...rows, emptyRow()];
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
            {/*  Confidence column */}
            <TableCell
              align="center"
              sx={{
                width: 78,
                minWidth: 78,
                maxWidth: 78,
                fontWeight: 700,
                border: '1px solid #ccc',
                backgroundColor: '#ffeb3b',
                padding: '4px',
                whiteSpace: 'nowrap',
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
                  wordBreak: 'break-word',
                }}
              >
                Action
              </TableCell>
            )}
          </TableRow>
        </TableHead>

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

              {/*  Confidence DOT per row */}
              <TableCell
                align="center"
                sx={{
                  border: '1px solid #ccc',
                  width: '6%',
                }}
              >
                {/*  Show dot only for existing rows */}
                {!row.__isNew &&
                  renderConfidenceColor(item.confidence, false, true, true)}
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

export default LetterDataFrameTable;
