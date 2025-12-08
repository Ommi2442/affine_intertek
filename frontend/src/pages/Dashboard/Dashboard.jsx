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
  CircularProgress,
  Alert,
  Skeleton,
} from '@mui/material';

import SearchIcon from '@mui/icons-material/Search';
import { fetchProjectsRequest } from '../../redux/features/dashboard/dashboardSlice';
import { useDispatch, useSelector } from 'react-redux';
import AppBreadcrumbs from '../../components/AppBreadCrumbs';
import { useNavigate } from 'react-router-dom';

const Dashboard = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const dashboardState = useSelector((state) => state.dashboard || {});
  const { projects = [], loading = false, error = null } = dashboardState;

  // projects.data = array of projects
  // projects.user_role = role coming from backend
  const user_role = projects?.user_role || 2;

  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(7);

  const renderYesNo = (value) => {
    const val = value === true || value === 'true';
    return (
      <Box
        onClick={() => navigate('/create-project')}
        sx={{
          color: val ? 'green' : 'red',
          cursor: 'pointer',
          textAlign: 'center',
        }}
      >
        {val ? 'Yes' : 'No'}
      </Box>
    );
  };

  useEffect(() => {
    dispatch(fetchProjectsRequest());
  }, [dispatch]);

  const filtered =
    projects?.data?.filter(
      (item) =>
        item.Client_Name?.toLowerCase().includes(search.toLowerCase()) ||
        item.Standard?.toLowerCase().includes(search.toLowerCase()) ||
        item.Project_Id?.toLowerCase().includes(search.toLowerCase())
    ) || [];

  const totalPages = Math.ceil(filtered?.length / rowsPerPage);

  const paginated = filtered?.slice(
    (page - 1) * rowsPerPage,
    page * rowsPerPage
  );

  const SkeletonRow = () => (
    <TableRow>
      {Array.from({ length: user_role === 1 ? 9 : 8 }).map((_, i) => (
        <TableCell key={i} align="center">
          <Skeleton variant="text" width="80%" height={22} />
        </TableCell>
      ))}
    </TableRow>
  );

  return (
    <Box
      sx={{
        p: 3,
        backgroundColor: 'white',
        borderRadius: '8px',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          mb: 3,
          alignItems: 'center',
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
          My Projects
        </Typography>

        <TextField
          variant="outlined"
          placeholder="Search..."
          size="small"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{
            width: '30%',
            '& .MuiOutlinedInput-root': {
              borderRadius: '50px',
            },
          }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <SearchIcon sx={{ color: '#555' }} />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <TableContainer component={Paper}>
        {error && !loading && (
          <Box sx={{ p: 3 }}>
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

              {/* ✅ Show ONLY for Admin */}
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
              paginated?.map((row, index) => (
                <TableRow key={index}>
                  <TableCell align="center">{row?.Standard}</TableCell>
                  <TableCell align="center">{row?.Client_Name}</TableCell>
                  <TableCell align="center">{row?.Product}</TableCell>
                  <TableCell align="center">{row?.Project_Id}</TableCell>
                  <TableCell align="center">
                    {row?.Proj_Created_On
                      ? new Date(row.Proj_Created_On).toLocaleDateString()
                      : '-'}
                  </TableCell>

                  {/* ✅ Only Admin sees Creator */}
                  {user_role === 1 && (
                    <TableCell align="center">{row?.Proj_Created_By}</TableCell>
                  )}

                  <TableCell align="center">
                    {renderYesNo(row?.TRF_Generated)}
                  </TableCell>
                  <TableCell align="center">
                    {renderYesNo(row?.CDR_Generated)}
                  </TableCell>
                  <TableCell align="center">
                    {renderYesNo(row?.Letter_Generated)}
                  </TableCell>

                  <TableCell align="center">
                    <IconButton>
                      <img src="/images/edit.png" width={18} height={18} />
                    </IconButton>

                    <IconButton>
                      <img src="/images/add-file.png" width={18} height={18} />
                    </IconButton>

                    <IconButton>
                      <img src="/images/delete.png" width={18} height={18} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}

            {!loading && !error && paginated?.length === 0 && (
              <TableRow>
                <TableCell colSpan={user_role === 1 ? 10 : 9} align="center">
                  No projects found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Box
        sx={{
          mt: 3,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography>Rows per page:</Typography>

          <Select
            value={rowsPerPage}
            size="small"
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

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <Button
            variant="contained"
            disabled={page === 1 || loading}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>

          <Typography sx={{ fontWeight: 'bold' }}>
            Page {page} of {totalPages}
          </Typography>

          <Button
            variant="contained"
            disabled={page === totalPages || loading}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

export default Dashboard;
