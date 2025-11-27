import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  MenuItem,
  Modal,
  Select,
  TextField,
  Typography,
} from '@mui/material';
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
    Standard: '',
    Client_Name: '',
    Product: '',
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const closeOnSubmit = async () => {
    try {
      // Call API and wait for completion
      await createProjectApi(form);
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
            select
            label="Standard"
            margin="normal"
            name="Standard"
            onChange={handleChange}
            defaultValue=""
          >
            <MenuItem value="">
              <em>Select Standard</em>
            </MenuItem>

            <MenuItem value="IEC_61010_1">IEC 61010-1</MenuItem>
            <MenuItem value="IEC_61010_2">IEC 61010-2</MenuItem>
            <MenuItem value="IEC_61010_3">IEC 61010-3</MenuItem>
          </TextField>

          <TextField
            fullWidth
            label="Client Name"
            margin="normal"
            name="Client_Name"
            onChange={handleChange}
          />
          <TextField
            fullWidth
            label="Product"
            margin="normal"
            name="Product"
            onChange={handleChange}
          />
          {/* <TextField
            fullWidth
            label="Project ID"
            margin="normal"
            onChange={handleChange}
          /> */}

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
