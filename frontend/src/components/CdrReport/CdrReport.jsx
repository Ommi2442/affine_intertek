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
import { idb_get, idb_set, STORES } from '../../utils/idb';
import RenderSheet1Excel from './RenderSheet1Excel';
import RenderSheet3Excel from './RenderSheet3Excel';
import RenderSheet6Excel from './RenderSheet6Excel';
import RenderSheet4Excel from './RenderSheet4Excel';
import RenderSheetDefaultExcel from './RenderSheetDefaultExcel';

const STORAGE_KEY_PREFIX = 'cdr_report_';

/* ---------------- COMPONENT ---------------- */
const CdrReport = forwardRef(
  (
    { jsonData, editMode = false, projectId, openComment, onBookmarkClick },
    ref
  ) => {
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
              <Typography fontWeight={700}>{sheet.sheet_name}</Typography>
            </AccordionSummary>

            <AccordionDetails>
              {sheet.sheet_no === 1 ? (
                <RenderSheet1Excel
                  sheet={sheet}
                  editMode={editMode}
                  updateField={updateField}
                  onBookmarkClick={onBookmarkClick}
                />
              ) : sheet.sheet_no === 3 ? (
                <RenderSheet3Excel sheet={sheet} />
              ) : sheet.sheet_no === 4 ? (
                <RenderSheet4Excel
                  sheet={sheet}
                  editMode={editMode}
                  updateField={updateField}
                  onBookmarkClick={onBookmarkClick}
                />
              ) : sheet.sheet_no === 6 ? (
                <RenderSheet6Excel
                  sheet={sheet}
                  editMode={editMode}
                  updateField={updateField}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                />
              ) : (
                <RenderSheetDefaultExcel
                  sheet={sheet}
                  editMode={editMode}
                  updateField={updateField}
                  onBookmarkClick={onBookmarkClick}
                />
              )}

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
