import React, { useEffect, useState } from "react";
import {
  Box,
  Button,
  MenuItem,
  Modal,
  TextField,
  Typography,
  FormControl,
  InputLabel,
  Select,
  CircularProgress,
  IconButton,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useNavigate } from "react-router-dom";
import { createProjectApi } from "../redux/api/createProjectApi";
import { checkProjectIdApi } from "../redux/api/checkProjectIdApi";

const style = {
  position: "absolute",
  top: "50%",
  left: "50%",
  transform: "translate(-50%, -50%)",
  width: 400,
  bgcolor: "background.paper",
  borderRadius: "10px",
  boxShadow: 24,
  p: 4,
};

export default function BasicModal({ open, handleClose }) {
  const navigate = useNavigate();

  const initialState = {
    Standard: "IEC_61010-1",
    Client_Name: "",
    Project_Id: "",
    Product: "",
  };

  const [form, setForm] = useState(initialState);
  const [errors, setErrors] = useState({});
  const [checkingId, setCheckingId] = useState(false);
  const [projectIdValid, setProjectIdValid] = useState(null);

  useEffect(() => {
    if (open) resetForm();
  }, [open]);

  const resetForm = () => {
    setForm(initialState);
    setErrors({});
    setCheckingId(false);
    setProjectIdValid(null);
  };

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setErrors({ ...errors, [e.target.name]: "" });
    if (e.target.name === "Project_Id") setProjectIdValid(null);
  };

  const handleProjectIdBlur = async () => {
    if (!form.Project_Id.trim()) return;

    try {
      setCheckingId(true);
      const res = await checkProjectIdApi(form.Project_Id);
      setProjectIdValid(!res?.exists);
    } catch (error) {
      console.error("Project ID check failed:", error);
    } finally {
      setCheckingId(false);
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!form.Client_Name.trim()) newErrors.Client_Name = "Required";
    if (!form.Project_Id.trim()) newErrors.Project_Id = "Required";
    if (!form.Product.trim()) newErrors.Product = "Required";

    if (projectIdValid === false) {
      newErrors.Project_Id = "Project ID already used";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const isFormValid =
    form.Client_Name.trim() &&
    form.Project_Id.trim() &&
    form.Product.trim() &&
    projectIdValid !== false;

  /*  FIXED SUBMIT */
  const closeOnSubmit = async () => {
    if (!validate()) return;

    try {
      const createdByEmail = localStorage.getItem("email");
      const userName = localStorage.getItem("name");

      const payload = {
        ...form,
        Proj_Created_By: createdByEmail,
        User_Name: userName
      };

      await createProjectApi(payload);

      resetForm();
      handleClose();

      localStorage.setItem('projectId', form.Project_Id);

      /*  PASS REQUIRED STATE */
      navigate("/create-project", {
        state: {
          standard: form.Standard,
          projectId: form.Project_Id,
          clientName: form.Client_Name,
          product: form.Product,
        },
      });
    } catch (error) {
      console.error("Create Project Failed:", error);
      alert("Error creating project");
    }
  };

  const closeModal = () => {
    resetForm();
    handleClose();
  };

  return (
    <Modal open={open} onClose={() => {}} disableEscapeKeyDown>
      <Box sx={style}>
        {/* CLOSE BUTTON */}
        <IconButton
          sx={{ position: "absolute", top: 10, right: 10 }}
          onClick={closeModal}
        >
          <CloseIcon />
        </IconButton>

        <Typography variant="h6" mb={2}>
          Create Project
        </Typography>

        {/* STANDARD */}
        <FormControl fullWidth margin="normal" required>
          <InputLabel>Standard</InputLabel>
          <Select
            label="Standard"
            name="Standard"
            value={form.Standard}
            readOnly
            open={false}
            sx={{ pointerEvents: "none" }}
          >
            <MenuItem value="IEC_61010-1">IEC_61010-1</MenuItem>
          </Select>
        </FormControl>

        {/* PROJECT ID */}
        <TextField
          fullWidth
          required
          label="Project ID"
          margin="normal"
          name="Project_Id"
          value={form.Project_Id}
          onChange={handleChange}
          onBlur={handleProjectIdBlur}
          error={projectIdValid === false}
          helperText={
            projectIdValid === false
              ? "Project ID already used"
              : projectIdValid === true
              ? <span style={{ color: "green" }}>Project ID available</span>
              : errors.Project_Id
          }
          InputProps={{
            endAdornment: checkingId ? <CircularProgress size={20} /> : null,
          }}
        />

        {/* CLIENT NAME */}
        <TextField
          fullWidth
          required
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
          required
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
          disabled={!isFormValid}
          sx={{
            mt: 2,
            backgroundColor: isFormValid ? "black" : "gray",
            "&:hover": { backgroundColor: isFormValid ? "#333" : "gray" },
          }}
        >
          Submit
        </Button>
      </Box>
    </Modal>
  );
}
