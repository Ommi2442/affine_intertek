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
  Tooltip,
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

const normalizeKey = (k) =>
  typeof k === 'string' ? k.trim().replace(/\s+/g, ' ') : k;

const HIDDEN_COLUMNS = new Set([
  'text_support',
  'confidence',
  'is_user_edited',
  'user_comments',
]);

const LetterDataFrameTable = ({
  item,
  editMode,
  onChange,
  renderHoverActions,
}) => {
  if (!item || !Array.isArray(item.value)) return null;

  const rows = item.value;

  // -------- DERIVE HEADERS DYNAMICALLY --------
  const HEADERS = React.useMemo(() => {
    if (!rows.length) return [];

    const keySet = new Set();

    rows.forEach((r) => {
      if (r && typeof r === 'object') {
        Object.keys(r).forEach((k) => {
          const nk = normalizeKey(k);

          if (nk.startsWith('__') || HIDDEN_COLUMNS.has(nk.toLowerCase())) {
            return;
          }

          keySet.add(nk);
        });
      }
    });

    return Array.from(keySet);
  }, [rows]);

  const [hoveredRow, setHoveredRow] = React.useState(null);

  /* -------- UPDATE CELL -------- */
  const updateCell = (rowIndex, key, value) => {
    const next = [...rows];

    const originalKey =
      Object.keys(next[rowIndex]).find((k) => normalizeKey(k) === key) ?? key;

    next[rowIndex] = {
      ...next[rowIndex],
      [originalKey]: value,
      is_user_edited: true,
    };

    onChange?.(next);
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

            {/* Confidence column */}
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
              {HEADERS.map((key) => {
                const cellValue =
                  row[key] ??
                  row[Object.keys(row).find((k) => normalizeKey(k) === key)] ??
                  '';

                return (
                  <TableCell key={key} sx={{ border: '1px solid #ccc' }}>
                    <Tooltip
                      title={
                        <span
                          style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}
                        >
                          {typeof cellValue === 'object'
                            ? cellValue?.comment
                            : cellValue}
                        </span>
                      }
                      arrow
                      placement="top"
                    >
                      <TextField
                        fullWidth
                        size="small"
                        value={
                          typeof cellValue === 'object' && cellValue !== null
                            ? (cellValue.comment ?? '')
                            : (cellValue ?? '')
                        }
                        InputProps={{
                          readOnly: !editMode,
                          sx: {
                            '& input': {
                              textOverflow: 'ellipsis',
                              overflow: 'hidden',
                              whiteSpace: 'nowrap',
                            },
                          },
                        }}
                        onChange={(e) =>
                          updateCell(rowIndex, key, e.target.value)
                        }
                      />
                    </Tooltip>
                  </TableCell>
                );
              })}

              {/* Confidence DOT + Hover Actions */}
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
                  renderConfidenceColor(
                    item.confidence,
                    row.is_user_edited,
                    true,
                    true
                  )}

                {hoveredRow === rowIndex &&
                  typeof renderHoverActions === 'function' &&
                  renderHoverActions(null, null, true, row)}
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
