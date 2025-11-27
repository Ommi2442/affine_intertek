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
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import ArchiveIcon from '@mui/icons-material/Archive';

import dashboardData from '../../utils/dashboard.json';
import { fetchProjectsRequest } from '../../redux/features/dashboard/dashboardSlice';
import { useDispatch, useSelector } from 'react-redux';

const renderYesNo = (value) => {
  const val = value === true || value === 'true';
  return (
    <Box sx={{ color: val ? 'green' : 'red', textAlign: 'center' }}>
      {val ? 'Yes' : 'No'}
    </Box>
  );
};

const Dashboard = () => {
  const dispatch = useDispatch();

  const dashboardState = useSelector((state) => state.dashboard || {});
  const { projects = [], loading = false, error = null } = dashboardState;

  console.log('projects', projects);
  const [data, setData] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(7);

  useEffect(() => {
    //setData(dashboardData);
    dispatch(fetchProjectsRequest());
  }, [dispatch]);

  const filtered =
    projects?.data?.filter(
      (item) =>
        item.Client_Name.toLowerCase().includes(search.toLowerCase()) ||
        item.Standard.toLowerCase().includes(search.toLowerCase()) ||
        item.Project_Id?.toLowerCase().includes(search.toLowerCase())
    ) || [];

  const totalPages = Math.ceil(filtered?.length / rowsPerPage);

  const paginated = filtered?.slice(
    (page - 1) * rowsPerPage,
    page * rowsPerPage
  );

  const SkeletonRow = () => (
    <TableRow>
      {Array.from({ length: 8 }).map((_, i) => (
        <TableCell key={i} align="center">
          <Skeleton variant="text" width="80%" height={22} />
        </TableCell>
      ))}
    </TableRow>
  );

  return (
    <Box sx={{ p: 3 }}>
      {/* HEADER */}
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
          sx={{ width: '260px' }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <SearchIcon sx={{ color: '#555' }} />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {/* TABLE */}

      <TableContainer component={Paper}>
        {/* ERROR MESSAGE */}
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
                <b>Product ID</b>
              </TableCell>
              <TableCell align="center">
                <b>Created On</b>
              </TableCell>
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
            {/* SKELETON */}
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
                  <TableCell align="center">{row?.Project_Id}</TableCell>
                  <TableCell align="center">
                    {row?.Proj_Created_On
                      ? new Date(row.Proj_Created_On).toLocaleDateString()
                      : '-'}
                  </TableCell>

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
                      <EditIcon sx={{ color: 'black' }} />
                    </IconButton>
                    <IconButton>
                      <ArchiveIcon sx={{ color: 'black' }} />
                    </IconButton>
                    <IconButton>
                      <DeleteIcon sx={{ color: 'black' }} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}

            {paginated?.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  No results found
                </TableCell>
              </TableRow>
            )}
            {/* EMPTY */}
            {!loading && !error && paginated?.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  No projects found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* PAGINATION + ROWS PER PAGE */}
      <Box
        sx={{
          mt: 3,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        {/* LEFT SIDE: Rows per page */}
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

        {/* RIGHT SIDE: Pagination */}
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
