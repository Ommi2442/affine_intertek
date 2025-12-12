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
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';

import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

import { idb_get, idb_set, idb_delete, STORES } from '../utils/idb';

/**
 * Behavior (Option A):
 *  - On first API load (jsonData arrives, not a refresh): save full JSON to IDB under
 *      key = `cdr_report_<projectId>` in STORES.CDR
 *  - When user edits -> update that field inside the stored full JSON and persist whole JSON
 *  - On browser refresh -> load full JSON from IDB and render (restores edits)
 *
 * Ref API:
 *  - getUpdatedJson() => returns current fullJson
 *  - getFieldValue(fieldName) => first matching value from fullJson
 *  - setFieldValue(fieldName, value) => updates fullJson and persists
 *  - clearDrafts() => clears stored JSON in IDB and in-memory (optional)
 */

const STORAGE_KEY_PREFIX = 'cdr_report_'; // final key: cdr_report_<projectId>

const CdrReport = forwardRef(
  ({ jsonData, editMode = false, projectId }, ref) => {
    // final storage key for entire JSON
    const storageKey = useMemo(
      () => `${STORAGE_KEY_PREFIX}${projectId ?? 'default'}`,
      [projectId]
    );

    // refresh detection (mount-time)
    const isRefreshRef = useRef(false);
    useEffect(() => {
      let navEntry;
      try {
        navEntry =
          performance.getEntriesByType &&
          performance.getEntriesByType('navigation') &&
          performance.getEntriesByType('navigation')[0];
      } catch (e) {
        navEntry = null;
      }

      const isRefresh =
        (performance.navigation && performance.navigation.type === 1) ||
        navEntry?.type === 'reload';

      isRefreshRef.current = !!isRefresh;
    }, []);

    // fullJson holds the entire CDR JSON that we render and persist
    const [fullJson, setFullJson] = useState(null);

    // expanded accordion
    const defaultOpen =
      (jsonData &&
        jsonData.Sheets &&
        jsonData.Sheets.length > 0 &&
        jsonData.Sheets[0].sheet_no) ||
      null;
    const [expandedSheet, setExpandedSheet] = useState(defaultOpen);

    // Derived sheets used for rendering:
    const sheets = useMemo(() => {
      return (
        (fullJson && fullJson.Sheets) || (jsonData && jsonData.Sheets) || []
      );
    }, [fullJson, jsonData]);

    // When jsonData arrives:
    //  - if refresh: load full JSON from IDB (restore user edits)
    //  - else: normal API load -> set fullJson = jsonData and persist it to IDB immediately
    useEffect(() => {
      if (!jsonData) return;

      // reset accordion to first sheet if available
      if (jsonData.Sheets && jsonData.Sheets.length) {
        setExpandedSheet(jsonData.Sheets[0].sheet_no);
      }

      if (isRefreshRef.current) {
        // load previously saved full JSON from IDB (restore user edits)
        idb_get(storageKey, STORES.CDR)
          .then((saved) => {
            if (saved && typeof saved === 'object') {
              setFullJson(saved);
            } else {
              // no saved JSON -> fall back to API JSON and also persist it (optional)
              setFullJson(jsonData);
              // persist API JSON so future refreshes will have it
              idb_set(storageKey, jsonData, STORES.CDR).catch(() => {});
            }
          })
          .catch(() => {
            // if any error reading, fall back to API JSON and persist
            setFullJson(jsonData);
            idb_set(storageKey, jsonData, STORES.CDR).catch(() => {});
          });
      } else {
        // fresh API load: use API JSON and persist entire JSON immediately
        setFullJson(jsonData);
        idb_set(storageKey, jsonData, STORES.CDR).catch(() => {});
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [jsonData]);

    // utility: persist current fullJson to IDB (store entire JSON)
    const persistFullJson = async (nextJson) => {
      try {
        await idb_set(storageKey, nextJson, STORES.CDR);
      } catch (e) {
        // ignore for now — could add retry or toast
        // console.error("Failed to persist fullJson", e);
      }
    };

    // update a field inside fullJson (by sheet_no and key), persist whole JSON
    const updateFieldInFullJson = (sheet_no, key, value) => {
      setFullJson((prev) => {
        const working = prev
          ? JSON.parse(JSON.stringify(prev))
          : { Sheets: [] };

        // find sheet
        const sheet = (working.Sheets || []).find(
          (s) => s.sheet_no === sheet_no
        );
        if (sheet) {
          // try Items first
          const items = sheet.Items || [];
          let updated = false;
          for (let it of items) {
            const itemKey = it.answer_cell ?? it.field;
            if (itemKey === key) {
              it.value = value;
              updated = true;
              break;
            }
          }

          // if not found in Items, try Rows data (table cells)
          if (!updated && Array.isArray(sheet.Rows)) {
            for (let r = 0; r < sheet.Rows.length; r++) {
              const row = sheet.Rows[r];
              if (!Array.isArray(row.data)) continue;
              for (let c = 0; c < row.data.length; c++) {
                const cellKey = `row_${row.start_cell ?? r}_col_${c}`;
                if (cellKey === key) {
                  row.data[c] = value;
                  updated = true;
                  break;
                }
              }
              if (updated) break;
            }
          }

          // if neither found, fall back to adding/updating a synthetic Items entry
          if (!updated) {
            sheet.Items = sheet.Items || [];
            sheet.Items.push({ field: key, answer_cell: key, value });
          }
        } else {
          // sheet not found — create minimal structure
          working.Sheets = working.Sheets || [];
          working.Sheets.push({
            sheet_no,
            sheet_name: `Sheet ${sheet_no}`,
            Items: [{ answer_cell: key, field: key, value }],
          });
        }

        // persist
        persistFullJson(working);

        return working;
      });
    };

    // helpers for parent & internal usage
    const getFieldValue = (sheet_no, key) => {
      if (!fullJson || !Array.isArray(fullJson.Sheets)) return undefined;
      const sheet = fullJson.Sheets.find((s) => s.sheet_no === sheet_no);
      if (!sheet) return undefined;

      // try Items
      for (const it of sheet.Items || []) {
        const itemKey = it.answer_cell ?? it.field;
        if (itemKey === key) return it.value ?? null;
      }

      // try Rows
      for (const r of sheet.Rows || []) {
        if (!Array.isArray(r.data)) continue;
        for (let c = 0; c < r.data.length; c++) {
          const cellKey = `row_${r.start_cell ?? 0}_col_${c}`;
          if (cellKey === key) return r.data[c] ?? null;
        }
      }

      return undefined;
    };

    // Expose imperative API on ref
    useImperativeHandle(
      ref,
      () => ({
        getUpdatedJson: () => fullJson ?? jsonData ?? { Sheets: [] },
        // find first matching field across sheets (legacy API)
        getFieldValue: (fieldName) => {
          const source = fullJson ?? jsonData;
          if (!source || !Array.isArray(source.Sheets)) return undefined;
          for (const s of source.Sheets) {
            for (const it of s.Items || []) {
              if (it.field === fieldName) return it.value ?? null;
            }
          }
          return undefined;
        },
        // set by fieldName (first match) — updates fullJson and persists
        setFieldValue: (fieldName, value) => {
          setFullJson((prev) => {
            const working = prev
              ? JSON.parse(JSON.stringify(prev))
              : { Sheets: [] };
            let found = false;
            for (const s of working.Sheets || []) {
              for (const it of s.Items || []) {
                if (it.field === fieldName) {
                  it.value = value;
                  found = true;
                  break;
                }
              }
              if (found) break;
            }

            if (!found) {
              // fallback: add to first sheet
              if (!working.Sheets) working.Sheets = [];
              if (working.Sheets.length === 0) {
                working.Sheets.push({
                  sheet_no: 1,
                  sheet_name: 'Sheet 1',
                  Items: [],
                });
              }
              working.Sheets[0].Items = working.Sheets[0].Items || [];
              working.Sheets[0].Items.push({
                field: fieldName,
                answer_cell: fieldName,
                value,
              });
            }

            persistFullJson(working);
            return working;
          });
          return true;
        },
        clearDrafts: async () => {
          setFullJson(jsonData ?? { Sheets: [] });
          try {
            await idb_set(storageKey, jsonData ?? { Sheets: [] }, STORES.CDR);
          } catch (e) {
            // ignore
          }
        },
        // direct update API for a specific sheet/key
        updateFieldInFullJson: (sheet_no, key, value) => {
          updateFieldInFullJsonPublic(sheet_no, key, value);
        },
      }),
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [fullJson, jsonData, storageKey]
    );

    // small wrapper to expose updateFieldInFullJson via closure (for imperative handle)
    const updateFieldInFullJsonPublic = (sheet_no, key, value) => {
      updateFieldInFullJson(sheet_no, key, value);
    };

    // Render helpers
    const handleAccordionChange = (sheet_no) => (_, expanded) => {
      setExpandedSheet(expanded ? sheet_no : null);
    };

    const renderItem = (sheet_no, item, index) => {
      const key = item.answer_cell ?? item.field ?? `item_${index}`;
      const currentValue =
        (fullJson && getFieldValue(sheet_no, key)) ?? item.value ?? '';

      const isEditable = !!(editMode && item.user_editable);

      if (item.task_type === 'title') {
        return (
          <Box key={key} sx={{ my: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              {item.field}
            </Typography>
          </Box>
        );
      }

      if (item.task_type === 'photo') {
        return (
          <Box key={key} sx={{ my: 1 }}>
            <Typography variant="body2">{item.field}</Typography>
            <Typography variant="caption" display="block">
              {item.photo_path || 'Photo field'}
            </Typography>
          </Box>
        );
      }

      return (
        <Box key={key} sx={{ display: 'flex', gap: 2, my: 1 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="body2">{item.field}</Typography>
          </Box>

          <Box sx={{ flex: 2 }}>
            <TextField
              fullWidth
              size="small"
              value={currentValue ?? ''}
              disabled={!isEditable}
              onChange={(e) => {
                if (!isEditable) return;
                updateFieldInFullJson(sheet_no, key, e.target.value);
              }}
            />
          </Box>
        </Box>
      );
    };

    const renderRowTable = (sheet_no, rows = []) => {
      const headingsRow = rows.find((r) => r.row_type === 'column_headings');
      const dataRows = rows.filter((r) => r.row_type === 'table_data');

      if (!headingsRow) return null;

      return (
        <TableContainer component={Paper} sx={{ my: 1 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                {headingsRow.data.map((h, i) => (
                  <TableCell key={i} sx={{ fontWeight: 700 }}>
                    {h}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>

            <TableBody>
              {dataRows.map((row, ridx) => (
                <TableRow key={ridx}>
                  {(row.data || []).map((cell, cidx) => {
                    const key = `row_${row.start_cell ?? ridx}_col_${cidx}`;
                    const draftVal = fullJson
                      ? getFieldValue(sheet_no, key)
                      : undefined;
                    const displayVal =
                      draftVal !== undefined ? draftVal : (cell ?? '');
                    const isEditable = !!(editMode && row.user_editable);

                    return (
                      <TableCell key={cidx}>
                        {isEditable ? (
                          <TextField
                            size="small"
                            value={displayVal}
                            onChange={(e) =>
                              updateFieldInFullJson(
                                sheet_no,
                                key,
                                e.target.value
                              )
                            }
                          />
                        ) : (
                          <Typography variant="body2">{displayVal}</Typography>
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      );
    };

    // Main render
    return (
      <Box>
        {(!sheets || sheets.length === 0) && (
          <Typography>No sheets available</Typography>
        )}

        {sheets.map((sheet) => {
          const sid = sheet.sheet_no;
          return (
            <Accordion
              key={sid}
              expanded={expandedSheet === sid}
              onChange={handleAccordionChange(sid)}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Typography sx={{ fontWeight: 700 }}>
                    {sheet.sheet_no}. {sheet.sheet_name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'gray' }}>
                    ({(sheet.Items && sheet.Items.length) || 0} fields)
                  </Typography>
                </Box>
              </AccordionSummary>

              <AccordionDetails>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {Array.isArray(sheet.Items) &&
                    sheet.Items.map((item, idx) => renderItem(sid, item, idx))}

                  {Array.isArray(sheet.Rows) && renderRowTable(sid, sheet.Rows)}

                  <Divider sx={{ mt: 2 }} />

                  <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() =>
                        idb_set(storageKey, fullJson ?? jsonData, STORES.CDR)
                      }
                    >
                      Save draft
                    </Button>

                    <Button
                      variant="text"
                      size="small"
                      onClick={async () => {
                        // clear persisted full JSON and reset to API JSON in memory
                        try {
                          await idb_set(
                            storageKey,
                            jsonData ?? { Sheets: [] },
                            STORES.CDR
                          );
                        } catch (e) {}
                        setFullJson(jsonData ?? { Sheets: [] });
                      }}
                    >
                      Reset to API JSON
                    </Button>
                  </Box>
                </Box>
              </AccordionDetails>
            </Accordion>
          );
        })}
      </Box>
    );
  }
);

export default CdrReport;
