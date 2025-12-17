/* eslint-disable */
import React, {
  forwardRef,
  useImperativeHandle,
  useState,
  useEffect,
  useMemo,
  useRef,
} from 'react';

import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  Typography,
  TextField,
  Button,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Paper,
} from '@mui/material';

import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { idb_get, idb_set, STORES } from '../utils/idb';

const STORAGE_KEY_PREFIX = 'cdr_report_';

/* ---------------- HELPERS ---------------- */
const colLetterToIndex = (cell = '') => (cell ? cell.charCodeAt(0) - 65 : 0);

const colSpanFromRange = (startCell, endCell) => {
  if (!startCell || !endCell) return 1;
  return colLetterToIndex(endCell) - colLetterToIndex(startCell) + 1;
};

const rowNumberFromCell = (cell = '') =>
  Number(cell.replace(/[A-Z]/g, '')) || 0;

/* ---------------- COMPONENT ---------------- */
const CdrReport = forwardRef(
  ({ jsonData, editMode = false, projectId }, ref) => {
    const storageKey = `${STORAGE_KEY_PREFIX}${projectId ?? 'default'}`;
    const isRefreshRef = useRef(false);

    const [fullJson, setFullJson] = useState(null);

    const sheets = useMemo(
      () =>
        (fullJson && fullJson.Sheets) || (jsonData && jsonData.Sheets) || [],
      [fullJson, jsonData]
    );

    const [expandedSheet, setExpandedSheet] = useState(null);

    /* -------- REFRESH DETECT -------- */
    useEffect(() => {
      const nav = performance.getEntriesByType?.('navigation')?.[0];
      isRefreshRef.current =
        nav?.type === 'reload' || performance.navigation?.type === 1;
    }, []);

    /* -------- LOAD / SAVE -------- */
    useEffect(() => {
      if (!jsonData) return;

      if (isRefreshRef.current) {
        idb_get(storageKey, STORES.CDR).then((saved) => {
          if (saved) setFullJson(saved);
          else {
            setFullJson(jsonData);
            idb_set(storageKey, jsonData, STORES.CDR);
          }
        });
      } else {
        setFullJson(jsonData);
        idb_set(storageKey, jsonData, STORES.CDR);
      }

      setExpandedSheet(jsonData?.Sheets?.[0]?.sheet_no ?? null);
    }, [jsonData]);

    const persist = (next) =>
      idb_set(storageKey, next, STORES.CDR).catch(() => {});

    /* -------- UPDATE FIELD -------- */
    const updateField = (sheet_no, key, value) => {
      setFullJson((prev) => {
        const next = JSON.parse(JSON.stringify(prev));
        const sheet = next.Sheets.find((s) => s.sheet_no === sheet_no);
        if (!sheet) return prev;

        const item = sheet.Items.find(
          (i) => (i.answer_cell ?? i.field) === key
        );
        if (item) item.value = value;

        persist(next);
        return next;
      });
    };

    /* -------- REF API -------- */
    useImperativeHandle(ref, () => ({
      getUpdatedJson: () => fullJson ?? jsonData,
    }));

    /* =========================
       SHEET 1 – EXCEL DYNAMIC
       ========================= */
    const renderSheet1Excel = (sheet) => {
      const border = { border: '1px solid #000' };

      /* group by row number */
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

    /* =========================
       SHEET 3 – IMAGE RENDER
       ========================= */
    const renderSheet3Photos = (sheet) => (
      <Box>
        {sheet.Items.map((item, idx) => (
          <Box key={idx} sx={{ mb: 3 }}>
            <Typography fontWeight={600}>{item.field}</Typography>
            {item.photo_path && (
              <Box
                component="img"
                src={item.photo_path}
                sx={{
                  maxWidth: '100%',
                  maxHeight: 300,
                  border: '1px solid #ccc',
                  mt: 1,
                }}
              />
            )}
          </Box>
        ))}
      </Box>
    );

    /* =========================
       DEFAULT RENDER
       ========================= */
    const renderDefaultItems = (sheet) =>
      sheet.Items.map((item, idx) => {
        const editable = editMode && item.user_editable;
        return (
          <Box key={idx} sx={{ display: 'flex', gap: 2, my: 1 }}>
            <Typography sx={{ flex: 1 }}>{item.field}</Typography>
            <Box sx={{ flex: 2 }}>
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
                <Typography>{item.value}</Typography>
              )}
            </Box>
          </Box>
        );
      });

    /* =========================
       MAIN RENDER
       ========================= */
    return (
      <Box>
        {sheets.map((sheet) => (
          <Accordion
            key={sheet.sheet_no}
            expanded={expandedSheet === sheet.sheet_no}
            onChange={(_, open) =>
              setExpandedSheet(open ? sheet.sheet_no : null)
            }
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight={700}>
                {sheet.sheet_no}. {sheet.sheet_name}
              </Typography>
            </AccordionSummary>

            <AccordionDetails>
              {sheet.sheet_no === 1
                ? renderSheet1Excel(sheet)
                : sheet.sheet_no === 3
                  ? renderSheet3Photos(sheet)
                  : renderDefaultItems(sheet)}

              <Divider sx={{ my: 2 }} />

              <Button
                size="small"
                variant="outlined"
                onClick={() => idb_set(storageKey, fullJson, STORES.CDR)}
              >
                Save draft
              </Button>
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>
    );
  }
);

export default CdrReport;
