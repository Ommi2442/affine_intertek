/* eslint-disable */
import React, {
  useState,
  useEffect,
  useRef,
  useMemo,
  forwardRef,
  useImperativeHandle,
} from 'react';

import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Divider,
  CircularProgress,
  Pagination,
  IconButton,
  Checkbox,
  Box,
} from '@mui/material';

import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ChatBubbleOutlineOutlinedIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';

import './DataTable.css';
import { idb_set, idb_get } from '../utils/idb';
import CommentDialog from './CommentDialog';
import { useSelector } from 'react-redux';
import { renderConfidenceColor } from '../utils/renderConfidenceColor';
import { renderFieldWithNewLines } from '../Helpers/renderFieldWithNewLines';
import { renderFieldWithCheckboxAndNewLines } from '../Helpers/renderFieldWithCheckboxAndNewLine';
import { RenderPage6Images } from '../Helpers/RenderPage6Images';
import { RenderPage5DynamicGroups } from './PageRenderers/RenderPage5DynamicGroups';

const DataTable = forwardRef(
  (
    {
      jsonData,
      onBookmarkClick,
      onConfidenceChange,
      editMode = false,
      isHardRefresh,
    },
    ref
  ) => {
    const containerRef = useRef(null);
    const sentinelRef = useRef(null);
    const pageRefs = useRef({});

    const confidenceScore = useSelector((state) => state.confidence);
    //console.log('confidencescor', confidenceScore);

    const [tables, setTables] = useState([]);
    const [visiblePages, setVisiblePages] = useState(1);
    const [currentPageIndex, setCurrentPageIndex] = useState(0);
    const [loading, setLoading] = useState(false);
    const [hovered, setHovered] = useState({ t: null, i: null });

    const [isCommentOpen, setIsCommentOpen] = useState(false);
    const [currentCommentText, setCurrentCommentText] = useState('');
    const commentTargetRef = useRef({ t: null, i: null });
    const [commentHistory, setCommentHistory] = useState([]);

    // Track whether this page load is a browser refresh
    //const isRefreshRef = useRef(false);

    // --------------------
    // helper: checks
    // --------------------
    // Return true only when:
    //  - item exists
    //  - item.user_editable === true
    //  - editMode === true (user clicked Edit/Refine)
    //  - item.is_textbox !== false (textbox allowed)
    const normalizeToArray = (v) => {
      // already correct format
      if (Array.isArray(v)) return v;

      // legacy string support
      if (typeof v === 'string' && v.length > 0) {
        return v.split('\n');
      }

      // default
      return [''];
    };

    const addPage3Row = (tableIdx) => {
      setTables((prev) => {
        const next = prev.map((t) => ({ ...t, Items: [...t.Items] }));
        const table = next[tableIdx];

        table.Items = table.Items.map((item) => {
          if (item.page_no !== 3 || item.is_table !== true) return item;

          const rows = normalizeToArray(item.value);
          return {
            ...item,
            value: [...rows, ''], // add empty row
            is_user_modified: true,
          };
        });

        return next;
      });
    };

    const deletePage3Row = (tableIdx) => {
      setTables((prev) => {
        const next = prev.map((t) => ({ ...t, Items: [...t.Items] }));
        const table = next[tableIdx];

        table.Items = table.Items.map((item) => {
          if (item.page_no !== 3 || item.is_table !== true) return item;

          const rows = normalizeToArray(item.value);

          // 🚫 keep at least one row
          if (rows.length <= 1) return item;

          return {
            ...item,
            value: rows.slice(0, -1), // ✅ remove last row
            is_user_modified: true,
          };
        });

        return next;
      });

      // realtime confidence update
      onConfidenceChange?.();
    };

    // useEffect(() => {
    //   idb_get('tables').then((saved) => {
    //     if (saved && Array.isArray(saved)) {
    //       setTables(saved);
    //     }
    //   });
    // }, []);
    useEffect(() => {
      let cancelled = false;

      const load = async () => {
        // 1️⃣ HARD REFRESH → LOAD FROM INDEXEDDB ONLY
        if (isHardRefresh) {
          const saved = await idb_get('tables');
          if (!cancelled && saved?.length) {
            setTables(saved);
            return;
          }
        }

        // 2️⃣ NAVIGATION / FRESH LOAD → BACKEND IS KING
        if (jsonData?.Tables?.length) {
          setTables(jsonData.Tables);
          await idb_set('tables', jsonData.Tables);
        }
      };

      load();
      return () => {
        cancelled = true;
      };
    }, [jsonData, isHardRefresh]);

    const isEditable = (item) => {
      if (!item) return false;
      const hasValueKey = (item) =>
        item && Object.prototype.hasOwnProperty.call(item, 'value');

      if (!hasValueKey(item)) return false;
      if (item.user_editable !== true) return false;

      // Remark / Verdict → editable only in edit mode
      if (
        item.task_type === 'remark' ||
        item.task_type === 'verdict' ||
        item.task_type === 'verdict_dependency'
      ) {
        return editMode;
      }

      if (!editMode) return false;
      if (item.is_textbox === false) return false;

      return true;
    };

    // Expose methods to parent via ref
    useImperativeHandle(ref, () => ({
      getUpdatedJson: () => ({ Tables: tables }),
      getFieldValue: (fieldName) => {
        for (const table of tables) {
          for (const item of table.Items) {
            if (item.field === fieldName) {
              return item.value ?? '';
            }
          }
        }
        return '';
      },
      setFieldValue: (fieldName, newValue) => {
        setTables((prev) => {
          const next = prev.map((tbl) => ({
            ...tbl,
            Items: tbl.Items.map((item) =>
              item.field === fieldName ? { ...item, value: newValue } : item
            ),
          }));
          return next;
        });
      },
    }));

    // LOAD JSON
    // useEffect(() => {
    //   // When API gives new data (Generate TRF clicked)
    //   if (isRefreshRef.current) return; // on refresh we keep localStorage data
    //   if (jsonData?.Tables) {
    //     setTables(jsonData.Tables);
    //     setVisiblePages(1);
    //     setCurrentPageIndex(0);
    //   }
    // }, [jsonData]);

    // Load from IndexedDB ONLY on hard refresh (mount)
    // useEffect(() => {
    //   const navEntry =
    //     performance.getEntriesByType &&
    //     performance.getEntriesByType('navigation') &&
    //     performance.getEntriesByType('navigation')[0];

    //   const isRefresh =
    //     (performance.navigation && performance.navigation.type === 1) ||
    //     navEntry?.type === 'reload' ||
    //     false;

    //   isRefreshRef.current = !!isRefresh;

    //   if (isRefreshRef.current) {
    //     idb_get('tables').then((saved) => {
    //       if (saved) {
    //         setTables(saved);
    //         setVisiblePages(1);
    //         setCurrentPageIndex(0);
    //       }
    //     });
    //   }
    // }, []);

    // Save to IndexedDB whenever tables change
    useEffect(() => {
      if (tables && tables.length > 0) {
        idb_set('tables', tables);
      }
    }, [tables]);

    // useEffect(() => {
    //   if (!jsonData?.Tables) return;

    //   setTables((prev) => {
    //     // Avoid unnecessary reset if data is identical
    //     if (JSON.stringify(prev) === JSON.stringify(jsonData.Tables)) {
    //       return prev;
    //     }
    //     return jsonData.Tables;
    //   });

    //   setVisiblePages(1);
    //   setCurrentPageIndex(0);
    // }, [jsonData]);

    useEffect(() => {
      if (!jsonData?.Tables) return;

      setTables((prev) => {
        // If no previous data → first load
        if (!prev || prev.length === 0) {
          return jsonData.Tables;
        }

        // Merge incoming tables WITHOUT overwriting user edits
        return jsonData.Tables.map((newTable) => {
          const oldTable = prev.find((t) => t.Table === newTable.Table);
          if (!oldTable) return newTable;

          return {
            ...newTable,
            Items: newTable.Items.map((newItem) => {
              const oldItem = oldTable.Items.find(
                (i) =>
                  i.field === newItem.field &&
                  i.question_row === newItem.question_row &&
                  i.answer_row === newItem.answer_row &&
                  i.task_type === newItem.task_type
              );

              //  Preserve user edits
              if (
                oldItem?.is_user_modified &&
                oldItem.task_type === newItem.task_type
              ) {
                return oldItem;
              }

              return oldItem
                ? {
                    ...newItem,
                    value: oldItem.value,
                    is_user_modified: oldItem.is_user_modified,
                    is_user_edited: oldItem.is_user_edited,
                    user_comments: oldItem.user_comments,
                    confidence: oldItem.confidence,
                  }
                : newItem;
            }),
          };
        });
      });
    }, [jsonData]);

    // useEffect(() => {
    //   if (!jsonData?.Tables) return;
    //   //console.log('hhh', jsonData);
    //   // If IndexedDB already loaded (refresh), NEVER override it
    //   if (isRefreshRef.current) return;

    //   // Only initial load from backend
    //   setTables(jsonData.Tables);
    //   setVisiblePages(1);
    //   setCurrentPageIndex(0);
    // }, [jsonData]);

    // Load from IndexedDB ONLY on hard refresh (mount)
    // useEffect(() => {
    //   const navEntry =
    //     performance.getEntriesByType &&
    //     performance.getEntriesByType('navigation') &&
    //     performance.getEntriesByType('navigation')[0];

    //   const isRefresh =
    //     (performance.navigation && performance.navigation.type === 1) ||
    //     navEntry?.type === 'reload' ||
    //     false;

    //   isRefreshRef.current = !!isRefresh;

    //   if (isRefreshRef.current) {
    //     idb_get('tables', 'trf').then((saved) => {
    //       if (saved) {
    //         setTables(saved);
    //         setVisiblePages(1);
    //         setCurrentPageIndex(0);
    //       }
    //     });
    //   }
    // }, []);

    // Save to IndexedDB whenever tables change
    // useEffect(() => {
    //   if (tables && tables.length > 0) {
    //     idb_set('tables', tables);
    //   }
    // }, [tables]);

    // FLATTEN ITEMS (hide disable_text: true in UI)
    const allItems = useMemo(() => {
      const arr = [];
      (tables || []).forEach((table, tIdx) => {
        (table.Items || []).forEach((item, realIndex) => {
          if (item.disable_text === true) return;

          arr.push({
            ...item,
            __t: tIdx,
            __i: realIndex, // ← REAL INDEX FIXES THE PROBLEM
          });
        });
      });
      return arr;
    }, [tables]);

    // GROUP BY PAGE NUMBER
    const { pageNos, pageMap } = useMemo(() => {
      const map = {};
      allItems.forEach((item) => {
        let p = item.page_no ?? item.page_number ?? 1;
        p = Number(p);
        if (isNaN(p) || p <= 0) p = 1;
        if (!map[p]) map[p] = [];
        map[p].push(item);
      });

      return {
        pageNos: Object.keys(map)
          .map(Number)
          .sort((a, b) => a - b),
        pageMap: map,
      };
    }, [allItems]);

    const totalPages = pageNos.length;
    const visiblePageNos = pageNos.slice(0, visiblePages);
    const safeIndex =
      totalPages === 0
        ? 0
        : Math.min(Math.max(currentPageIndex, 0), totalPages - 1);

    // INFINITE SCROLL
    useEffect(() => {
      const sentinel = sentinelRef.current;
      const root = containerRef.current;
      if (!sentinel || !root || totalPages === 0) return;

      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting && visiblePages < totalPages) {
            setLoading(true);
            setTimeout(() => {
              setVisiblePages((v) => Math.min(v + 1, totalPages));
              setLoading(false);
            }, 200);
          }
        },
        { root, threshold: 0.2 }
      );

      observer.observe(sentinel);
      return () => observer.disconnect();
    }, [visiblePages, totalPages]);

    // SCROLL → ACTIVE PAGE
    useEffect(() => {
      const el = containerRef.current;
      if (!el || visiblePageNos.length === 0) return;

      const onScroll = () => {
        let active = safeIndex;
        const top = el.scrollTop;
        const offset = 150;

        visiblePageNos.forEach((p, idx) => {
          const ref = pageRefs.current[p];
          if (ref && top + offset >= ref.offsetTop) active = idx;
        });

        if (active !== safeIndex) setCurrentPageIndex(active);
      };

      el.addEventListener('scroll', onScroll, { passive: true });
      return () => el.removeEventListener('scroll', onScroll);
    }, [visiblePageNos, safeIndex]);

    // PAGINATION
    const handlePageChange = (e, pageIndex1Based) => {
      const idx = pageIndex1Based - 1;
      if (idx < 0 || idx >= totalPages) return;

      const targetPageNo = pageNos[idx];
      if (!visiblePageNos.includes(targetPageNo)) setVisiblePages(idx + 1);
      setCurrentPageIndex(idx);

      setTimeout(() => {
        const ref = pageRefs.current[targetPageNo];
        if (ref && containerRef.current)
          containerRef.current.scrollTo({
            top: ref.offsetTop,
            behavior: 'smooth',
          });
      }, 80);
    };

    // UPDATE CELL VALUE
    const updateCell = (t, i, val) => {
      setTables((prev) => {
        const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
        const item = next[t].Items[i];

        // 🔹 only mark modified if value ACTUALLY changed
        const isModified = item.value !== val;
        if (!isModified) return prev;

        next[t].Items[i] = {
          ...item,
          value: val,
          is_user_modified: true,
          is_user_edited: true,
        };

        return next;
      });

      // trigger realtime confidence update
      onConfidenceChange?.();
    };

    // COMMENT HANDLING
    const openComment = (t, i) => {
      commentTargetRef.current = { t, i };
      const item = tables?.[t]?.Items?.[i];

      // ✅ get ALL existing comments
      const history = Array.isArray(item?.user_comments)
        ? item.user_comments
        : [];

      // ✅ pick latest comment (if exists)
      const latestComment =
        history.length > 0 ? history[history.length - 1].comment : '';

      setCommentHistory(history); // show full history
      setCurrentCommentText(latestComment); // empty input
      setIsCommentOpen(true);
    };

    // const handleApprove = (tIdx, iIdx) => {
    //   setTables((prev) => {
    //     const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
    //     const item = next[tIdx].Items[iIdx];
    //     console.log('tem', item);

    //     // Prevent double approve
    //     if (item.is_user_approved) return prev;

    //     const c = Number(item.confidence);

    //     // User edited + approve → User Edited
    //     if (item.is_user_modified === true) {
    //       next[tIdx].Items[iIdx] = {
    //         ...item,
    //         is_user_approved: true,
    //         is_user_edited: true,
    //         confidence: 100, // safe
    //       };
    //       return next;
    //     }

    //     // Medium / Low + approve → Promote to HIGH
    //     if (!Number.isNaN(c) && c < 75) {
    //       next[tIdx].Items[iIdx] = {
    //         ...item,
    //         is_user_approved: true,
    //         confidence: 100,
    //       };
    //       return next;
    //     }

    //     // Already high + approve → no change
    //     return prev;
    //   });
    //   console.log('entered');

    //   // trigger realtime confidence recalculation

    //   //window.dispatchEvent(new Event('idb-updated'));
    //   setTimeout(() => {
    //     onConfidenceChange?.();
    //   }, 0);
    // };

    const handleApprove = async (tIdx, iIdx) => {
      let updatedTables = null;

      setTables((prev) => {
        const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
        const item = next[tIdx].Items[iIdx];

        if (!item || item.is_user_approved) return prev;

        //  If medium / low → promote to HIGH
        const shouldPromote =
          item.accuracy_level === true && Number(item.confidence) < 100;

        next[tIdx].Items[iIdx] = {
          ...item,
          is_user_approved: true,
          confidence: shouldPromote ? 100 : item.confidence, // do NOT touch user_edited
        };

        // 🔥 Clause row promotion (page 9+)
        if (
          item.task_type === 'remark' ||
          item.task_type === 'verdict' ||
          item.task_type === 'verdict_dependency'
        ) {
          const clauseRow = item.clause_row;
          const questionRow = item.question_row;

          next[tIdx].Items = next[tIdx].Items.map((row) => {
            if (
              row.task_type == null &&
              row.clause_row === clauseRow &&
              row.question_row === questionRow
            ) {
              return {
                ...row,
                confidence: 100, // promote clause too
              };
            }
            return row;
          });
        }

        updatedTables = next;
        return next;
      });

      // 🔥 THIS IS THE CRITICAL PART
      if (updatedTables) {
        await idb_set('tables', updatedTables); // <-- update IndexedDB immediately
      }

      // 🔥 Now confidence score recalculates correctly
      onConfidenceChange?.();
    };

    const getLoggedInUser = () => {
      try {
        const user = localStorage.getItem('name');
        return user || 'Unknown User';
      } catch {
        return 'Unknown User';
      }
    };

    const saveComment = () => {
      const { t, i } = commentTargetRef.current;
      if (t == null || i == null || !currentCommentText.trim()) return;

      const loggedInUser = getLoggedInUser();

      setTables((prev) => {
        const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
        const item = next[t].Items[i];

        const prevComments = Array.isArray(item.user_comments)
          ? item.user_comments
          : [];

        next[t].Items[i] = {
          ...item,
          user_comments: [
            ...prevComments,
            {
              comment: currentCommentText.trim(),
              Submited_at: new Date().toISOString(),
              Submited_By: loggedInUser,
              Deleted: null,
            },
          ],
        };

        return next;
      });

      setCurrentCommentText('');
      setIsCommentOpen(false);
    };

    if (totalPages === 0) return <Typography>No Data</Typography>;

    // HOVER ACTIONS: only show when editMode=true AND item editable AND hovered
    const renderHoverActions = (tIdx, iIdx, userEditable) => {
      if (!userEditable) return null;
      if (tIdx == null || iIdx == null) return null;
      if (hovered.t !== tIdx || hovered.i !== iIdx) return null;

      const item = tables?.[tIdx]?.Items?.[iIdx];
      if (!item || item.user_editable !== true) return null;

      const hasValueField = Object.prototype.hasOwnProperty.call(item, 'value');
      if (!hasValueField) return null;

      const isTbdNotAvailable =
        typeof item.value === 'string' &&
        item.value.trim().toLowerCase() === 'tbd-info not available';

      const canApprove =
        item.ai_fillable === true && item.accuracy_level === true;

      return (
        <div className="dt-hover-actions">
          {/* ✅ APPROVE — only when AI confidence exists */}
          {canApprove && (
            <IconButton size="small" onClick={() => handleApprove(tIdx, iIdx)}>
              <CheckCircleIcon className="dt-icon-approve" />
            </IconButton>
          )}

          {/* ✅ COMMENT — always allowed */}
          <IconButton size="small" onClick={() => openComment(tIdx, iIdx)}>
            <ChatBubbleOutlineOutlinedIcon className="dt-icon-comment" />
          </IconButton>

          {/* 🚫 BOOKMARK hidden only for "TBD-Info not available" */}
          {!isTbdNotAvailable && (
            <IconButton
              size="small"
              onClick={() => {
                const row = tables?.[tIdx]?.Items?.[iIdx] ?? {
                  __t: tIdx,
                  __i: iIdx,
                };
                onBookmarkClick?.(row);
              }}
            >
              <MenuBookOutlinedIcon className="dt-icon-bookmark" />
            </IconButton>
          )}
        </div>
      );
    };

    // TABLE MODE (is_table: true) - grouped table rendering
    const renderTableGroupsForPage = (pageItems, pageNo) => {
      const tableItems = pageItems.filter(
        (it) => it.is_table === true && it.disable_text !== true
      );
      if (tableItems.length === 0) return null;

      // group by original table __t
      const groupsByTable = {};
      tableItems.forEach((item) => {
        const key = item.__t ?? 0;
        if (!groupsByTable[key]) groupsByTable[key] = [];
        groupsByTable[key].push(item);
      });

      // helper: get column index with PAGE 7 answer_column → UI_answer_column logic
      const getColumnIndex = (item) => {
        let ansCol = item.answer_column;
        if (
          pageNo === 7 &&
          (ansCol === 0 || ansCol === '0') &&
          item.UI_answer_column != null
        ) {
          ansCol = item.UI_answer_column;
        }
        const raw =
          item.rendering_column ?? item.question_column ?? ansCol ?? 0;
        const num = Number(raw);
        return Number.isNaN(num) ? 0 : num;
      };

      const tableGroups = Object.values(groupsByTable).sort((a, b) => {
        const aMin = Math.min(
          ...a.map((it) =>
            typeof it.question_row === 'number' ? it.question_row : 0
          )
        );
        const bMin = Math.min(
          ...b.map((it) =>
            typeof it.question_row === 'number' ? it.question_row : 0
          )
        );
        return aMin - bMin;
      });

      return tableGroups.map((group, gIdx) => {
        const rowsByQR = {};
        group.forEach((it) => {
          const qr = typeof it.question_row === 'number' ? it.question_row : 0;
          if (!rowsByQR[qr]) rowsByQR[qr] = [];
          rowsByQR[qr].push(it);
        });

        const rowKeys = Object.keys(rowsByQR)
          .map(Number)
          .sort((a, b) => a - b);

        const maxColumns = Math.max(
          ...Object.values(rowsByQR).map((rows) => rows.length)
        );

        const canEditPage3 = pageNo === 3 && editMode === true;

        return (
          <TableContainer
            component={Paper}
            className="dt-table-container"
            key={gIdx}
          >
            <Table size="small" className="dt-table">
              <TableBody>
                {rowKeys.map((qr) => {
                  const rowItems = rowsByQR[qr]
                    .slice()
                    .sort((a, b) => getColumnIndex(a) - getColumnIndex(b));

                  // SINGLE ROW (or explicit single_row)
                  if (
                    rowItems.length === 1 ||
                    rowItems[0].single_row === true
                  ) {
                    const col = rowItems[0];
                    const tIdx = col.__t;
                    const iIdx = col.__i;
                    const editable = isEditable(col);
                    const isPage7 = pageNo === 7;
                    const isCheckboxUI =
                      isPage7 && col.checkbox_answer_UI === true;
                    const isPage7CheckboxUI =
                      pageNo === 7 &&
                      col.take_value_UI === true &&
                      col.checkbox_value !== undefined;

                    const value = col.value ?? col.Value ?? '';
                    const label = col.field ?? col.Field ?? '';
                    const rows = col.rendering_row ? col.rendering_row : 1;
                    //  PAGE 4 SPECIAL: Summary of testing → textbox
                    if (
                      pageNo === 4 &&
                      col.single_row === true &&
                      col.user_editable === true
                    ) {
                      return (
                        <TableRow key={qr}>
                          <TableCell
                            colSpan={maxColumns}
                            className="dt-single-row-cell"
                          >
                            <div className="dt-value-column dt-relative">
                              {/* LABEL */}
                              <Typography
                                sx={{
                                  fontSize: 14,
                                  whiteSpace: 'pre-wrap',
                                  fontWeight: col.is_bold === true ? 700 : 400,
                                  mb: 1,
                                }}
                              >
                                {label}
                              </Typography>

                              {/* TEXTBOX */}
                              <textarea
                                className="dt-textarea dt-textarea-with-actions"
                                value={value ?? ''}
                                rows={col.rendering_row || 2}
                                disabled={!editMode}
                                onChange={(e) =>
                                  editMode &&
                                  updateCell(tIdx, iIdx, e.target.value)
                                }
                              />

                              {renderHoverActions(
                                tIdx,
                                iIdx,
                                col.user_editable === true
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    }

                    return (
                      <TableRow key={qr}>
                        <TableCell
                          colSpan={maxColumns}
                          className="dt-single-row-cell"
                        >
                          <div
                            className="dt-value-column dt-relative"
                            onMouseEnter={() =>
                              setHovered({ t: tIdx, i: iIdx })
                            }
                            onMouseLeave={() =>
                              setHovered({ t: null, i: null })
                            }
                          >
                            {renderHoverActions(tIdx, iIdx, true)}

                            {/* ================= SINGLE ROW ================= */}
                            {isPage7CheckboxUI ? (
                              <div
                                style={{
                                  display: 'flex',
                                  alignItems: 'flex-start',
                                  gap: 24,
                                }}
                              >
                                {/* LEFT COLUMN — FIELD TEXT (NO CHECKBOX) */}
                                <div style={{ flex: 1 }}>
                                  <Typography
                                    sx={{
                                      fontSize: 14,
                                      whiteSpace: 'pre-wrap',
                                    }}
                                  >
                                    {label}
                                  </Typography>
                                </div>

                                {/* RIGHT COLUMN — CHECKBOX OPTIONS FROM VALUE */}
                                <div style={{ flex: 1 }}>
                                  {(() => {
                                    const checkboxIndexes = JSON.parse(
                                      col.checkbox_index || '[]'
                                    );

                                    // extract options safely
                                    const options = (value || '')
                                      .split('\n')
                                      .map((v) => v.replace(/\s+/g, ' ').trim()) // normalize junk chars
                                      .filter((v) => v.includes('[*]')); // ✅ DO NOT use startsWith

                                    return options.map((opt, idx) => {
                                      const cleanText = opt
                                        .replace('[*]', '')
                                        .trim();
                                      const checkboxKey = `checkbox_value_${checkboxIndexes[idx]}`;
                                      const checked = !!col[checkboxKey];

                                      return (
                                        <div
                                          key={idx}
                                          style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 6,
                                            marginBottom: 6,
                                          }}
                                        >
                                          <Checkbox
                                            size="small"
                                            checked={checked}
                                            disabled={!editMode}
                                            onChange={() => {
                                              setTables((prev) => {
                                                const next = prev.map(
                                                  (tbl) => ({
                                                    ...tbl,
                                                    Items: [...tbl.Items],
                                                  })
                                                );

                                                const current =
                                                  next[tIdx].Items[iIdx];
                                                next[tIdx].Items[iIdx] = {
                                                  ...current,
                                                  [checkboxKey]: !checked,
                                                };

                                                return next;
                                              });
                                            }}
                                          />

                                          <Typography sx={{ fontSize: 14 }}>
                                            {cleanText}
                                          </Typography>
                                        </div>
                                      );
                                    });
                                  })()}
                                </div>
                              </div>
                            ) : (
                              /* fallback for other pages */

                              <Typography
                                sx={{
                                  fontSize: 14,
                                  whiteSpace: 'pre-wrap',
                                  fontWeight: col.is_bold === true ? 700 : 400,
                                  marginBottom: 8,
                                }}
                              >
                                {label}
                              </Typography>
                            )}

                            {renderHoverActions(
                              tIdx,
                              iIdx,
                              col.user_editable === true
                            )}

                            {col.user_comments?.[0]?.comment && (
                              <Typography
                                variant="caption"
                                className="dt-comment-caption"
                              >
                                💬 {col.user_comments[0].comment}
                              </Typography>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  }

                  // MULTI-COLUMN ROW
                  return (
                    <React.Fragment key={qr}>
                      {/* Header row */}
                      <TableRow>
                        {rowItems.map((col, idx) => (
                          <TableCell key={idx} className="dt-thead-cell">
                            {col.field ?? col.Field ?? ''}
                          </TableCell>
                        ))}
                      </TableRow>

                      {/* Value row */}
                      {pageNo === 3 ? (
                        (() => {
                          const splitLines = (v) =>
                            typeof v === 'string' && v.length > 0
                              ? v.split('\n')
                              : [''];

                          const rowCount = Math.max(
                            ...rowItems.map(
                              (c) => normalizeToArray(c.value).length
                            )
                          );

                          return Array.from({ length: rowCount }).map(
                            (_, rowIdx) => (
                              <TableRow key={`p3-row-${rowIdx}`}>
                                {rowItems.map((col, idx) => {
                                  const tIdx = col.__t;
                                  const iIdx = col.__i;
                                  const editable = isEditable(col);

                                  const lines = normalizeToArray(col.value);
                                  const cellValue = lines[rowIdx] ?? '';

                                  return (
                                    <TableCell key={idx}>
                                      <div className="dt-value-column dt-relative">
                                        {!editable ? (
                                          <Typography>{cellValue}</Typography>
                                        ) : (
                                          <textarea
                                            className="dt-textarea dt-textarea-with-actions"
                                            value={cellValue}
                                            rows={1}
                                            onChange={(e) => {
                                              const updated = [...lines];
                                              updated[rowIdx] = e.target.value;

                                              setTables((prev) => {
                                                const next = prev.map((t) => ({
                                                  ...t,
                                                  Items: [...t.Items],
                                                }));

                                                next[tIdx].Items[iIdx] = {
                                                  ...next[tIdx].Items[iIdx],
                                                  value: updated, //  KEEP ARRAY
                                                  is_user_modified: true,
                                                  is_user_edited: true,
                                                };

                                                return next;
                                              });

                                              onConfidenceChange?.();
                                            }}
                                          />
                                        )}
                                      </div>
                                    </TableCell>
                                  );
                                })}
                              </TableRow>
                            )
                          );
                        })()
                      ) : (
                        /* ALL OTHER PAGES — ORIGINAL BEHAVIOUR (UNCHANGED) */
                        <TableRow>
                          {rowItems.map((col, idx) => {
                            const tIdx = col.__t;
                            const iIdx = col.__i;
                            const editable = isEditable(col);
                            const isPage7 = pageNo === 7;
                            const isCheckboxUI =
                              isPage7 && col.checkbox_answer_UI === true;
                            const value = col.value ?? col.Value ?? '';
                            const rows = col.rendering_row
                              ? col.rendering_row
                              : 1;

                            return (
                              <TableCell key={idx}>
                                <div
                                  className="dt-value-column dt-relative"
                                  onMouseEnter={() =>
                                    setHovered({ t: tIdx, i: iIdx })
                                  }
                                  onMouseLeave={() =>
                                    setHovered({ t: null, i: null })
                                  }
                                >
                                  {isCheckboxUI ? (
                                    <Typography>{value}</Typography>
                                  ) : col.user_editable !== true ? (
                                    <Typography>{value}</Typography>
                                  ) : (
                                    <div style={{ display: 'flex' }}>
                                      <textarea
                                        className="dt-textarea dt-textarea-with-actions"
                                        value={value}
                                        rows={rows}
                                        disabled={!editable}
                                        onChange={(e) =>
                                          editable &&
                                          updateCell(tIdx, iIdx, e.target.value)
                                        }
                                      />
                                      {renderConfidenceColor(
                                        col.confidence,
                                        col.is_user_edited,
                                        col.ai_fillable,
                                        col.accuracy_level
                                      )}
                                    </div>
                                  )}

                                  {renderHoverActions(
                                    tIdx,
                                    iIdx,
                                    col.user_editable === true
                                  )}

                                  {col._comment && (
                                    <Typography
                                      variant="caption"
                                      className="dt-comment-caption"
                                    >
                                      💬 {col._comment}
                                    </Typography>
                                  )}
                                </div>
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                })}
              </TableBody>
            </Table>
            {pageNo === 3 && (
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'flex-end',
                  gap: 1,
                  p: 1,
                }}
              >
                {canEditPage3 && (
                  <button
                    className="dt-add-row-btn"
                    onClick={() => addPage3Row(group[0].__t)}
                  >
                    ➕ Add Row
                  </button>
                )}
                {canEditPage3 && (
                  <button
                    className="dt-delete-row-btn"
                    onClick={() => deletePage3Row(group[0].__t)}
                  >
                    ➖ Delete Row
                  </button>
                )}
              </Box>
            )}

            <Divider className="dt-divider" />
          </TableContainer>
        );
      });
    };
    // NORMAL (NON-TABLE) ITEMS - for pages outside 9–42
    const renderNormalItems = (normalItems, pageNo) => {
      if (normalItems.length === 0) return null;

      let groupedNormal = {};

      if (pageNo === 5) {
        return (
          <RenderPage5DynamicGroups
            items={normalItems}
            setTables={setTables}
            isEditable={isEditable}
            updateCell={updateCell}
            editMode={editMode}
          />
        );
      }

      if (pageNo === 6) {
        return normalItems.map((item, idx) => {
          const hasImages =
            Array.isArray(item.marking_urls) && item.marking_urls.length > 0;
          return (
            <Box key={idx} sx={{ mb: 3 }}>
              <Typography
                style={{
                  fontSize: 14,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontWeight: item.is_bold === true ? 700 : 400,
                  mb: 1,
                }}
              >
                {item.field}
              </Typography>

              {hasImages && (
                <RenderPage6Images
                  item={item}
                  tIdx={item.__t}
                  iIdx={item.__i}
                  editMode={editMode && item.user_editable === true}
                  setTables={setTables}
                />
              )}
            </Box>
          );
        });
      }

      // PAGE 2 special: group by question_row
      if (pageNo === 2) {
        normalItems.forEach((item) => {
          if (item.disable_text === true) return;
          const qr =
            typeof item.question_row === 'number' ? item.question_row : 0;
          if (!groupedNormal[qr]) groupedNormal[qr] = [];
          groupedNormal[qr].push(item);
        });
      } else {
        // Default: group by field name
        normalItems.forEach((item) => {
          if (item.disable_text === true) return;
          const field = item.field ?? item.Field ?? '';
          if (!groupedNormal[field]) groupedNormal[field] = [];
          groupedNormal[field].push(item);
        });
      }

      return (
        <TableContainer component={Paper} className="dt-table-container">
          <Table size="small" className="dt-table">
            <TableBody>
              {Object.entries(groupedNormal).map(
                ([groupKey, rowsArr], idx1) => {
                  const first = rowsArr[0];

                  const fieldLabel =
                    pageNo === 2
                      ? (first.field ?? first.Field ?? '')
                      : groupKey;

                  // SINGLE ROW
                  if (first.single_row === true) {
                    const tIdx = first.__t;
                    const iIdx = first.__i;

                    const editable = isEditable(first);
                    const isPage7 = pageNo === 7;
                    const value =
                      first.value ??
                      first.Value ??
                      first.field ??
                      first.Field ??
                      '';
                    const rows = first.rendering_row ? first.rendering_row : 1;
                    //  PAGE 8: remove duplicated field text from value
                    let cleanValue = value;

                    if (
                      pageNo === 8 &&
                      typeof value === 'string' &&
                      typeof fieldLabel === 'string' &&
                      value.startsWith(fieldLabel)
                    ) {
                      cleanValue = value.replace(fieldLabel, '').trim();
                    }

                    return (
                      <TableRow key={idx1}>
                        <TableCell colSpan={2} className="dt-single-row-cell">
                          <div
                            className="dt-value-column dt-relative"
                            onMouseEnter={() =>
                              setHovered({ t: tIdx, i: iIdx })
                            }
                            onMouseLeave={() =>
                              setHovered({ t: null, i: null })
                            }
                          >
                            {pageNo === 5 &&
                            first.checkbox_value !== undefined &&
                            ((first.field || '').includes('[*]') ||
                              (first.value || '').includes('[*]')) ? (
                              renderFieldWithCheckboxAndNewLines(
                                first,
                                tIdx,
                                iIdx,
                                setTables,
                                editMode
                              )
                            ) : pageNo === 7 && first.new_logic_1 === true ? (
                              <div>
                                {/* FIELD */}
                                <Typography
                                  style={{
                                    fontSize: 14,
                                    mb: 1,
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    fontWeight:
                                      first.is_bold === true ? 700 : 500,
                                  }}
                                >
                                  {fieldLabel}
                                </Typography>

                                {/* VALUE — render ALL text, replace [*] with checkbox */}
                                {(first.value || '')
                                  .split('\n')
                                  .map((line, lineIdx) => {
                                    // line contains checkbox markers
                                    if (line.includes('[*]')) {
                                      const checkboxIndexes = JSON.parse(
                                        first.checkbox_index || '[]'
                                      );
                                      let cbCounter = 0;
                                      const parts = line.split(/(\[\*\])/g);

                                      return (
                                        <Typography
                                          key={lineIdx}
                                          sx={{
                                            fontSize: 14,
                                            whiteSpace: 'pre-wrap',
                                            mb: 1,
                                          }}
                                        >
                                          {parts.map((part, idx) => {
                                            if (part === '[*]') {
                                              const checkboxKey = `checkbox_value_${checkboxIndexes[cbCounter]}`;
                                              const checked =
                                                !!first[checkboxKey];
                                              cbCounter += 1;

                                              return (
                                                <Checkbox
                                                  key={`cb-${idx}`}
                                                  size="small"
                                                  checked={checked}
                                                  disabled={!editMode}
                                                  sx={{ padding: '0 4px' }}
                                                  onChange={() => {
                                                    setTables((prev) => {
                                                      const next = prev.map(
                                                        (tbl) => ({
                                                          ...tbl,
                                                          Items: [...tbl.Items],
                                                        })
                                                      );

                                                      next[tIdx].Items[iIdx] = {
                                                        ...next[tIdx].Items[
                                                          iIdx
                                                        ],
                                                        [checkboxKey]: !checked,
                                                      };

                                                      return next;
                                                    });
                                                  }}
                                                />
                                              );
                                            }

                                            return (
                                              <Typography
                                                key={`txt-${idx}`}
                                                component="span"
                                                sx={{ fontSize: 14 }}
                                              >
                                                {part}
                                              </Typography>
                                            );
                                          })}
                                        </Typography>
                                      );
                                    }

                                    // normal text line
                                    return (
                                      <Typography
                                        key={lineIdx}
                                        sx={{
                                          fontSize: 14,
                                          whiteSpace: 'pre-wrap',
                                          mb: 1,
                                        }}
                                      >
                                        {line}
                                      </Typography>
                                    );
                                  })}
                              </div>
                            ) : pageNo === 7 &&
                              first.checkbox_value !== undefined &&
                              first.take_value_UI !== true &&
                              (first.value || '').includes('[*]') ? (
                              <Typography
                                sx={{ fontSize: 14, whiteSpace: 'pre-wrap' }}
                              >
                                {(() => {
                                  const checkboxIndexes = JSON.parse(
                                    first.checkbox_index || '[]'
                                  );
                                  let cbCounter = 0;

                                  const parts = (first.value || '').split(
                                    /(\[\*\])/g
                                  );

                                  return parts.map((part, idx) => {
                                    if (part === '[*]') {
                                      const checkboxKey = `checkbox_value_${checkboxIndexes[cbCounter]}`;
                                      const checked = !!first[checkboxKey];
                                      cbCounter += 1;

                                      return (
                                        <Checkbox
                                          key={`cb-${idx}`}
                                          size="small"
                                          checked={checked}
                                          disabled={!editMode}
                                          sx={{ padding: '0 4px' }}
                                          onChange={() => {
                                            setTables((prev) => {
                                              const next = prev.map((tbl) => ({
                                                ...tbl,
                                                Items: [...tbl.Items],
                                              }));

                                              next[tIdx].Items[iIdx] = {
                                                ...next[tIdx].Items[iIdx],
                                                [checkboxKey]: !checked,
                                              };

                                              return next;
                                            });
                                          }}
                                        />
                                      );
                                    }

                                    return (
                                      <Typography
                                        key={`txt-${idx}`}
                                        component="span"
                                        sx={{ fontSize: 14 }}
                                      >
                                        {part}
                                      </Typography>
                                    );
                                  });
                                })()}
                              </Typography>
                            ) : pageNo === 7 && first.take_value_UI === true ? (
                              <div
                                style={{
                                  display: 'flex',
                                  gap: 24,
                                  alignItems: 'flex-start',
                                }}
                              >
                                {/* LEFT: FIELD TEXT */}
                                <div style={{ flex: 1 }}>
                                  <Typography
                                    style={{
                                      fontSize: 14,
                                      whiteSpace: 'pre-wrap',
                                      wordBreak: 'break-word',
                                    }}
                                  >
                                    {fieldLabel}
                                  </Typography>
                                </div>

                                {/* RIGHT: CHECKBOX VALUES */}
                                <div style={{ flex: 1 }}>
                                  {(() => {
                                    const checkboxIndexes = JSON.parse(
                                      first.checkbox_index || '[]'
                                    );

                                    const options = (first.value || '')
                                      .split('\n')
                                      .map((v) => v.trim())
                                      .filter((v) => v.includes('[*]'));

                                    return options.map((opt, idx) => {
                                      const cleanText = opt
                                        .replace('[*]', '')
                                        .trim();
                                      const checkboxKey = `checkbox_value_${checkboxIndexes[idx]}`;
                                      const checked = !!first[checkboxKey];

                                      return (
                                        <div
                                          key={idx}
                                          style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 6,
                                            marginBottom: 6,
                                          }}
                                        >
                                          <Checkbox
                                            size="small"
                                            checked={checked}
                                            disabled={!editMode}
                                            onChange={() => {
                                              setTables((prev) => {
                                                const next = prev.map(
                                                  (tbl) => ({
                                                    ...tbl,
                                                    Items: [...tbl.Items],
                                                  })
                                                );
                                                next[tIdx].Items[iIdx] = {
                                                  ...next[tIdx].Items[iIdx],
                                                  [checkboxKey]: !checked,
                                                };
                                                return next;
                                              });
                                            }}
                                          />
                                          <Typography sx={{ fontSize: 14 }}>
                                            {cleanText}
                                          </Typography>
                                        </div>
                                      );
                                    });
                                  })()}
                                </div>
                              </div>
                            ) : pageNo === 8 ? (
                              /* ===== PAGE 8 ONLY : FIELD + TEXTAREA ===== */

                              <div>
                                {/* FIELD */}
                                <Typography
                                  style={{
                                    fontSize: 14,
                                    fontWeight: 500,
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    mb: 1,
                                  }}
                                >
                                  {fieldLabel}
                                </Typography>

                                {/* VALUE */}
                                {!editable ? (
                                  <Typography
                                    sx={{
                                      fontSize: 14,
                                      whiteSpace: 'pre-wrap',
                                      wordBreak: 'break-word',
                                    }}
                                  >
                                    {cleanValue}
                                  </Typography>
                                ) : (
                                  <div style={{ display: 'flex' }}>
                                    <textarea
                                      className="dt-textarea dt-textarea-with-actions"
                                      value={cleanValue}
                                      rows={rows}
                                      disabled={!editable}
                                      onChange={(e) =>
                                        editable &&
                                        updateCell(
                                          tIdx,
                                          iIdx,
                                          `${fieldLabel}\n${e.target.value}`
                                        )
                                      }
                                    />
                                    {renderConfidenceColor(
                                      first.confidence,
                                      first.is_user_edited,
                                      first.ai_fillable,
                                      first.accuracy_level
                                    )}
                                  </div>
                                )}
                              </div>
                            ) : first.checkbox_value !== undefined ? (
                              // ✅ checkbox rows → NEVER show textarea
                              <Typography>{value}</Typography>
                            ) : !editable ? (
                              <Typography>{value}</Typography>
                            ) : (
                              <div style={{ display: 'flex' }}>
                                <textarea
                                  className="dt-textarea dt-textarea-with-actions"
                                  value={value}
                                  rows={rows}
                                  disabled={!editable}
                                  onChange={(e) =>
                                    editable &&
                                    updateCell(tIdx, iIdx, e.target.value)
                                  }
                                />
                                {renderConfidenceColor(
                                  first.confidence,
                                  first.is_user_edited,
                                  first.ai_fillable,
                                  first.accuracy_level
                                )}
                              </div>
                            )}

                            {renderHoverActions(
                              tIdx,
                              iIdx,
                              first.user_editable === true
                            )}

                            {first._comment && (
                              <Typography
                                variant="caption"
                                className="dt-comment-caption"
                              >
                                💬 {first._comment}
                              </Typography>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  }

                  // MULTI-VALUE ROW
                  return (
                    <TableRow key={idx1}>
                      <TableCell className="dt-field-cell">
                        <div className="dt-field-label">
                          {first.checkbox_index !== undefined
                            ? (() => {
                                const index = Math.floor(
                                  Number(first.checkbox_index)
                                );
                                if (Number.isNaN(index)) return null;
                                const checkboxKey = `checkbox_value_${index}`;
                                const checked = !!first[checkboxKey];

                                return (
                                  <Checkbox
                                    size="small"
                                    checked={checked}
                                    disabled={!editMode}
                                    onChange={() => {
                                      setTables((prev) => {
                                        const next = prev.map((tbl) => ({
                                          ...tbl,
                                          Items: [...tbl.Items],
                                        }));

                                        next[first.__t].Items[first.__i] = {
                                          ...next[first.__t].Items[first.__i],
                                          [checkboxKey]: !checked,
                                        };

                                        return next;
                                      });
                                    }}
                                  />
                                );
                              })()
                            : null}

                          {fieldLabel}
                        </div>
                      </TableCell>

                      <TableCell className="dt-value-cell">
                        <div className="dt-value-row">
                          {rowsArr.map((r, idx2) => {
                            const tIdx = r.__t;
                            const iIdx = r.__i;

                            const editable = isEditable(r);
                            const isPage7 = pageNo === 7;
                            const isCheckboxUI =
                              isPage7 && r.checkbox_answer_UI === true;

                            const value = r.value ?? r.Value ?? '';
                            const rows = r.rendering_row ? r.rendering_row : 1;

                            return (
                              <div
                                key={idx2}
                                className="dt-value-column dt-relative"
                                onMouseEnter={() =>
                                  setHovered({ t: tIdx, i: iIdx })
                                }
                                onMouseLeave={() =>
                                  setHovered({ t: null, i: null })
                                }
                              >
                                {r.checkbox_value !== undefined &&
                                pageNo !== 7 ? (
                                  // ✅ checkbox exists → NEVER show textarea
                                  <Typography>{''}</Typography>
                                ) : isCheckboxUI ? (
                                  <div>
                                    {(value || '')
                                      .split('\n')
                                      .map((opt) => opt.trim())
                                      .filter(Boolean)
                                      .map((opt, idxOpt) => (
                                        <div
                                          key={idxOpt}
                                          style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 4,
                                          }}
                                        >
                                          <Checkbox size="small" />
                                          <Typography variant="body2">
                                            {opt}
                                          </Typography>
                                        </div>
                                      ))}
                                  </div>
                                ) : pageNo === 7 &&
                                  r.take_value_UI ===
                                    true ? null : r.user_editable !== true ? ( // ⛔ block textarea for page 7 checkbox UI
                                  <Typography>{value}</Typography>
                                ) : (
                                  <div
                                    style={{
                                      display: 'flex',
                                    }}
                                  >
                                    <textarea
                                      className="dt-textarea dt-textarea-with-actions"
                                      value={value}
                                      rows={rows}
                                      disabled={!editable}
                                      onChange={(e) =>
                                        editable &&
                                        updateCell(tIdx, iIdx, e.target.value)
                                      }
                                    />

                                    {renderConfidenceColor(
                                      r.confidence,
                                      r.is_user_edited,
                                      r.ai_fillable,
                                      r.accuracy_level
                                    )}
                                  </div>
                                )}

                                {renderHoverActions(
                                  tIdx,
                                  iIdx,
                                  r.user_editable === true
                                )}

                                {r._comment && (
                                  <Typography
                                    variant="caption"
                                    className="dt-comment-caption"
                                  >
                                    💬 {r._comment}
                                  </Typography>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                }
              )}
            </TableBody>
          </Table>

          <Divider className="dt-divider" />
        </TableContainer>
      );
    };
    // PAGE 9 → 42 SPECIAL 4-COLUMN IEC 61010-1 TABLE
    const renderPart10Table = (pageItems) => {
      //const items = pageItems.filter((i) => i.disable_text !== true);

      const HIDE_FIELDS = new Set([
        'Requirement + Test',
        'Result - Remark',
        'Verdict',
        'IEC 61010-1',
      ]);

      const items = pageItems.filter((i) => {
        if (i.disable_text === true) return false;

        //  hide unwanted header-like rows purely by field name
        if (HIDE_FIELDS.has(i.field)) return false;

        return true;
      });

      // Header row (if exists)
      const headerItem = items.find((i) => i.table_head === true);

      // Data rows only
      const dataItems = items.filter((i) => i.table_head !== true);

      // Group rows by clause_row + question_row + field
      const groupsByRow = {};

      dataItems.forEach((item) => {
        const fieldLabel = item.field ?? item.Field ?? '';

        const key = [
          item.clause_row ?? '',
          item.question_row ?? '',
          fieldLabel,
        ].join('|');

        if (!groupsByRow[key]) {
          groupsByRow[key] = {
            clause: item.clause ?? item.clause_number ?? '',
            field: fieldLabel,
            question_row:
              typeof item.question_row === 'number' ? item.question_row : 0,

            remarkItem: null,
            verdictItem: null,

            requirementComment: item._comment ?? null,
          };
        } else if (!groupsByRow[key].requirementComment && item._comment) {
          groupsByRow[key].requirementComment = item._comment;
        }

        if (item.task_type === 'remark') {
          groupsByRow[key].remarkRef = {
            __t: item.__t,
            __i: item.__i,
          };
        } else if (
          item.task_type === 'verdict' ||
          item.task_type === 'verdict_dependency'
        ) {
          groupsByRow[key].verdictRef = {
            __t: item.__t,
            __i: item.__i,
          };
        }
      });

      const finalRows = Object.values(groupsByRow).sort(
        (a, b) => a.question_row - b.question_row
      );

      const bodyCellSx = {
        borderRight: '1px solid #ccc',
        borderBottom: '1px solid #ccc',
        verticalAlign: 'top',
      };

      const headerCellSx = {
        borderRight: '1px solid #aaa',
        borderBottom: '2px solid #000',
        fontWeight: 'bold',
      };

      // Requirement cell (never editable)
      const renderRequirementCell = (fieldLabel, comment) => {
        if (!fieldLabel && !comment) return null;
        return (
          <div className="dt-value-column dt-relative">
            <Typography
              style={{
                fontSize: 14,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {fieldLabel}
            </Typography>

            {comment && (
              <Typography variant="caption" className="dt-comment-caption">
                💬 {comment}
              </Typography>
            )}
          </div>
        );
      };

      // Remark / Verdict Cells
      const renderRemarkOrVerdictCell = (item, tIdx, iIdx) => {
        if (!item) return null;
        if (tIdx == null || iIdx == null) return null;

        // const tIdx = item.__t;
        // const iIdx = item.__i;
        if (iIdx === -1) return null;

        const value = item.value ?? item.Value ?? '';
        const rows = item.rendering_row || 1;
        const comment = item._comment;

        // Not user editable → plain text always
        if (
          item.task_type !== 'remark' &&
          item.task_type !== 'verdict' &&
          item.task_type !== 'verdict_dependency'
        ) {
          return (
            <div className="dt-value-column dt-relative">
              <Typography sx={{ whiteSpace: 'pre-wrap' }}>{value}</Typography>
              {comment && (
                <Typography variant="caption" className="dt-comment-caption">
                  💬 {comment}
                </Typography>
              )}
            </div>
          );
        }

        // else user_editable === true -> show textarea (disabled until editMode and other checks)
        return (
          <div
            className={`dt-value-column dt-relative ${
              item.is_bold === true ? 'bold' : ''
            }`}
            onMouseEnter={() => setHovered({ t: tIdx, i: iIdx })}
            onMouseLeave={() => setHovered({ t: null, i: null })}
          >
            <div style={{ display: 'flex' }}>
              <textarea
                className="dt-textarea dt-textarea-with-actions"
                value={value}
                rows={rows}
                disabled={!editMode}
                style={{ marginRight: '10px' }}
                onChange={(e) => {
                  if (!editMode) return;

                  const newVal = e.target.value;

                  setTables((prevTables) => {
                    const next = prevTables.map((tbl) => ({
                      ...tbl,
                      Items: [...tbl.Items],
                    }));

                    const clauseRow = item.clause_row;
                    const clauseField = item.field ?? item.Field ?? '';

                    // 1update verdict / remark
                    next[tIdx].Items[iIdx] = {
                      ...next[tIdx].Items[iIdx],
                      value: newVal,
                      is_user_modified: true,
                      is_user_edited: true,
                    };

                    // 2bubble to clause row (page 9+)
                    next[tIdx].Items = next[tIdx].Items.map((row) => {
                      const rowField = row.field ?? row.Field ?? '';
                      if (
                        row.task_type == null &&
                        row.clause_row === clauseRow &&
                        rowField === clauseField
                      ) {
                        return {
                          ...row,
                          is_user_modified: true,
                          is_user_edited: true,
                          confidence: 100,
                        };
                      }
                      return row;
                    });

                    return next;
                  });

                  onConfidenceChange?.();
                }}
              />

              {renderConfidenceColor(
                item.confidence,
                item.is_user_edited,
                item.ai_fillable,
                item.accuracy_level
              )}
            </div>

            {renderHoverActions(tIdx, iIdx, true)}

            {comment && (
              <Typography variant="caption" className="dt-comment-caption">
                💬 {comment}
              </Typography>
            )}
          </div>
        );
      };

      return (
        <TableContainer component={Paper} className="dt-table-container">
          {/* Optional table_head header */}
          {headerItem && (
            <div
              style={{
                textAlign: 'center',
                fontWeight: 'bold',
                padding: '8px 0',
                borderBottom: '2px solid #000',
                fontSize: '16px',
              }}
            >
              {headerItem.field ?? headerItem.Field ?? ''}
            </div>
          )}

          <Table
            size="small"
            className="dt-table"
            sx={{ border: '1px solid #ccc', borderCollapse: 'collapse' }}
          >
            <TableHead>
              <TableRow>
                <TableCell className="dt-thead-cell" sx={headerCellSx}>
                  Clause
                </TableCell>
                <TableCell className="dt-thead-cell" sx={headerCellSx}>
                  Requirement + Test
                </TableCell>
                <TableCell className="dt-thead-cell" sx={headerCellSx}>
                  Result – Remark
                </TableCell>
                <TableCell className="dt-thead-cell" sx={headerCellSx}>
                  Verdict
                </TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {finalRows.map((row, idx) => (
                <TableRow key={idx}>
                  <TableCell sx={bodyCellSx}>{row.clause ?? ''}</TableCell>

                  <TableCell sx={bodyCellSx}>
                    {renderRequirementCell(row.field, row.requirementComment)}
                  </TableCell>

                  <TableCell sx={bodyCellSx}>
                    {renderRemarkOrVerdictCell(
                      tables?.[row.remarkRef?.__t]?.Items?.[row.remarkRef?.__i],
                      row.remarkRef?.__t,
                      row.remarkRef?.__i
                    )}
                  </TableCell>

                  <TableCell sx={bodyCellSx}>
                    {renderRemarkOrVerdictCell(
                      tables?.[row.verdictRef?.__t]?.Items?.[
                        row.verdictRef?.__i
                      ],
                      row.verdictRef?.__t,
                      row.verdictRef?.__i
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Divider className="dt-divider" />
        </TableContainer>
      );
    };
    // RENDER FULL UI (final part)
    return (
      <>
        <div className="dt-container" ref={containerRef}>
          <div className="dt-sticky-header"></div>

          {visiblePageNos.map((pageNo) => {
            const pageItems = pageMap[pageNo] || [];

            const tableItems = pageItems.filter(
              (it) =>
                it.is_table === true &&
                it.page_no !== 6 &&
                it.disable_text !== true
            );
            const normalItems = pageItems.filter(
              (it) =>
                (it.is_table !== true || it.page_no === 6) &&
                it.disable_text !== true
            );

            return (
              <div
                className="dt-page"
                key={pageNo}
                ref={(el) => (pageRefs.current[pageNo] = el)}
              >
                {pageNo !== 1 && (
                  <Typography
                    sx={{
                      fontSize: '14px',
                      color: '#8a8a8a',
                      marginBottom: '6px',
                      textAlign: 'right',
                      paddingBottom: '2%',
                      paddingRight: '2%',
                      fontWeight: 600,
                    }}
                  >
                    Page {pageNo} of {pageNos[pageNos.length - 1]}
                  </Typography>
                )}

                {/* Page 9 → 42 special IEC 61010-1 clause table */}
                {pageNo >= 9 && pageNo <= 42 ? (
                  renderPart10Table(pageItems)
                ) : (
                  <>
                    {tableItems.length > 0 &&
                      renderTableGroupsForPage(pageItems, pageNo)}
                    {normalItems.length > 0 &&
                      renderNormalItems(normalItems, pageNo)}
                  </>
                )}

                <Divider className="dt-divider" />
              </div>
            );
          })}

          <div ref={sentinelRef} className="dt-sentinel" />

          <div className="dt-pagination-wrapper">
            <Pagination
              count={totalPages}
              page={safeIndex + 1}
              onChange={handlePageChange}
              color="primary"
              size="small"
            />
          </div>

          {loading && (
            <div className="dt-loading">
              <CircularProgress size={28} />
            </div>
          )}
        </div>

        <CommentDialog
          open={isCommentOpen}
          onClose={() => setIsCommentOpen(false)}
          comments={commentHistory}
          currentComment={currentCommentText}
          setCurrentComment={setCurrentCommentText}
          onSubmit={saveComment}
        />
      </>
    );
  }
);

export default DataTable;
