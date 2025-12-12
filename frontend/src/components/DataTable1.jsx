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
} from '@mui/material';

import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ChatBubbleOutlineOutlinedIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';

import './DataTable.css';
import CommentDialog from './CommentDialog';

const DataTable1 = forwardRef(
  ({ jsonData, onBookmarkClick, onApprove, editMode = false }, ref) => {
    const containerRef = useRef(null);
    const sentinelRef = useRef(null);
    const pageRefs = useRef({});

    const [tables, setTables] = useState([]);
    const [visiblePages, setVisiblePages] = useState(1);
    const [currentPageIndex, setCurrentPageIndex] = useState(0);
    const [loading, setLoading] = useState(false);
    const [hovered, setHovered] = useState({ t: null, i: null });

    const [isCommentOpen, setIsCommentOpen] = useState(false);
    const [currentCommentText, setCurrentCommentText] = useState('');
    const commentTargetRef = useRef({ t: null, i: null });

    // --------------------
    // helper: checks
    // --------------------
    // Return true only when:
    //  - item exists
    //  - item.user_editable === true
    //  - editMode === true (user clicked Edit/Refine)
    //  - item.is_textbox !== false (textbox allowed)
    const isEditable = (item) => {
      if (!item) return false;
      if (item.user_editable !== true) return false; // must be explicitly editable
      if (!editMode) return false; // only editable when edit mode is ON
      if (item.is_textbox === false) return false; // textbox not allowed
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
    useEffect(() => {
      const fresh = jsonData?.Tables ?? [];
      setTables(fresh);
      setVisiblePages(1);
      setCurrentPageIndex(0);
    }, [jsonData]);

    // FLATTEN ITEMS (hide disable_text: true in UI)
    const allItems = useMemo(() => {
      const arr = [];
      (tables || []).forEach((table, tIdx) => {
        (table.Items || [])
          .filter((item) => item.disable_text !== true)
          .forEach((item, iIdx) => {
            arr.push({ ...item, __t: tIdx, __i: iIdx });
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
        next[t].Items[i] = { ...next[t].Items[i], value: val };
        return next;
      });
    };

    // COMMENT HANDLING
    const openComment = (t, i) => {
      commentTargetRef.current = { t, i };
      const item = tables?.[t]?.Items?.[i];
      setCurrentCommentText(item?._comment || '');
      setIsCommentOpen(true);
    };

    const saveComment = () => {
      const { t, i } = commentTargetRef.current;
      if (t == null || i == null) return;

      setTables((prev) => {
        const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
        next[t].Items[i] = {
          ...next[t].Items[i],
          _comment: currentCommentText,
        };
        return next;
      });

      setIsCommentOpen(false);
    };

    if (totalPages === 0) return <Typography>No Data</Typography>;

    // HOVER ACTIONS: only show when editMode=true AND item editable AND hovered
    const renderHoverActions = (tIdx, iIdx, editable) => {
      if (!editMode) return null;
      if (!editable) return null;
      if (tIdx == null || iIdx == null) return null;
      if (hovered.t !== tIdx || hovered.i !== iIdx) return null;

      return (
        <div className="dt-hover-actions">
          <IconButton size="small" onClick={() => onApprove?.(tIdx, iIdx)}>
            <CheckCircleIcon className="dt-icon-approve" />
          </IconButton>

          <IconButton size="small" onClick={() => openComment(tIdx, iIdx)}>
            <ChatBubbleOutlineOutlinedIcon className="dt-icon-comment" />
          </IconButton>

          {/* Bookmark: send the full row object (safe lookup) */}
          <IconButton
            size="small"
            onClick={() => {
              const row =
                // safe access to the row object from tables state
                (Array.isArray(tables) &&
                  tables[tIdx] &&
                  Array.isArray(tables[tIdx].Items) &&
                  tables[tIdx].Items[iIdx]) ??
                null;

              // call parent with object; fallback to {__t,__i} if not found
              onBookmarkClick?.(row ?? { __t: tIdx, __i: iIdx });
            }}
          >
            <MenuBookOutlinedIcon className="dt-icon-bookmark" />
          </IconButton>
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
                    const value = col.value ?? col.Value ?? '';
                    const label = col.field ?? col.Field ?? '';
                    const rows = col.rendering_row ? col.rendering_row : 1;

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
                            <Typography style={{ marginBottom: 4 }}>
                              {label}
                            </Typography>

                            {isCheckboxUI ? (
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
                            ) : col.user_editable !== true ? (
                              // user_editable === false → render plain text
                              <Typography>{value}</Typography>
                            ) : (
                              // user_editable === true → show textarea but enable only when isEditable(col) === true
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
                            )}

                            {renderHoverActions(tIdx, iIdx, editable)}

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
                                ) : col.user_editable !== true ? (
                                  <Typography>{value}</Typography>
                                ) : (
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
                                )}

                                {renderHoverActions(tIdx, iIdx, editable)}

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
                    </React.Fragment>
                  );
                })}
              </TableBody>
            </Table>

            <Divider className="dt-divider" />
          </TableContainer>
        );
      });
    };
    // NORMAL (NON-TABLE) ITEMS - for pages outside 9–42
    const renderNormalItems = (normalItems, pageNo) => {
      if (normalItems.length === 0) return null;

      let groupedNormal = {};

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
            <TableHead>
              <TableRow>
                <TableCell className="dt-thead-cell dt-field-header">
                  Field
                </TableCell>
                <TableCell className="dt-thead-cell dt-value-header">
                  Value
                </TableCell>
              </TableRow>
            </TableHead>

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
                            {first.user_editable !== true ? (
                              <Typography>{value}</Typography>
                            ) : (
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
                            )}

                            {renderHoverActions(tIdx, iIdx, editable)}

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
                          {first.checkbox_value !== undefined ? (
                            <Checkbox
                              size="small"
                              checked={!!first.checkbox_value}
                            />
                          ) : null}
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
                                {isCheckboxUI ? (
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
                                ) : r.user_editable !== true ? (
                                  <Typography>{value}</Typography>
                                ) : (
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
                                )}

                                {renderHoverActions(tIdx, iIdx, editable)}

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
      const items = pageItems.filter((i) => i.disable_text !== true);

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
          groupsByRow[key].remarkItem = item;
        } else if (item.task_type === 'verdict') {
          groupsByRow[key].verdictItem = item;
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
            <Typography>{fieldLabel}</Typography>

            {comment && (
              <Typography variant="caption" className="dt-comment-caption">
                💬 {comment}
              </Typography>
            )}
          </div>
        );
      };

      // Remark / Verdict Cells
      const renderRemarkOrVerdictCell = (item) => {
        if (!item) return null;

        const tIdx = item.__t;
        const iIdx = item.__i;

        const editable = isEditable(item);

        const value = item.value ?? item.Value ?? '';
        const rows = item.rendering_row || 1;
        const comment = item._comment;

        // if item is not user_editable -> render plain text
        if (item.user_editable !== true) {
          return (
            <div className="dt-value-column dt-relative">
              <Typography>{value}</Typography>
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
            className="dt-value-column dt-relative"
            onMouseEnter={() => setHovered({ t: tIdx, i: iIdx })}
            onMouseLeave={() => setHovered({ t: null, i: null })}
          >
            <textarea
              className="dt-textarea dt-textarea-with-actions"
              value={value}
              rows={rows}
              disabled={!editable}
              onChange={(e) =>
                editable && updateCell(tIdx, iIdx, e.target.value)
              }
            />

            {renderHoverActions(tIdx, iIdx, editable)}

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
                    {renderRemarkOrVerdictCell(row.remarkItem)}
                  </TableCell>

                  <TableCell sx={bodyCellSx}>
                    {renderRemarkOrVerdictCell(row.verdictItem)}
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
          <div className="dt-sticky-header">
            <Typography variant="h6" className="dt-header-title">
              Report
            </Typography>
          </div>

          {visiblePageNos.map((pageNo) => {
            const pageItems = pageMap[pageNo] || [];

            const tableItems = pageItems.filter(
              (it) => it.is_table === true && it.disable_text !== true
            );
            const normalItems = pageItems.filter(
              (it) => it.is_table !== true && it.disable_text !== true
            );

            return (
              <div
                className="dt-page"
                key={pageNo}
                ref={(el) => (pageRefs.current[pageNo] = el)}
              >
                <Typography className="dt-page-title">Page {pageNo}</Typography>

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
          comments={[]}
          currentComment={currentCommentText}
          setCurrentComment={setCurrentCommentText}
          onSubmit={saveComment}
        />
      </>
    );
  }
);

export default DataTable1;
