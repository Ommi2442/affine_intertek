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
      isHardRefresh,
    },
    ref
  ) => {
    const storageKey = `${STORAGE_KEY_PREFIX}${projectId ?? 'default'}`;
    //const isRefreshRef = useRef(false);

    const [fullJson, setFullJson] = useState(null);

    const sheets = useMemo(
      () =>
        (fullJson && fullJson.Sheets) || (jsonData && jsonData.Sheets) || [],
      [fullJson, jsonData]
    );

    const [expandedSheet, setExpandedSheet] = useState(null);

    /* -------- REFRESH DETECT -------- */
    // useEffect(() => {
    //   const nav = performance.getEntriesByType?.('navigation')?.[0];
    //   isRefreshRef.current =
    //     nav?.type === 'reload' || performance.navigation?.type === 1;
    // }, []);

    /* -------- LOAD / SAVE -------- */
    // useEffect(() => {
    //   if (!jsonData) return;

    //   if (isRefreshRef.current) {
    //     idb_get(storageKey, STORES.CDR).then((saved) => {
    //       if (saved) setFullJson(saved);
    //       else {
    //         setFullJson(jsonData);
    //         idb_set(storageKey, jsonData, STORES.CDR);
    //       }
    //     });
    //   } else {
    //     setFullJson(jsonData);
    //     idb_set(storageKey, jsonData, STORES.CDR);
    //   }

    //   setExpandedSheet(jsonData?.Sheets?.[0]?.sheet_no ?? null);
    // }, [jsonData]);

    useEffect(() => {
      if (!jsonData) return;

      let cancelled = false;

      const load = async () => {
        // HARD REFRESH → reuse IndexedDB only
        if (isHardRefresh) {
          const saved = await idb_get(storageKey, STORES.CDR);
          if (cancelled) return;

          if (saved) {
            console.log('CDR restored from IndexedDB (inside CdrReport)');
            setFullJson(saved);
            setExpandedSheet(saved?.Sheets?.[0]?.sheet_no ?? null);
            return;
          }

          // fallback only if cache truly missing
          console.warn('No CDR cache found → falling back to backend JSON');
          setFullJson(jsonData);
          setExpandedSheet(jsonData?.Sheets?.[0]?.sheet_no ?? null);
          return;
        }

        // NORMAL LOAD → backend is authoritative
        setFullJson(jsonData);
        setExpandedSheet(jsonData?.Sheets?.[0]?.sheet_no ?? null);

        // overwrite cache only on non-refresh
        await idb_set(storageKey, jsonData, STORES.CDR);
      };

      load();

      return () => {
        cancelled = true;
      };
    }, [jsonData, isHardRefresh, storageKey]);

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
      let didPromote = false;
      let updatedJson = null;

      setFullJson((prev) => {
        if (!prev) return prev;

        const next = JSON.parse(JSON.stringify(prev));
        const sheet = next.Sheets.find((s) => s.sheet_no === sheet_no);
        if (!sheet) return prev;

        const item = sheet.Items[itemIndex];
        if (!item || item.is_user_approved) return prev;

        const c = Number(item.confidence);
        const normalized = c <= 1 ? Math.round(c * 100) : Math.round(c);

        const isMediumOrLow = !Number.isNaN(normalized) && normalized < 75;

        sheet.Items[itemIndex] = {
          ...item,
          is_user_approved: true,
          confidence: isMediumOrLow ? 100 : item.confidence,
        };

        if (isMediumOrLow) didPromote = true;

        updatedJson = next;
        return next;
      });

      if (updatedJson) {
        await idb_set(storageKey, updatedJson, STORES.CDR);
      }

      // Recalculate ONLY if confidence changed (Medium/Low → High)
      if (didPromote) {
        onConfidenceChange?.();
      }
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

        const isModified = item.value !== value;

        item.value = value;

        if (isModified && item.is_user_edited !== true) {
          item.is_user_edited = true; //  ONLY typing sets this
          onConfidenceChange?.(); //  realtime user-edited
        }

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
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>
    );
  }
);

export default CdrReport;
