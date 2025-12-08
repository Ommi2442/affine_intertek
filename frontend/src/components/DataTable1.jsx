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
  ({ jsonData, onBookmarkClick, onApprove }, ref) => {
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

    // ---------------------------------------------------
    // EXPOSE UPDATED JSON TO PARENT (unchanged)
    // ---------------------------------------------------
    useImperativeHandle(ref, () => ({
      getUpdatedJson: () => ({ Tables: tables }),
    }));

    // ---------------------------------------------------
    // LOAD JSON
    // ---------------------------------------------------
    useEffect(() => {
      const fresh = jsonData?.Tables ?? [];
      setTables(fresh);
      setVisiblePages(1);
      setCurrentPageIndex(0);
    }, [jsonData]);

    // ---------------------------------------------------
    // FLATTEN ITEMS (hide disable_text: true)
    // ---------------------------------------------------
    const allItems = useMemo(() => {
      const arr = [];
      (tables || []).forEach((table, tIdx) => {
        (table.Items || [])
          .filter((item) => item.disable_text !== true) // 👈 HIDE ONLY IN UI
          .forEach((item, iIdx) => {
            arr.push({ ...item, __t: tIdx, __i: iIdx });
          });
      });
      return arr;
    }, [tables]);

    // ---------------------------------------------------
    // GROUP BY PAGE NUMBER
    // ---------------------------------------------------
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

    // ---------------------------------------------------
    // INFINITE SCROLL
    // ---------------------------------------------------
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

    // ---------------------------------------------------
    // SCROLL → ACTIVE PAGE
    // ---------------------------------------------------
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

    // ---------------------------------------------------
    // PAGINATION
    // ---------------------------------------------------
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

    // ---------------------------------------------------
    // UPDATE CELL VALUE
    // ---------------------------------------------------
    const updateCell = (t, i, val) => {
      setTables((prev) => {
        const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
        next[t].Items[i] = { ...next[t].Items[i], value: val };
        return next;
      });
    };

    // ---------------------------------------------------
    // COMMENT HANDLING
    // ---------------------------------------------------
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

    // ---------------------------------------------------
    // HOVER ACTIONS
    // ---------------------------------------------------
    const renderHoverActions = (tIdx, iIdx, editable) => {
      if (!editable) return null;
      if (hovered.t !== tIdx || hovered.i !== iIdx) return null;

      return (
        <div className="dt-hover-actions">
          <IconButton size="small" onClick={() => onApprove?.(tIdx, iIdx)}>
            <CheckCircleIcon className="dt-icon-approve" />
          </IconButton>
          <IconButton size="small" onClick={() => openComment(tIdx, iIdx)}>
            <ChatBubbleOutlineOutlinedIcon className="dt-icon-comment" />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => onBookmarkClick?.(tIdx, iIdx)}
          >
            <MenuBookOutlinedIcon className="dt-icon-bookmark" />
          </IconButton>
        </div>
      );
    };
    // ============================================================
    // TABLE MODE (is_table: true)
    // ============================================================
    const renderTableGroupsForPage = (pageItems) => {
      // filtered table items (hide disable_text)
      const tableItems = pageItems.filter(
        (it) => it.is_table === true && it.disable_text !== true
      );
      if (tableItems.length === 0) return null;

      // group by original table
      const groupsByTable = {};
      tableItems.forEach((item) => {
        const key = item.__t ?? 0;
        if (!groupsByTable[key]) groupsByTable[key] = [];
        groupsByTable[key].push(item);
      });

      // sort table groups by question_row (original order)
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

      // RENDER EACH TABLE GROUP
      return tableGroups.map((group, gIdx) => {
        // group rows inside this table by question_row
        const rowsByQR = {};
        group.forEach((it) => {
          const qr = typeof it.question_row === 'number' ? it.question_row : 0;
          if (!rowsByQR[qr]) rowsByQR[qr] = [];
          rowsByQR[qr].push(it);
        });

        const rowKeys = Object.keys(rowsByQR)
          .map(Number)
          .sort((a, b) => a - b);

        // number of columns across entire table (for full-width rows)
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
                  const rowItems = rowsByQR[qr].slice().sort((a, b) => {
                    const colA =
                      a.rendering_column ??
                      a.question_column ??
                      a.answer_column ??
                      0;
                    const colB =
                      b.rendering_column ??
                      b.question_column ??
                      b.answer_column ??
                      0;
                    return colA - colB;
                  });

                  // ==========================================
                  // SINGLE-ROW (or explicit single_row:true)
                  // ==========================================
                  if (
                    rowItems.length === 1 ||
                    rowItems[0].single_row === true
                  ) {
                    const col = rowItems[0];
                    const tIdx = col.__t;
                    const iIdx = col.__i;
                    const editable = col.user_editable === true;
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

                            {editable ? (
                              <textarea
                                className="dt-textarea dt-textarea-with-actions"
                                value={value}
                                rows={rows}
                                onChange={(e) =>
                                  updateCell(tIdx, iIdx, e.target.value)
                                }
                              />
                            ) : (
                              <Typography>{value}</Typography>
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

                  // ==========================================
                  // MULTI-COLUMN TABLE ROW
                  // ==========================================
                  return (
                    <React.Fragment key={qr}>
                      {/* HEADER ROW */}
                      <TableRow>
                        {rowItems.map((col, idx) => (
                          <TableCell key={idx} className="dt-thead-cell">
                            {col.field ?? col.Field ?? ''}
                          </TableCell>
                        ))}
                      </TableRow>

                      {/* VALUE ROW */}
                      <TableRow>
                        {rowItems.map((col, idx) => {
                          const tIdx = col.__t;
                          const iIdx = col.__i;

                          const editable = col.user_editable === true;
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
                                {editable ? (
                                  <textarea
                                    className="dt-textarea dt-textarea-with-actions"
                                    value={value}
                                    rows={rows}
                                    onChange={(e) =>
                                      updateCell(tIdx, iIdx, e.target.value)
                                    }
                                  />
                                ) : (
                                  <Typography>{value}</Typography>
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

    // ============================================================
    // NORMAL (NON-TABLE) ITEMS
    // ============================================================
    const renderNormalItems = (normalItems, pageNo) => {
      if (normalItems.length === 0) return null;

      let groupedNormal = {};

      // ======================================
      // PAGE 2 SPECIAL LOGIC:
      // Group by question_row (to display sequential blocks)
      // ======================================
      if (pageNo === 2) {
        normalItems.forEach((item) => {
          if (item.disable_text === true) return; // hide only UI
          const qr =
            typeof item.question_row === 'number' ? item.question_row : 0;
          if (!groupedNormal[qr]) groupedNormal[qr] = [];
          groupedNormal[qr].push(item);
        });
      }

      // ======================================
      // DEFAULT LOGIC (all other pages)
      // ======================================
      else {
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

                  // ==========================================
                  // SINGLE-ROW (non-table)
                  // ==========================================
                  if (first.single_row === true) {
                    const tIdx = first.__t;
                    const iIdx = first.__i;
                    const editable = first.user_editable === true;
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
                            {editable ? (
                              <textarea
                                className="dt-textarea dt-textarea-with-actions"
                                value={value}
                                rows={rows}
                                onChange={(e) =>
                                  updateCell(tIdx, iIdx, e.target.value)
                                }
                              />
                            ) : (
                              <Typography>{value}</Typography>
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

                  // ==========================================
                  // DEFAULT MULTI-VALUE ROW
                  // ==========================================
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

                            const editable = r.user_editable === true;
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
                                {editable ? (
                                  <textarea
                                    className="dt-textarea dt-textarea-with-actions"
                                    value={value}
                                    rows={rows}
                                    onChange={(e) =>
                                      updateCell(tIdx, iIdx, e.target.value)
                                    }
                                  />
                                ) : (
                                  <Typography>{value}</Typography>
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
    // ============================================================
    // RENDER FULL UI
    // ============================================================
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

            // Filter table + normal items (hide disable_text ONLY from UI)
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

                {/* TABLE MODE FIRST */}
                {tableItems.length > 0 && renderTableGroupsForPage(pageItems)}

                {/* NORMAL FIELDS NEXT */}
                {normalItems.length > 0 &&
                  renderNormalItems(normalItems, pageNo)}

                <Divider className="dt-divider" />
              </div>
            );
          })}

          {/* Infinite scroll sentinel */}
          <div ref={sentinelRef} className="dt-sentinel" />

          {/* Sticky pagination */}
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

        {/* COMMENT DIALOG */}
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
