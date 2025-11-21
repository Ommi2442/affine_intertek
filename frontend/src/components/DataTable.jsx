import React, { useState, useEffect, useRef } from 'react';
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
  TextField,
  CircularProgress,
  Pagination,
} from '@mui/material';

// If you want to import your uploaded json directly, uncomment and use this path:
// import jsonData from "/mnt/data/dot.json";

const STORAGE_KEY = 'report_tables_saved_v1';

const DataTable = ({ jsonData }) => {
  // if caller doesn't pass jsonData, try to load from file path (fallback)
  // Note: In many React setups importing from /mnt/data won't work at runtime — prefer passing jsonData as prop.
  const fallbackJson = typeof jsonData === 'undefined' ? null : jsonData;

  const [tables, setTables] = useState([]);
  const [visiblePages, setVisiblePages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);

  const containerRef = useRef(null);
  const observerRef = useRef(null);
  const pageRefs = useRef({});

  // Load saved data OR jsonData.Tables on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          setTables(parsed);
        } else if (parsed?.Tables) {
          setTables(parsed.Tables);
        }
      } else if (fallbackJson?.Tables) {
        setTables(fallbackJson.Tables);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(fallbackJson.Tables));
      } else if (jsonData?.Tables) {
        // if jsonData prop passed
        setTables(jsonData.Tables);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(jsonData.Tables));
      } else {
        setTables([]);
      }
    } catch (err) {
      console.error('Error loading saved tables:', err);
      if (jsonData?.Tables) {
        setTables(jsonData.Tables);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(jsonData.Tables));
      }
    }

    setVisiblePages(1);
  }, [jsonData, fallbackJson]);

  // Save to localStorage
  const saveToStorage = (updatedTables) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedTables));
    } catch (err) {
      console.error('Error saving to storage:', err);
    }
  };

  // Update value - uses real indices
  const handleValueChange = (tableIndex, itemIndex, newValue) => {
    setTables((prev) => {
      const updated = prev.map((t, ti) =>
        ti === tableIndex
          ? {
              ...t,
              Items: t.Items.map((it, ii) =>
                ii === itemIndex ? { ...it, Value: newValue } : it
              ),
            }
          : t
      );
      saveToStorage(updated);
      return updated;
    });
  };

  // Infinite scroll: observe sentinel and increase visiblePages
  useEffect(() => {
    const sentinel = observerRef.current;
    if (!sentinel) return;
    if (!tables || tables.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const e = entries[0];
        if (e.isIntersecting && visiblePages < tables.length && !loading) {
          setLoading(true);
          // load 1 more page at a time (you can increase)
          setTimeout(() => {
            setVisiblePages((p) => Math.min(p + 1, tables.length));
            setLoading(false);
          }, 300);
        }
      },
      { root: containerRef.current, threshold: 0.1 }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [tables, visiblePages, loading]);

  // Update active pagination on scroll
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onScroll = () => {
      const scrollTop = el.scrollTop;
      let active = 1;

      // determine the highest page whose top is <= scrollTop + offset
      const offset = 160; // tweak if header/padding differ
      for (let p = 1; p <= visiblePages; p++) {
        const ref = pageRefs.current[p];
        if (ref) {
          if (scrollTop + offset >= ref.offsetTop) {
            active = p;
          }
        }
      }

      setCurrentPage(active);
    };

    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [visiblePages]);

  // Pagination click -> scroll to page
  const handlePageChange = (e, page) => {
    setCurrentPage(page);
    const ref = pageRefs.current[page];
    if (ref && containerRef.current) {
      containerRef.current.scrollTo({
        top: ref.offsetTop,
        behavior: 'smooth',
      });
    }
  };

  return (
    <Box
      ref={containerRef}
      sx={{
        height: '85vh',
        overflowY: 'auto',
        padding: 3,
        background: '#ffffff',
        position: 'relative',
      }}
    >
      {/* Sticky header */}
      <Box
        sx={{
          position: 'sticky',
          top: 0,
          background: '#ffffff',
          zIndex: 10,
          borderBottom: '2px solid #e0e0e0',
          py: 1,
          mb: 2,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            px: 1,
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            Report
          </Typography>

          {/* top pagination (optional) */}
          {/* <Pagination
            count={tables.length || 1}
            page={currentPage}
            onChange={handlePageChange}
            color="primary"
            size="small"
          /> */}
        </Box>
      </Box>

      {/* Render visible tables (Page 1 = Table 0) */}
      {(tables || []).slice(0, visiblePages).map((table, tableIndex) => (
        <Box
          key={tableIndex}
          ref={(el) => (pageRefs.current[tableIndex + 1] = el)}
          sx={{ mb: 6 }}
        >
          <Typography
            variant="h6"
            sx={{
              fontWeight: '700',
              mb: 2,
              borderBottom: '2px solid #f0f0f0',
              pb: 1,
            }}
          >
            Page {tableIndex + 1} (Table {table.Table})
          </Typography>

          <TableContainer component={Paper} sx={{ mb: 3 }}>
            <Table
              size="small"
              sx={{
                tableLayout: 'fixed',
                width: '100%',
                borderCollapse: 'separate',
              }}
            >
              <TableHead>
                <TableRow>
                  {/* Fixed width Field column: 35% */}
                  <TableCell sx={{ fontWeight: '700', width: '35%' }}>
                    Field
                  </TableCell>

                  {/* Value column takes remaining 65% */}
                  <TableCell sx={{ fontWeight: '700', width: '65%' }}>
                    Value
                  </TableCell>
                </TableRow>
              </TableHead>

              <TableBody>
                {table.Items.map((item, itemIndex) => {
                  // if Field is empty, skip rendering (keeps original indices intact)
                  if (!item.Field) return null;

                  return (
                    <TableRow key={itemIndex}>
                      <TableCell
                        sx={{
                          verticalAlign: 'top',
                          whiteSpace: 'normal',
                        }}
                      >
                        {item.Field}
                      </TableCell>

                      <TableCell sx={{ width: '65%' }}>
                        <TextField
                          fullWidth
                          multiline
                          minRows={1}
                          maxRows={5}
                          size="small"
                          sx={{
                            width: '100%',
                            '& .MuiInputBase-input': {
                              whiteSpace: 'normal', // FULL text visible
                            },
                          }}
                          value={item.Value ?? ''}
                          onChange={(e) =>
                            handleValueChange(
                              tableIndex,
                              itemIndex,
                              e.target.value
                            )
                          }
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>

          <Divider sx={{ mb: 3 }} />
        </Box>
      ))}

      {/* Sentinel placed before sticky bottom pagination so observer can detect end of content */}
      <div ref={observerRef} style={{ height: 90 }} />

      {/* Sticky bottom pagination */}

      <Box
        sx={{
          position: 'sticky',
          bottom: 0,
          background: '#ffffff',
          zIndex: 12,
          borderTop: '2px solid #e0e0e0',
          py: 2,
          height: '50px',
          mt: 2,
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <Pagination
          count={tables.length || 1}
          page={currentPage}
          onChange={handlePageChange}
          color="primary"
          size="small"
        />
      </Box>

      {/* Loader indicator */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
          <CircularProgress size={28} />
        </Box>
      )}
    </Box>
  );
};

export default DataTable;
