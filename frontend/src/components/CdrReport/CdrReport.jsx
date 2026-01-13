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
    {
      jsonData,
      editMode = false,
      projectId,
      openComment,
      onBookmarkClick,
      cdrFinalised,
      onConfidenceChange,
    },
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

    //handleapprove for approving ai confidence score
    // const handleApprove = (sheet_no, itemIndex) => {
    //   setFullJson((prev) => {
    //     const next = JSON.parse(JSON.stringify(prev));
    //     const sheet = next.Sheets.find((s) => s.sheet_no === sheet_no);
    //     if (!sheet) return prev;

    //     const item = sheet.Items[itemIndex];
    //     if (!item || item.is_user_approved) return prev;

    //     const c = Number(item.confidence);

    //     // CASE 1: Edited + approve → User Edited
    //     if (item.is_user_modified === true) {
    //       item.is_user_approved = true;
    //       item.is_user_edited = true;
    //       item.confidence = 100;
    //     }
    //     // CASE 2: Medium / Low + approve → Promote to High
    //     else if (!Number.isNaN(c) && c < 75) {
    //       item.is_user_approved = true;
    //       item.confidence = 100;
    //     }

    //     persist(next);
    //     onConfidenceChange?.();
    //     return next;
    //   });
    // };
    const handleApprove = async (sheet_no, itemIndex) => {
      let updatedJson = null;

      setFullJson((prev) => {
        if (!prev) return prev;

        const next = JSON.parse(JSON.stringify(prev));
        const sheet = next.Sheets.find((s) => s.sheet_no === sheet_no);
        if (!sheet) return prev;

        const item = sheet.Items[itemIndex];
        if (!item || item.is_user_approved) return prev;

        const c = Number(item.confidence);

        const shouldPromote =
          item.accuracy_level === true && !Number.isNaN(c) && c < 100;

        sheet.Items[itemIndex] = {
          ...item,
          is_user_approved: true,
          confidence: shouldPromote ? 100 : item.confidence,
        };

        updatedJson = next; //  store for IndexedDB write
        return next;
      });

      /*  THIS is what was missing in CDR */
      if (updatedJson) {
        await idb_set(storageKey, updatedJson, STORES.CDR);
      }

      onConfidenceChange?.();
    };

    /* -------- UPDATE FIELD -------- */
    const updateField = (sheet_no, key, value) => {
      setFullJson((prev) => {
        const next = JSON.parse(JSON.stringify(prev));
        const sheet = next.Sheets.find((s) => s.sheet_no === sheet_no);
        if (!sheet) return prev;

        const item = sheet.Items.find(
          (i) => (i.answer_cell ?? i.field) === key
        );
        if (!item) return prev;

        // mark user modification only if value changed
        const isModified = item.value !== value;

        item.value = value;
        if (isModified) {
          item.is_user_modified = true;
        }

        persist(next);
        onConfidenceChange?.(); // realtime update
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
                  handleApprove={(itemIndex) =>
                    handleApprove(sheet.sheet_no, itemIndex)
                  }
                  onBookmarkClick={onBookmarkClick}
                />
              ) : sheet.sheet_no === 3 ? (
                <RenderSheet3Excel
                  sheet={sheet}
                  editMode={editMode}
                  isFinalised={cdrFinalised}
                  onChange={(updatedItems) => {
                    sheet.Items = updatedItems;
                  }}
                />
              ) : sheet.sheet_no === 4 ? (
                <RenderSheet4Excel
                  sheet={sheet}
                  editMode={editMode}
                  updateField={updateField}
                  handleApprove={(itemIndex) =>
                    handleApprove(sheet.sheet_no, itemIndex)
                  }
                  onBookmarkClick={onBookmarkClick}
                />
              ) : sheet.sheet_no === 6 ? (
                <RenderSheet6Excel
                  sheet={sheet}
                  editMode={editMode}
                  updateField={updateField}
                  openComment={openComment}
                  handleApprove={(itemIndex) =>
                    handleApprove(sheet.sheet_no, itemIndex)
                  }
                  onBookmarkClick={onBookmarkClick}
                />
              ) : (
                <RenderSheetDefaultExcel
                  sheet={sheet}
                  editMode={editMode}
                  updateField={updateField}
                  handleApprove={(itemIndex) =>
                    handleApprove(sheet.sheet_no, itemIndex)
                  }
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
