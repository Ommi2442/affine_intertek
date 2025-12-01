import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
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
import jsonFromFile from '../utils/final_payload.json';
import CommentDialog from './CommentDialog';

const STORAGE_KEY = 'report_tables_saved_v3';

function debounce(fn, wait) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

const DataTable1 = ({
  jsonData = jsonFromFile,
  onBookmarkClick,
  onApprove,
}) => {
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

  // ---------------- LOAD JSON ----------------
  useEffect(() => {
    const fresh = jsonData?.Tables ?? [];
    setTables(fresh);
    setVisiblePages(1);
    setCurrentPageIndex(0);
  }, [jsonData]);

  // ---------------- FLATTEN ITEMS ----------------
  const allItems = useMemo(() => {
    const arr = [];
    (tables || []).forEach((table, tIdx) => {
      (table.Items || []).forEach((item, iIdx) => {
        arr.push({ ...item, __t: tIdx, __i: iIdx });
      });
    });
    return arr;
  }, [tables]);

  // ---------------- GROUP BY page_no / page_number ----------------
  const { pageNos, pageMap } = useMemo(() => {
    const map = {};
    allItems.forEach((item) => {
      let p = item.page_no ?? item.page_number ?? 1;

      p = Number(p);
      if (isNaN(p) || p <= 0) p = 1;

      if (!map[p]) map[p] = [];
      map[p].push(item);
    });

    const sorted = Object.keys(map)
      .map(Number)
      .sort((a, b) => a - b);

    return { pageNos: sorted, pageMap: map };
  }, [allItems]);

  const totalPages = pageNos.length;
  const visiblePageNos = pageNos.slice(0, visiblePages);

  const safeIndex =
    totalPages === 0
      ? 0
      : Math.min(Math.max(currentPageIndex, 0), totalPages - 1);

  // ---------------- INFINITE SCROLL ----------------
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

  // ---------------- SCROLL → ACTIVE PAGE ----------------
  useEffect(() => {
    const el = containerRef.current;
    if (!el || visiblePageNos.length === 0) return;

    const onScroll = () => {
      let active = safeIndex;
      const top = el.scrollTop;
      const offset = 150;

      visiblePageNos.forEach((p, idx) => {
        const ref = pageRefs.current[p];
        if (ref && top + offset >= ref.offsetTop) {
          active = idx;
        }
      });

      if (active !== safeIndex) {
        setCurrentPageIndex(active);
      }
    };

    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [visiblePageNos, safeIndex]);

  // ---------------- PAGINATION CLICK ----------------
  const handlePageChange = (e, pageIndex1Based) => {
    const idx = pageIndex1Based - 1;
    if (idx < 0 || idx >= totalPages) return;

    const targetPageNo = pageNos[idx];

    if (!visiblePageNos.includes(targetPageNo)) {
      setVisiblePages(idx + 1);
    }

    setCurrentPageIndex(idx);

    setTimeout(() => {
      const ref = pageRefs.current[targetPageNo];
      if (ref) {
        containerRef.current.scrollTo({
          top: ref.offsetTop,
          behavior: 'smooth',
        });
      }
    }, 80);
  };

  // ---------------- UPDATE CELL ----------------
  const updateCell = (t, i, newValue) => {
    setTables((prev) => {
      const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));
      next[t].Items[i] = { ...next[t].Items[i], value: newValue };
      return next;
    });
  };

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
      next[t].Items[i] = { ...next[t].Items[i], _comment: currentCommentText };
      return next;
    });

    setIsCommentOpen(false);
  };

  if (totalPages === 0) {
    return <Typography>No Data</Typography>;
  }

  // ---------------- RENDER ----------------
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

          const grouped = {};
          pageItems.forEach((item) => {
            const field = item.field ?? item.Field ?? '';
            if (!grouped[field]) grouped[field] = [];
            grouped[field].push(item);
          });

          return (
            <div
              className="dt-page"
              key={pageNo}
              ref={(el) => (pageRefs.current[pageNo] = el)}
            >
              <Typography className="dt-page-title">Page {pageNo}</Typography>

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
                    {Object.entries(grouped).map(([field, rows], index1) => (
                      <TableRow key={index1}>
                        <TableCell className="dt-field-cell">
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px',
                            }}
                          >
                            {/* ✔ Checkbox BEFORE KEY when answer_column === 3 OR when checkbox_value exists */}
                            {rows[0].checkbox_value !== undefined ||
                            rows[0].answer_column === 3 ? (
                              <Checkbox
                                size="small"
                                checked={!!rows[0].checkbox_value}
                              />
                            ) : null}

                            {field}
                          </div>
                        </TableCell>

                        <TableCell className="dt-value-cell">
                          <div className="dt-value-row">
                            {rows.map((r, index2) => {
                              const tIdx = r.__t;
                              const iIdx = r.__i;
                              const value = r.value ?? r.Value ?? '';

                              const editable = r.user_editable === true;

                              return (
                                <div
                                  key={index2}
                                  className="dt-value-column"
                                  onMouseEnter={() =>
                                    setHovered({ t: tIdx, i: iIdx })
                                  }
                                  onMouseLeave={() =>
                                    setHovered({ t: null, i: null })
                                  }
                                  style={{ position: 'relative' }}
                                >
                                  {/* ✔ Render textbox only if user_editable */}
                                  {editable ? (
                                    <textarea
                                      className="dt-textarea"
                                      value={value}
                                      onChange={(e) =>
                                        updateCell(tIdx, iIdx, e.target.value)
                                      }
                                      rows={1}
                                      style={{ paddingRight: '70px' }}
                                    />
                                  ) : (
                                    <Typography>{value}</Typography>
                                  )}

                                  {/* HOVER ICONS */}
                                  {hovered.t === tIdx &&
                                    hovered.i === iIdx &&
                                    editable && (
                                      <div
                                        className="dt-hover-actions"
                                        style={{
                                          position: 'absolute',
                                          top: '50%',
                                          right: '5px',
                                          transform: 'translateY(-50%)',
                                          display: 'flex',
                                          gap: '4px',
                                        }}
                                      >
                                        <IconButton
                                          size="small"
                                          onClick={() =>
                                            onApprove?.(tIdx, iIdx)
                                          }
                                        >
                                          <CheckCircleIcon className="dt-icon-approve" />
                                        </IconButton>

                                        <IconButton
                                          size="small"
                                          onClick={() =>
                                            openComment(tIdx, iIdx)
                                          }
                                        >
                                          <ChatBubbleOutlineOutlinedIcon className="dt-icon-comment" />
                                        </IconButton>

                                        <IconButton
                                          size="small"
                                          onClick={() =>
                                            onBookmarkClick?.(tIdx, iIdx)
                                          }
                                        >
                                          <MenuBookOutlinedIcon className="dt-icon-bookmark" />
                                        </IconButton>
                                      </div>
                                    )}

                                  {/* SHOW COMMENT */}
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
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

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
};

export default DataTable1;
