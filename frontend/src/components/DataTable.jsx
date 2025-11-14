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

const LOCAL_STORAGE_KEY = 'editable_json_report';

const DataTable = ({ jsonData, onDataChange }) => {
  const [editableData, setEditableData] = useState({});
  const [visiblePages, setVisiblePages] = useState(3);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  const observerRef = useRef(null);
  const containerRef = useRef(null);
  const pageRefs = useRef({});

  // Load saved data or fallback to json
  useEffect(() => {
    const savedData = localStorage.getItem(LOCAL_STORAGE_KEY);

    if (savedData) {
      try {
        const parsedSaved = JSON.parse(savedData);

        // If the incoming JSON is different from the saved one → use new JSON
        if (JSON.stringify(parsedSaved) !== JSON.stringify(jsonData)) {
          setEditableData(jsonData);
          localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(jsonData));
        } else {
          setEditableData(parsedSaved);
        }
      } catch (e) {
        console.error('Error parsing saved JSON:', e);
        setEditableData(jsonData);
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(jsonData));
      }
    } else {
      // No local data, use latest JSON
      setEditableData(jsonData);
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(jsonData));
    }
  }, [jsonData]);

  // Save edits to localStorage
  useEffect(() => {
    if (Object.keys(editableData).length > 0) {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(editableData));
    }
  }, [editableData]);

  // Handle field edit
  const handleValueChange = (path, newValue) => {
    const keys = path.split('.');
    const updatedData = structuredClone(editableData);
    let current = updatedData;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) current[keys[i]] = {};
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = newValue;
    setEditableData(updatedData);
    if (onDataChange) onDataChange(updatedData);
  };

  // Render array values
  const renderArray = (arr, path) => {
    if (!Array.isArray(arr)) return null;
    if (arr.length > 0 && typeof arr[0] === 'object') {
      return arr.map((obj, idx) => (
        <Box key={`${path}.${idx}`} sx={{ marginY: 2 }}>
          <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
            {`Item ${idx + 1}`}
          </Typography>
          {renderTable(obj, `${path}.${idx}`)}
        </Box>
      ));
    }
    return (
      <TextField
        fullWidth
        variant="outlined"
        size="small"
        value={arr.join(', ')}
        onChange={(e) =>
          handleValueChange(
            path,
            e.target.value.split(',').map((v) => v.trim())
          )
        }
      />
    );
  };

  // Render nested tables
  const renderTable = (data, parentPath = '') => {
    if (!data || typeof data !== 'object') return null;
    return (
      <TableContainer
        component={Paper}
        sx={{ mb: 3, backgroundColor: '#fafafa' }}
      >
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 'bold', width: '35%' }}>
                Field
              </TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Value</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(data).map(([key, value]) => {
              const path = parentPath ? `${parentPath}.${key}` : key;
              if (typeof value === 'object' && !Array.isArray(value)) {
                return (
                  <TableRow key={path}>
                    <TableCell
                      colSpan={2}
                      sx={{ background: '#f5f5f5', fontWeight: 'bold' }}
                    >
                      {key}
                      {renderTable(value, path)}
                    </TableCell>
                  </TableRow>
                );
              }
              if (Array.isArray(value)) {
                return (
                  <TableRow key={path}>
                    <TableCell sx={{ fontWeight: 500 }}>{key}</TableCell>
                    <TableCell>{renderArray(value, path)}</TableCell>
                  </TableRow>
                );
              }
              return (
                <TableRow key={path}>
                  <TableCell sx={{ fontWeight: 500 }}>{key}</TableCell>
                  <TableCell>
                    <TextField
                      fullWidth
                      variant="outlined"
                      size="small"
                      value={value || ''}
                      onChange={(e) => handleValueChange(path, e.target.value)}
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  // Infinite scroll logic (fixed)
  useEffect(() => {
    if (!observerRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const last = entries[0];
        const totalPages = Object.keys(editableData).length; // fixed

        if (last.isIntersecting && !loading && visiblePages < totalPages) {
          setLoading(true);
          setTimeout(() => {
            setVisiblePages((prev) => Math.min(prev + 3, totalPages));
            setLoading(false);
          }, 500);
        }
      },
      { threshold: 0.3 } // trigger earlier
    );

    observer.observe(observerRef.current);
    return () => observer.disconnect();
  }, [loading, visiblePages, editableData]);

  // Scroll listener to sync pagination
  useEffect(() => {
    const handleScroll = () => {
      const positions = Object.entries(pageRefs.current).map(([page, ref]) => ({
        page,
        top: ref?.offsetTop || 0,
      }));

      const scrollPos = containerRef.current.scrollTop;
      let current = 1;
      for (let i = 0; i < positions.length; i++) {
        if (scrollPos + 150 >= positions[i].top)
          current = Number(positions[i].page);
      }
      setCurrentPage(current);
    };

    const ref = containerRef.current;
    if (ref) ref.addEventListener('scroll', handleScroll);
    return () => ref?.removeEventListener('scroll', handleScroll);
  }, []);

  // Scroll to a specific page
  const handlePageChange = (event, page) => {
    setCurrentPage(page);
    const ref = pageRefs.current[page];
    if (ref && containerRef.current) {
      containerRef.current.scrollTo({
        top: ref.offsetTop,
        behavior: 'smooth',
      });
    }
  };

  const pageEntries = Object.entries(editableData).slice(0, visiblePages);

  // Reset all data
  const handleReset = () => {
    localStorage.removeItem(LOCAL_STORAGE_KEY);
    setEditableData(jsonData);
  };

  return (
    <Box
      ref={containerRef}
      sx={{
        height: '85vh',
        overflowY: 'auto',
        padding: 3,
        background: '#f9f9f9',
        position: 'relative',
      }}
    >
      {/* Sticky header with pagination */}
      <Box
        sx={{
          position: 'sticky',
          top: 0,
          background: '#f9f9f9',
          zIndex: 3,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: 1,
          borderBottom: '2px solid #ddd',
          mb: 2,
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
          📄 Report
        </Typography>

        <Pagination
          count={Object.keys(editableData).length}
          page={currentPage}
          onChange={handlePageChange}
          color="primary"
          size="small"
          sx={{ marginRight: 2 }}
        />

        <button
          style={{
            background: '#e53935',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            padding: '6px 12px',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
          onClick={handleReset}
        >
          Reset Form
        </button>
      </Box>

      {/* Render visible pages */}
      {pageEntries.map(([pageKey, sections], index) => (
        <Box
          key={pageKey}
          ref={(el) => (pageRefs.current[index + 1] = el)}
          sx={{ mb: 5 }}
        >
          <Typography
            variant="h6"
            sx={{
              fontWeight: 'bold',
              color: '#333',
              mb: 2,
              borderBottom: '2px solid #ccc',
              pb: '4px',
            }}
          >
            {pageKey}
          </Typography>

          {Object.entries(sections).map(([sectionTitle, sectionData]) => (
            <Box key={sectionTitle} sx={{ mb: 4 }}>
              <Typography
                variant="subtitle1"
                sx={{
                  fontWeight: 'bold',
                  color: '#555',
                  mb: 1,
                  mt: 2,
                }}
              >
                {sectionTitle}
              </Typography>
              {renderTable(sectionData, `${pageKey}.${sectionTitle}`)}
            </Box>
          ))}

          <Divider sx={{ mt: 3, mb: 3 }} />
        </Box>
      ))}

      {/* Show loader only if more pages left */}
      {loading && visiblePages < Object.keys(editableData).length && (
        <Box display="flex" justifyContent="center" my={2}>
          <CircularProgress />
        </Box>
      )}

      {/* Sentinel */}
      <div ref={observerRef} style={{ height: '50px' }} />
    </Box>
  );
};

export default DataTable;
