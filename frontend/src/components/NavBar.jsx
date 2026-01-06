import React, { useEffect, useState } from 'react';
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
import { useMsal } from '@azure/msal-react';

const Navbar = ({ signOutClickHandler, openProjectModal }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { instance } = useMsal();

  // Detect active tab
  const currentTab = location.pathname.includes('dashboard')
    ? 'dashboard'
    : 'create';

  const [anchorEl, setAnchorEl] = useState(null);
  const [userName, setUserName] = useState(null);
  const user = userName ? userName.split(' ') : [''];

  const openMenu = (e) => setAnchorEl(e.currentTarget);
  const closeMenu = () => setAnchorEl(null);

  const handleLogout = () => {
    // Clear local storage (your custom app tokens)
    localStorage.clear();
    sessionStorage.clear();

    // Force MSAL to clear account state
    instance.logoutRedirect({
      postLogoutRedirectUri: 'https://red-cliff-09de2ee0f.3.azurestaticapps.net/',
      authority: `https://login.microsoftonline.com/common/oauth2/v2.0/logout`,
    });

    // navigate('/');
  };

  useEffect(() => {
    const storedName = localStorage.getItem('name');
    setUserName(storedName || '');
  }, []);

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
          <Typography sx={{ color: 'black', fontWeight: 600 }}>
            {' '}
            {user[0] || ''}
          </Typography>
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
