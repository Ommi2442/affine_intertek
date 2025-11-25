import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Select,
  MenuItem,
  IconButton,
} from '@mui/material';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import { useNavigate } from 'react-router-dom';

const Navbar = ({ signOutClickHandler }) => {
  const [selectedItem, setSelectedItem] = useState('Create');
  const Navigate = useNavigate();
  const handleChange = (event) => {
    setSelectedItem(event.target.value);
  };

  const customLogout = () => {
    const logintype = localStorage.getItem('logintype');
    if (logintype === 'sso') {
      signOutClickHandler();
    } else {
      sessionStorage.clear();
      localStorage.clear();
      Navigate('/');
    }
  };

  return (
    <AppBar
      position="fixed"
      sx={{
        backgroundColor: '#fff',
        boxShadow: 2,
        width: '100%',
        zIndex: 1200,
      }}
    >
      <Toolbar sx={{ display: 'flex', justifyContent: 'space-between' }}>
        {/* LEFT: Logo */}
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <img
            src="/images/intertek_logo.svg"
            alt="Logo"
            style={{ width: '50%' }}
          />
        </Box>

        {/* MIDDLE: Dashboard Display + Select */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h6" sx={{ color: 'black', fontWeight: 600 }}>
            {selectedItem}
          </Typography>

          <Select
            value={selectedItem}
            onChange={handleChange}
            size="small"
            sx={{
              backgroundColor: '#f5f5f5',
              borderRadius: 1,
              minWidth: 150,
            }}
          >
            <MenuItem value="Create">Create</MenuItem>
            <MenuItem value="Dashboard">Dashboard</MenuItem>
            <MenuItem value="Users">Users</MenuItem>
            <MenuItem value="Analytics">Analytics</MenuItem>
          </Select>
        </Box>

        {/* RIGHT: Account Icon */}
        <IconButton>
          <AccountCircleIcon sx={{ color: 'black' }} />
        </IconButton>
        <div>
          <button onClick={customLogout}>Logout</button>
        </div>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
