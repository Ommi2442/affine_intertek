import React, { useState } from 'react';
import {
  Box,
  Button,
  MenuItem,
  Modal,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
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
    Project_Name: '',
    Product: ''
  });

  const [errors, setErrors] = useState({});

  // Handle input change
  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });

    // Clear error while typing
    setErrors({ ...errors, [e.target.name]: '' });
  };

  // Validate fields
  const validate = () => {
    const newErrors = {};

    if (!form.Standard) newErrors.Standard = 'Standard is required';
    if (!form.Client_Name.trim()) newErrors.Client_Name = 'Client Name is required';
    if (!form.Project_Name.trim()) newErrors.Project_Name = 'Project_Name is required';
    if (!form.Product.trim()) newErrors.Product = 'Product is required';

    setErrors(newErrors);

    return Object.keys(newErrors).length === 0; // true if no errors
  };

  // Submit handler
  const closeOnSubmit = async () => {
    if (!validate()) return; // Stop if validation fails

    let res;

    try {
      res = await createProjectApi(form);
      console.log("res", res);

      localStorage.setItem("projectId", res?.data?.Project_Id);

      // Clear form after successful submit
      setForm({
        Standard: '',
        Client_Name: '',
        Project_Name: '',
        Product: ''
      });

      handleClose(); 
      navigate("/create-project");

    } catch (err) {
      console.error("Create Project Failed", err);
      alert("Error creating project");
    }
  };

  return (
    <Modal open={open} onClose={handleClose}>
      <Box sx={style}>
        <Typography variant="h6" mb={2}>
          Create Project
        </Typography>

        {/* STANDARD */}
        <TextField
          fullWidth
          select
          label="Standard"
          margin="normal"
          name="Standard"
          value={form.Standard}
          onChange={handleChange}
          error={!!errors.Standard}
          helperText={errors.Standard}
        >
          <MenuItem value="">
            <em>Select Standard</em>
          </MenuItem>
          <MenuItem value="IEC_61010_1">IEC 61010-1</MenuItem>
          <MenuItem value="IEC_61010_2">IEC 61010-2</MenuItem>
          <MenuItem value="IEC_61010_3">IEC 61010-3</MenuItem>
        </TextField>

        {/* PROJECT NAME */}
        <TextField
          fullWidth
          label="Project Name"
          margin="normal"
          name="Project_Name"
          value={form.Project_Name}
          onChange={handleChange}
          error={!!errors.Project_Name}
          helperText={errors.Project_Name}
        />

        {/* CLIENT NAME */}
        <TextField
          fullWidth
          label="Client Name"
          margin="normal"
          name="Client_Name"
          value={form.Client_Name}
          onChange={handleChange}
          error={!!errors.Client_Name}
          helperText={errors.Client_Name}
        />

        {/* PRODUCT */}
        <TextField
          fullWidth
          label="Product"
          margin="normal"
          name="Product"
          value={form.Product}
          onChange={handleChange}
          error={!!errors.Product}
          helperText={errors.Product}
        />

        {/* SUBMIT */}
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
  );
}
