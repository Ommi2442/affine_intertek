import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Button,
  Badge,
} from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import { useNavigate, useLocation } from 'react-router-dom';

const Navbar = ({ signOutClickHandler, openProjectModal }) => {
  const navigate = useNavigate();
  const location = useLocation();

  // Detect active tab
  const currentTab = location.pathname.includes('dashboard')
    ? 'dashboard'
    : 'create';

  const [anchorEl, setAnchorEl] = useState(null);

  const openMenu = (e) => setAnchorEl(e.currentTarget);
  const closeMenu = () => setAnchorEl(null);

  const handleLogout = () => {
    const logintype = localStorage.getItem('logintype');
    if (logintype === 'sso') {
      signOutClickHandler();
    } else {
      sessionStorage.clear();
      localStorage.clear();
      navigate('/');
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
            style={{ width: '120px' }}
          />
        </Box>

        {/* MIDDLE: Tabs */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* Dashboard Tab */}
          <Button
            onClick={() => navigate('/dashboard')}
            sx={{
              textTransform: 'none',
              backgroundColor:
                currentTab === 'dashboard' ? '#E0F3FF' : 'transparent',
              color: currentTab === 'dashboard' ? '#03A9F4' : 'black',
              padding: '8px 20px',
              borderRadius: '8px',
              fontWeight: 600,
              '&:hover': {
                backgroundColor:
                  currentTab === 'dashboard' ? '#E0F3FF' : '#f2f2f2',
              },
            }}
          >
            Dashboard
          </Button>

          {/* Create Project Tab */}
          <Button
            onClick={openProjectModal}
            sx={{
              textTransform: 'none',
              backgroundColor:
                currentTab === 'create' ? '#E0F3FF' : 'transparent',
              color: currentTab === 'create' ? '#03A9F4' : 'black',
              padding: '8px 20px',
              borderRadius: '8px',
              fontWeight: 600,
              '&:hover': {
                backgroundColor:
                  currentTab === 'create' ? '#E0F3FF' : '#f2f2f2',
              },
            }}
          >
            Create Project
          </Button>
        </Box>

        {/* RIGHT: Notification + Profile */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* Notification Icon */}
          <IconButton>
            <Badge badgeContent={0} color="error">
              <NotificationsIcon sx={{ color: 'black', fontSize: 26 }} />
            </Badge>
          </IconButton>

          {/* Profile Icon */}
          <IconButton onClick={openMenu}>
            <AccountCircleIcon sx={{ color: 'black', fontSize: 32 }} />
          </IconButton>

          {/* Dropdown Menu */}
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={closeMenu}
          >
            <MenuItem
              onClick={() => {
                closeMenu();
                handleLogout();
              }}
            >
              Logout
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
