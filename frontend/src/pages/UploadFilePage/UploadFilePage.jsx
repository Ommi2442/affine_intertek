import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  Button,
  Typography,
  Stack,
  Paper,
  Card,
  IconButton,
  Snackbar,
  Alert,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { uploadFilesApi } from "../../redux/api/uploadApi";
import {
  getProjectByIdApi,
  deleteUploadedFileApi,
} from "../../redux/api/projectApi";

const UploadFilePage = () => {
  const [files, setFiles] = useState({
    sourceFiles: [],
    trfTemplate: { name: "CB scheme TRF template_iec61010_1p.doc" },
    cdrTemplate: { name: "CDR report.xlsx" },
    letterTemplate: { name: "Intertek GFT-OP-10a Letter Report template.doc" },
    standardDocument: { name: "IEC_61010-1-2010.pdf" },
  });

  const [recentUploads, setRecentUploads] = useState([]);
  const [deletingFile, setDeletingFile] = useState("");

  const [deleteToast, setDeleteToast] = useState({
    open: false,
    message: "",
  });

  const allowedExtensions = [
  "pdf", "docx", "msg", "xls", "xlsx",
  "png", "jpg", "jpeg", "eml", "doc", "txt"
  ];

  const [errorToast, setErrorToast] = useState({
  open: false,
  message: ""
  });



  const projectId = localStorage.getItem("projectId");

  const inputRefs = {
    sourceFiles: useRef(null),
    trfTemplate: useRef(null),
    cdrTemplate: useRef(null),
    letterTemplate: useRef(null),
    standardDocument: useRef(null),
  };

  // ------------------------------------------------------
  // Load Recent Uploaded Files
  // ------------------------------------------------------
  const loadRecentUploads = async () => {
    const res = await getProjectByIdApi(projectId);
    setRecentUploads(res.uploaded_files || []);
  };

  useEffect(() => {
    loadRecentUploads();
  }, []);

  // ------------------------------------------------------
  // Handle local file change
  // ------------------------------------------------------
  const handleFileChange = (e, key, multiple = false, disabled = false) => {
    if (disabled) return;

    const chosenFiles = Array.from(e.target.files);
    const validFiles = [];

    for (const file of chosenFiles) {
      const ext = file.name.split(".").pop().toLowerCase();

      if (allowedExtensions.includes(ext)) {
        validFiles.push(file);
      } else {
        setErrorToast({
          open: true,
          message: `File type not allowed: ${file.name}`
        });
      }
    }

    if (validFiles.length === 0) return;

    setFiles(prev => ({
      ...prev,
      [key]: multiple ? [...prev[key], ...validFiles] : validFiles[0]
    }));
  };


  // ------------------------------------------------------
  // DELETE uploaded file with animation + toast
  // ------------------------------------------------------
  const handleDeleteRecentFile = async (fileName) => {
    try {
      setDeletingFile(fileName); // trigger blur animation

      setTimeout(async () => {
        const res = await deleteUploadedFileApi(projectId, fileName);

        setRecentUploads(res.uploaded_files || []);

        setDeletingFile("");

        setDeleteToast({
          open: true,
          message: `"${fileName}" deleted`,
        });
      }, 300);
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  // ------------------------------------------------------
  // Upload left-side source files
  // ------------------------------------------------------
  const handleGenerate = async () => {
    if (files.sourceFiles.length > 0) {
      await uploadFilesApi(projectId, "source_documents", files.sourceFiles);
      loadRecentUploads();
    }
  };

  // ------------------------------------------------------
  // Render file input row (left side unchanged)
  // ------------------------------------------------------
  const renderFileInput = (label, key, description, multiple = false, disabled = false) => {
    const currentFiles = multiple ? files[key] : files[key] ? [files[key]] : [];

    const showUploadButton =
      key === "sourceFiles" ? true : !disabled && currentFiles.length === 0;

    return (
      <Box sx={{ display: "flex", alignItems: "center", width: "100%", gap: 2 }}>
        <Box sx={{ minWidth: "220px" }}>
          <Typography sx={{ fontWeight: 600 }}>{label}</Typography>
          {description && (
            <Typography sx={{ fontSize: "14px", color: "gray" }}>
              {description}
            </Typography>
          )}
        </Box>

        <Box sx={{ display: "flex", flexWrap: "wrap", flex: 1, gap: 1 }}>
          {/* Already selected files */}
          {currentFiles.map((file, idx) => (
            <Box
              key={idx}
              sx={{
                bgcolor: "#f0f0f0",
                px: 1,
                py: 0.5,
                borderRadius: 1,
                display: "flex",
                alignItems: "center",
                gap: 1,
              }}
            >
              <Typography>{file.name}</Typography>

              {key === "sourceFiles" && (
                <IconButton
                  size="small"
                  onClick={() => {
                    setFiles((prev) => ({
                      ...prev,
                      sourceFiles: prev.sourceFiles.filter((_, i) => i !== idx),
                    }));
                  }}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              )}
            </Box>
          ))}

          {/* Upload Button */}
          {showUploadButton && (
            <Button
              variant="outlined"
              disabled={disabled}
              onClick={() => inputRefs[key].current.click()}
            >
              Upload
            </Button>
          )}

          {/* Hidden Input */}
          <input
            type="file"
            hidden
            ref={inputRefs[key]}
            multiple={multiple}
            disabled={disabled}
            onChange={(e) => handleFileChange(e, key, multiple, disabled)}
          />
        </Box>
      </Box>
    );
  };

  return (
    <Box display="flex" justifyContent="center" width="100%">
      <Card sx={{ width: "90%", p: 3 }}>
        <Typography variant="h5" fontWeight={600} mb={3}>
          Project Files
        </Typography>

        <Box display="flex" gap={3}>
          {/* LEFT SIDE - UNCHANGED */}
          <Box sx={{ width: "70%" }}>
            <Stack spacing={3}>
              {renderFileInput("Source Documents:", "sourceFiles", "(Multiple Files)", true)}

              {renderFileInput("TRF Template:", "trfTemplate", "(Word Input)", false, true)}
              {renderFileInput("CDR Template:", "cdrTemplate", "(Excel Input)", false, true)}
              {renderFileInput("Letter Template:", "letterTemplate", "(Word Input)", false, true)}
              {renderFileInput("Standard Document:", "standardDocument", "", false, true)}

              {/* GENERATE BUTTON AT BOTTOM */}
              <Button
                variant="contained"
                sx={{ mt: 3, backgroundColor: "#0d99ff" }}
                onClick={handleGenerate}
              >
                Upload Files & Generate
              </Button>
            </Stack>
          </Box>

          {/* RIGHT SIDE – RECENT UPLOADS */}
          <Paper
            elevation={2}
            sx={{
              width: "30%",
              p: 2,
              height: "420px",
              display: "flex",
              flexDirection: "column",
              borderRadius: 2,
              border: "1px solid #ddd",
            }}
          >
            <Typography variant="h6" fontWeight={600}>
              Recent Uploads
            </Typography>

            <Box
              sx={{
                overflowY: "auto",
                mt: 2,
                pr: 1,
                flex: 1,
              }}
            >
              {recentUploads.map((file, index) => (
                <Box
                  key={index}
                  sx={{
                    bgcolor: "#f7f7f7",
                    p: 1,
                    borderRadius: 1,
                    mb: 1,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    transition: "all 0.3s ease",
                    filter: deletingFile === file.filename ? "blur(3px)" : "none",
                    opacity: deletingFile === file.filename ? 0 : 1,
                  }}
                >
                  <Typography
                    sx={{
                      maxWidth: "200px",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                    title={file.filename}
                  >
                    {file.filename}
                  </Typography>

                  <IconButton size="small" onClick={() => handleDeleteRecentFile(file.filename)}>
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Box>
              ))}
            </Box>
          </Paper>
        </Box>

        {/* Toast Popup */}
        <Snackbar
          open={deleteToast.open}
          autoHideDuration={1800}
          onClose={() => setDeleteToast({ open: false, message: "" })}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        >
          <Alert
            severity="success"
            sx={{
              bgcolor: "#28c76f",
              color: "#fff",
              borderRadius: "10px",
              px: 2,
              py: 1,
              boxShadow: "0px 3px 10px rgba(0,0,0,0.2)",
            }}
          >
            {deleteToast.message}
          </Alert>
        </Snackbar>

        <Snackbar
          open={errorToast.open}
          autoHideDuration={2500}
          onClose={() => setErrorToast({ open: false, message: "" })}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        >
          <Alert
            severity="error"
            variant="filled"
            sx={{
              bgcolor: "#ff4d4f",
              color: "#fff",
              borderRadius: "10px",
              px: 2,
              py: 1,
              boxShadow: "0px 3px 10px rgba(0,0,0,0.25)",
            }}
          >
            {errorToast.message}
          </Alert>
        </Snackbar>


      </Card>
    </Box>
  );
};

export default UploadFilePage;
