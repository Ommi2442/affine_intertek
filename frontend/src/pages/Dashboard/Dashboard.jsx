import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  TableContainer,
  Paper,
  Button,
  InputAdornment,
  IconButton,
  MenuItem,
  Select,
  Alert,
  Skeleton,
} from '@mui/material';

import SearchIcon from '@mui/icons-material/Search';
import { fetchProjectsRequest } from '../../redux/features/dashboard/dashboardSlice';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { getProjectReportStatusApi } from '../../redux/api/projectStatusApi';
import { deleteProjectsRequest } from '../../redux/features/deleteProject/deleteProjectSlice';
import { archieveProjectsRequest } from '../../redux/features/archieveProject/archieveProjectSlice';

/* 👇 USE EXISTING API FILE */
// import {
//   deleteProjectApi,
//   archiveProjectApi,
// } from '../../redux/api/projectStatusApi';

const Dashboard = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const dashboardState = useSelector((state) => state.dashboard || {});
  const { projects = {}, loading = false, error = null } = dashboardState;

  const user_role = projects?.user_role || 2;

  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(7);

  useEffect(() => {
    dispatch(fetchProjectsRequest());
  }, [dispatch]);

  /*  FIX: Pass row details to create-project */
  const renderYesNo = (row, value, type) => {
    const val = value === true || value === 'true';

    const handleClick = () => {
      localStorage.setItem('projectId', row?.Project_Id);

      if (val == false) {
        navigate('/create-project', {
          state: {
            standard: row?.Standard,
            projectId: row?.Project_Id,
            clientName: row?.Client_Name,
            product: row?.Product,
            source: type,
          },
        });
      } else {
        navigate('/report-page', {
          state: {
            standard: row?.Standard,
            projectId: row?.Project_Id,
            clientName: row?.Client_Name,
            product: row?.Product,
            source: type, // TRF | CDR | LETTER
          },
        });
      }
    };

    return (
      <Box
        onClick={handleClick}
        sx={{
          color: val ? 'green' : 'red',
          cursor: 'pointer',
          textAlign: 'center',
          fontWeight: 600,
          '&:hover': { textDecoration: 'underline' },
        }}
      >
        {val ? 'Yes' : 'No'}
      </Box>
    );
  };

  /* ---------------- NEW: DELETE ---------------- */
  const handleDelete = async (row) => {
    const ok = window.confirm('Are you sure you want to delete this project?');
    if (!ok) return;

    dispatch(deleteProjectsRequest(row.Project_Id));
  };

  /* ---------------- NEW: ARCHIVE ---------------- */
  const handleArchive = async (row) => {
    const ok = window.confirm('Are you sure you want to archive this project?');
    if (!ok) return;

    const payload = {
      param: row.Project_Id,
      bodyObj: {
        Proj_Archived: true,
      },
    };

    dispatch(archieveProjectsRequest(payload));
  };

  const filtered =
    projects?.data?.filter(
      (item) =>
        item.Client_Name?.toLowerCase().includes(search.toLowerCase()) ||
        item.Standard?.toLowerCase().includes(search.toLowerCase()) ||
        item.Project_Id?.toLowerCase().includes(search.toLowerCase()) ||
        item.Product?.toLowerCase().includes(search.toLowerCase()) ||
        item.Proj_Created_On?.toLowerCase().includes(search.toLowerCase()) ||
        item.Proj_Created_By?.toLowerCase().includes(search.toLowerCase())
    ) || [];

  const totalPages = Math.ceil(filtered.length / rowsPerPage);

  const paginated = filtered.slice(
    (page - 1) * rowsPerPage,
    page * rowsPerPage
  );

  const SkeletonRow = () => (
    <TableRow>
      {Array.from({ length: user_role === 1 ? 10 : 9 }).map((_, i) => (
        <TableCell key={i} align="center">
          <Skeleton variant="text" width="80%" height={22} />
        </TableCell>
      ))}
    </TableRow>
  );

  return (
    <Box sx={{ p: 3, backgroundColor: 'white', borderRadius: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h5" fontWeight="bold">
          My Projects
        </Typography>

        <TextField
          placeholder="Search..."
          size="small"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ width: '30%' }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <TableContainer component={Paper}>
        {error && !loading && (
          <Box p={3}>
            <Alert severity="error">
              Failed to load projects. Please try again.
            </Alert>
          </Box>
        )}

        <Table>
          <TableHead sx={{ bgcolor: '#f5f5f5' }}>
            <TableRow>
              <TableCell align="center">
                <b>Standard</b>
              </TableCell>
              <TableCell align="center">
                <b>Client Name</b>
              </TableCell>
              <TableCell align="center">
                <b>Product</b>
              </TableCell>
              <TableCell align="center">
                <b>Project ID</b>
              </TableCell>
              <TableCell align="center">
                <b>Created On</b>
              </TableCell>

              {user_role === 1 && (
                <TableCell align="center">
                  <b>Created By</b>
                </TableCell>
              )}

              <TableCell align="center">
                <b>TRF Generated</b>
              </TableCell>
              <TableCell align="center">
                <b>CDR Generated</b>
              </TableCell>
              <TableCell align="center">
                <b>Letter Generated</b>
              </TableCell>
              <TableCell align="center">
                <b>Actions</b>
              </TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {loading &&
              Array.from({ length: rowsPerPage }).map((_, i) => (
                <SkeletonRow key={i} />
              ))}

            {!loading &&
              !error &&
              paginated.map((row, index) => (
                <TableRow key={index}>
                  <TableCell align="center">{row.Standard}</TableCell>
                  <TableCell align="center">{row.Client_Name}</TableCell>
                  <TableCell align="center">{row.Product}</TableCell>
                  <TableCell align="center">{row.Project_Id}</TableCell>
                  <TableCell align="center">
                    {row.Proj_Created_On
                      ? new Date(row.Proj_Created_On).toLocaleDateString()
                      : '-'}
                  </TableCell>

                  {user_role === 1 && (
                    <TableCell align="center">{row.Proj_Created_By}</TableCell>
                  )}

                  {/*  UPDATED CALLS */}
                  <TableCell align="center">
                    {renderYesNo(row, row.trf_completed, 'TRF')}
                  </TableCell>
                  <TableCell align="center">
                    {renderYesNo(row, row.cdr_completed, 'CDR')}
                  </TableCell>
                  <TableCell align="center">
                    {renderYesNo(row, row.letter_completed, 'LETTER')}
                  </TableCell>

                  <TableCell align="center">
                    <IconButton>
                      <img src="/images/edit.png" width={18} height={18} />
                    </IconButton>

                    <IconButton onClick={() => handleArchive(row)}>
                      <img src="/images/add-file.png" width={18} height={18} />
                    </IconButton>

                    <IconButton onClick={() => handleDelete(row)}>
                      <img src="/images/delete.png" width={18} height={18} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}

            {!loading && paginated.length === 0 && (
              <TableRow>
                <TableCell colSpan={user_role === 1 ? 10 : 9} align="center">
                  No projects found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography>Rows per page:</Typography>
          <Select
            size="small"
            value={rowsPerPage}
            onChange={(e) => {
              setRowsPerPage(e.target.value);
              setPage(1);
            }}
          >
            <MenuItem value={5}>5</MenuItem>
            <MenuItem value={7}>7</MenuItem>
            <MenuItem value={10}>10</MenuItem>
            <MenuItem value={20}>20</MenuItem>
          </Select>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            disabled={page === 1 || loading}
            onClick={() => setPage(page - 1)}
            variant="contained"
          >
            Previous
          </Button>

          <Typography fontWeight="bold">
            Page {page} of {totalPages}
          </Typography>

          <Button
            disabled={page === totalPages || loading}
            onClick={() => setPage(page + 1)}
            variant="contained"
          >
            Next
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

export default Dashboard;
