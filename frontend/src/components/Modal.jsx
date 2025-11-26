import React, { useEffect, useState } from 'react';
import { Box, Button, Modal, TextField, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { createProjectApi } from '../redux/api/createProjectApi';

const style = {
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: 400,
  bgcolor: 'background.paper',
  borderRadius: '10px',
  boxShadow: 24,
  p: 4,
};

export default function BasicModal({ open, handleClose }) {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    standard: '',
    clientName: '',
    product: '',
    projectId: '',
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const closeOnSubmit = async () => {
    try {
      // Call API and wait for completion
      //await createProjectApi(form);
      handleClose();
      navigate('/create-project');
    } catch (err) {
      console.error('Create Project Failed', err);
      alert('Error creating project');
    }
  };

  return (
    <>
      <Modal open={open} onClose={handleClose}>
        <Box sx={style}>
          <Typography variant="h6" mb={2}>
            Create Project
          </Typography>

          <TextField
            fullWidth
            label="Standard"
            margin="normal"
            onChange={handleChange}
          />
          <TextField
            fullWidth
            label="Client Name"
            margin="normal"
            onChange={handleChange}
          />
          <TextField
            fullWidth
            label="Product"
            margin="normal"
            onChange={handleChange}
          />
          <TextField
            fullWidth
            label="Project ID"
            margin="normal"
            onChange={handleChange}
          />

          <Button
            onClick={closeOnSubmit}
            variant="contained"
            fullWidth
            sx={{
              mt: 2,
              backgroundColor: 'black',
              '&:hover': { backgroundColor: '#333' },
            }}
          >
            Submit
          </Button>
        </Box>
      </Modal>
    </>
  );
}
