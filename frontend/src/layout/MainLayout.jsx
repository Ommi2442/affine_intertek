import React, { useState } from 'react';
import Navbar from '../components/NavBar';
import { Outlet } from 'react-router-dom';
import BasicModal from '../components/Modal';
import AppBreadcrumbs from '../components/AppBreadCrumbs';
import { Box } from '@mui/material';

const MainLayout = () => {
  const [openModal, setOpenModal] = useState(false);

  const handleOpenProjectModal = () => {
    setOpenModal(true);
  };

  const handleCloseProjectModal = () => {
    setOpenModal(false);
  };

  return (
    <>
      <Navbar openProjectModal={handleOpenProjectModal} />

      <Box style={{ paddingTop: '80px' }}>
        <Box sx={{ pt: 3, pl: '2%' }}>
          <AppBreadcrumbs />
        </Box>
        <Box sx={{ pl: '2%', pr: '2%' }}>
          <Outlet />
        </Box>
      </Box>

      {/* Global Create Project Modal */}
      <BasicModal open={openModal} handleClose={handleCloseProjectModal} />
    </>
  );
};

export default MainLayout;
