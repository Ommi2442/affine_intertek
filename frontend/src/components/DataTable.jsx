import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ChatBubbleOutlineOutlinedIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';

import './DataTable.css';
import jsonFromFile from '../utils/final_payload.json';
import CommentDialog from './CommentDialog';

const STORAGE_KEY = 'report_tables_saved_v3';

function debounce(fn, wait) {
  let t = null;
  return (...args) => {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

const DataTable = ({ jsonData = jsonFromFile, onBookmarkClick, onApprove }) => {
  const tablesRef = useRef([]);
  const [visiblePages, setVisiblePages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [renderTick, setRenderTick] = useState(0);

  const [hovered, setHovered] = useState({ table: null, row: null });

  const [isCommentOpen, setIsCommentOpen] = useState(false);
  const [currentCommentText, setCurrentCommentText] = useState('');
  const commentTargetRef = useRef({ table: null, row: null });

  const containerRef = useRef(null);
  const observerRef = useRef(null);
  const pageRefs = useRef({});
  const existingCommentsArray = [];

  const saveToStorageDebounced = useRef(
    debounce((data) => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      } catch (e) {
        console.error('save error', e);
      }
    }, 800)
  ).current;

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          tablesRef.current = parsed;
        } else if (parsed?.Tables) {
          tablesRef.current = parsed.Tables;
        } else if (jsonData?.Tables) {
          tablesRef.current = jsonData.Tables;
        } else {
          tablesRef.current = [];
        }
      } else if (jsonData?.Tables) {
        tablesRef.current = jsonData.Tables;
        saveToStorageDebounced(tablesRef.current);
      } else {
        tablesRef.current = [];
      }
    } catch (err) {
      console.error('Data load error', err);
      tablesRef.current = jsonData?.Tables ?? [];
    }
    setVisiblePages(1);
    setRenderTick((t) => t + 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jsonData]);

  const persistRef = useCallback(() => {
    saveToStorageDebounced(tablesRef.current);
  }, [saveToStorageDebounced]);

  const updateCell = (tableIndex, itemIndex, newValue) => {
    const tables = tablesRef.current;
    if (!tables?.[tableIndex]) return;
    tables[tableIndex].Items[itemIndex] = {
      ...tables[tableIndex].Items[itemIndex],
      value: newValue,
    };
    persistRef();
    setRenderTick((t) => t + 1);
  };

  const getVisibleTables = () => {
    return (tablesRef.current || []).slice(0, visiblePages);
  };

  const handleBookmark = (tableIndex, itemIndex) => {
    const item = tablesRef.current?.[tableIndex]?.Items?.[itemIndex];
    if (!item) return;
    const payload = {
      field: item.field ?? item.Field ?? 'Field',
      value: item.value ?? item.Value ?? '',
      tableIndex,
      itemIndex,
    };
    if (typeof onBookmarkClick === 'function') onBookmarkClick(payload);
  };

  const handleApprove = (tableIndex, itemIndex) => {
    const item = tablesRef.current?.[tableIndex]?.Items?.[itemIndex];
    if (!item) return;
    if (typeof onApprove === 'function') {
      onApprove({
        tableIndex,
        itemIndex,
        field: item.field ?? item.Field,
        value: item.value ?? item.Value,
      });
    }
  };

  const openComment = (tableIndex, itemIndex) => {
    const item = tablesRef.current?.[tableIndex]?.Items?.[itemIndex];
    commentTargetRef.current = { table: tableIndex, row: itemIndex };
    setCurrentCommentText(item?._comment ?? '');
    setIsCommentOpen(true);
  };

  const saveComment = () => {
    const { table, row } = commentTargetRef.current;
    if (table == null) {
      setIsCommentOpen(false);
      return;
    }
    const tables = tablesRef.current;
    tables[table].Items[row] = {
      ...tables[table].Items[row],
      _comment: currentCommentText,
    };
    persistRef();
    setIsCommentOpen(false);
    setRenderTick((t) => t + 1);
  };

  useEffect(() => {
    const sentinel = observerRef.current;
    if (!sentinel) return;
    if (!tablesRef.current || tablesRef.current.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const e = entries[0];
        if (
          e.isIntersecting &&
          visiblePages < tablesRef.current.length &&
          !loading
        ) {
          setLoading(true);
          setTimeout(() => {
            setVisiblePages((p) => Math.min(p + 1, tablesRef.current.length));
            setLoading(false);
          }, 250);
        }
      },
      { root: containerRef.current, threshold: 0.15 }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [visiblePages, loading]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      const scrollTop = el.scrollTop;
      let active = 1;
      const offset = 160;
      for (let p = 1; p <= visiblePages; p++) {
        const ref = pageRefs.current[p];
        if (ref && scrollTop + offset >= ref.offsetTop) active = p;
      }
      setCurrentPage(active);
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [visiblePages]);

  const handlePageChange = (e, page) => {
    setCurrentPage(page);
    const ref = pageRefs.current[page];
    if (ref && containerRef.current) {
      containerRef.current.scrollTo({ top: ref.offsetTop, behavior: 'smooth' });
    }
  };

  const visibleTables = getVisibleTables();

  return (
    <>
      <div className="dt-container" ref={containerRef}>
        <div className="dt-sticky-header">
          <div className="dt-header-inner">
            <Typography variant="h6" className="dt-header-title">
              Report
            </Typography>
          </div>
        </div>

        {(visibleTables || []).map((table, tableIndex) => {
          const realTableIndex = tableIndex;
          return (
            <div
              className="dt-page"
              key={realTableIndex}
              ref={(el) => (pageRefs.current[realTableIndex + 1] = el)}
            >
              <Typography className="dt-page-title">
                Page {realTableIndex + 1} (Table {table.Table})
              </Typography>

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
                    {(() => {
                      const grouped = {};
                      table.Items.forEach((item, idx) => {
                        const field = item.field ?? item.Field ?? '';
                        if (!field) return;
                        if (!grouped[field]) grouped[field] = [];
                        grouped[field].push({ ...item, __originalIndex: idx });
                      });

                      return Object.entries(grouped).map(
                        ([field, rows], groupIndex) => (
                          <TableRow key={groupIndex}>
                            <TableCell className="dt-field-cell">
                              {field}
                            </TableCell>

                            <TableCell className="dt-value-cell">
                              <div className="dt-value-row">
                                {rows.map((r, innerIdx) => {
                                  const realIndex = r.__originalIndex;
                                  const value = r.value ?? r.Value ?? '';

                                  return (
                                    <div
                                      key={innerIdx}
                                      className="dt-value-column"
                                      onMouseEnter={() =>
                                        setHovered({
                                          table: realTableIndex,
                                          row: realIndex,
                                        })
                                      }
                                      onMouseLeave={() =>
                                        setHovered({ table: null, row: null })
                                      }
                                      style={{ position: 'relative' }} // ✅ Make container relative
                                    >
                                      <textarea
                                        className="dt-textarea"
                                        value={value}
                                        onChange={(e) =>
                                          updateCell(
                                            realTableIndex,
                                            realIndex,
                                            e.target.value
                                          )
                                        }
                                        rows={1}
                                        style={{
                                          paddingRight: '70px', // ✅ Space for icons
                                        }}
                                      />

                                      {hovered.table === realTableIndex &&
                                        hovered.row === realIndex && (
                                          <div
                                            className="dt-hover-actions"
                                            style={{
                                              position: 'absolute',
                                              top: '50%', // vertically center
                                              right: '5px',
                                              transform: 'translateY(-50%)',
                                              display: 'flex',
                                              gap: '4px',
                                            }}
                                          >
                                            <IconButton
                                              size="small"
                                              onClick={() =>
                                                handleApprove(
                                                  realTableIndex,
                                                  realIndex
                                                )
                                              }
                                              aria-label="approve"
                                            >
                                              <CheckCircleIcon className="dt-icon-approve" />
                                            </IconButton>

                                            <IconButton
                                              size="small"
                                              onClick={() =>
                                                openComment(
                                                  realTableIndex,
                                                  realIndex
                                                )
                                              }
                                              aria-label="comment"
                                            >
                                              <ChatBubbleOutlineOutlinedIcon className="dt-icon-comment" />
                                            </IconButton>

                                            <IconButton
                                              size="small"
                                              onClick={() =>
                                                handleBookmark(
                                                  realTableIndex,
                                                  realIndex
                                                )
                                              }
                                              aria-label="bookmark"
                                            >
                                              <MenuBookOutlinedIcon className="dt-icon-bookmark" />
                                            </IconButton>
                                          </div>
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
                        )
                      );
                    })()}
                  </TableBody>
                </Table>
              </TableContainer>

              <Divider className="dt-divider" />
            </div>
          );
        })}

        <div ref={observerRef} className="dt-sentinel" />

        <div className="dt-pagination-wrapper">
          <Pagination
            count={tablesRef.current?.length || 1}
            page={currentPage}
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
        comments={existingCommentsArray}
        currentComment={currentCommentText}
        setCurrentComment={setCurrentCommentText}
        onSubmit={saveComment}
      />
    </>
  );
};

export default DataTable;
