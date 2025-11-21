import React, { useState } from 'react';
import Navbar from '../components/NavBar';
import { Outlet } from 'react-router-dom';
import BasicModal from '../components/Modal';

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

      <div style={{ paddingTop: '80px' }}>
        <Outlet />
      </div>

      {/* Global Create Project Modal */}
      <BasicModal open={openModal} handleClose={handleCloseProjectModal} />
    </>
  );
};

export default MainLayout;
