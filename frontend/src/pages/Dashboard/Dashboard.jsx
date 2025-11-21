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
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import ArchiveIcon from '@mui/icons-material/Archive';

// Import your JSON file
import dashboardData from '../../utils/dashboard.json';

const ROWS_PER_PAGE = 7;

// Convert true/false → Yes/No + colors
const renderYesNo = (value) => {
  const val = value === true || value === 'true';

  return (
    <Box
      sx={{
        color: val ? 'green' : 'red',
        textAlign: 'center',
        width: '100%',
      }}
    >
      {val ? 'Yes' : 'No'}
    </Box>
  );
};

const Dashboard = () => {
  const [data, setData] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    setData(dashboardData);
  }, []);

  // Filter data by search
  const filtered = data.filter(
    (item) =>
      item.Client_Name.toLowerCase().includes(search.toLowerCase()) ||
      item.Standard.toLowerCase().includes(search.toLowerCase()) ||
      item.Pro_Id?.toLowerCase().includes(search.toLowerCase())
  );

  const totalPages = Math.ceil(filtered.length / ROWS_PER_PAGE);

  const paginated = filtered.slice(
    (page - 1) * ROWS_PER_PAGE,
    page * ROWS_PER_PAGE
  );

  return (
    <Box sx={{ p: 3 }}>
      {/* Top Bar */}
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

      {/* Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead
            sx={{ bgcolor: '#f5f5f5', width: '100%', textAlign: 'center' }}
          >
            <TableRow>
              <TableCell>
                <b>Standard</b>
              </TableCell>
              <TableCell>
                <b>Client Name</b>
              </TableCell>
              <TableCell>
                <b>Product ID</b>
              </TableCell>
              <TableCell>
                <b>Created On</b>
              </TableCell>
              <TableCell>
                <b>TRF Generated</b>
              </TableCell>
              <TableCell>
                <b>CDR Generated</b>
              </TableCell>
              <TableCell>
                <b>Letter Generated</b>
              </TableCell>
              <TableCell>
                <b>Actions</b>
              </TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {paginated.map((row, index) => (
              <TableRow key={index} sx={{ textAlign: 'center', width: '100%' }}>
                <TableCell>{row.Standard}</TableCell>
                <TableCell>{row.Client_Name}</TableCell>
                <TableCell>{row.Pro_Id}</TableCell>
                <TableCell>{row.Proj_Created_On}</TableCell>

                <TableCell>{renderYesNo(row.TRF_Generated)}</TableCell>
                <TableCell>{renderYesNo(row.CDR_Generated)}</TableCell>
                <TableCell>{renderYesNo(row.Letter_Generated)}</TableCell>

                {/* EDIT / DELETE in text */}
                <TableCell>
                  <IconButton>
                    <EditIcon sx={{ color: 'grey' }} />
                  </IconButton>
                  <IconButton>
                    <ArchiveIcon sx={{ color: 'grey' }} />
                  </IconButton>
                  <IconButton>
                    <DeleteIcon sx={{ color: 'grey' }} />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}

            {paginated.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  No results found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <Box
        sx={{
          mt: 3,
          display: 'flex',
          justifyContent: 'center',
          gap: 3,
        }}
      >
        <Button
          variant="contained"
          color="primary"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          Previous
        </Button>

        <Typography sx={{ mt: 1, fontWeight: 'bold' }}>
          Page {page} of {totalPages}
        </Typography>

        <Button
          variant="contained"
          color="primary"
          disabled={page === totalPages}
          onClick={() => setPage(page + 1)}
        >
          Next
        </Button>
      </Box>
    </Box>
  );
};

export default Dashboard;
