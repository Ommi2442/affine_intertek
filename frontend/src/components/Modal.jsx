import React, { useState } from 'react';
import {
  Box,
  Button,
  MenuItem,
  Modal,
  TextField,
  Typography,
  FormControl,
  InputLabel,
  Select
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
    Standard: 'IEC_61010_1',  // Pre-selected default
    Client_Name: '',
    Project_Id: '',
    Product: ''
  });

  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setErrors({ ...errors, [e.target.name]: '' });
  };

  const validate = () => {
    const newErrors = {};
    if (!form.Standard) newErrors.Standard = 'Standard is required';
    if (!form.Client_Name.trim()) newErrors.Client_Name = 'Client Name is required';
    if (!form.Project_Id.trim()) newErrors.Project_Id = 'Project ID is required';
    if (!form.Product.trim()) newErrors.Product = 'Product is required';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const closeOnSubmit = async () => {
    if (!validate()) return;

    try {
      // read email from localStorage (change key if you store it under another name)
      const createdByEmail = localStorage.getItem('email');

      // attach Proj_Created_By to payload
      const payload = {
        ...form,
        Proj_Created_By: createdByEmail
      };

      const res = await createProjectApi(payload);
      console.log("res", res);

      // save returned project id as before
      localStorage.setItem("projectId", res?.data?.Project_Id);

      setForm({
        Standard: 'IEC_61010_1',
        Client_Name: '',
        Project_Id: '',
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

        {/* STANDARD - Pre-selected & ReadOnly */}
        <FormControl fullWidth margin="normal">
          <InputLabel>Standard</InputLabel>
          <Select
            label="Standard"
            name="Standard"
            value={form.Standard}
            readOnly
            open={false}                  // Prevent dropdown opening
            sx={{ pointerEvents: "none" }} // Disable user interaction
          >
            <MenuItem value="IEC_61010_1">IEC 61010-1</MenuItem>
          </Select>
        </FormControl>

        {/* PROJECT ID */}
        <TextField
          fullWidth
          label="Project ID"
          margin="normal"
          name="Project_Id"
          value={form.Project_Id}
          onChange={handleChange}
          error={!!errors.Project_Id}
          helperText={errors.Project_Id}
        />

        {/* CLIENT */}
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
