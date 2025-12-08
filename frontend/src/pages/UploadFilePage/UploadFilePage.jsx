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
  Tooltip,        // ✅ ADD THIS
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { uploadFilesApi } from "../../redux/api/uploadApi";
import {
  getProjectByIdApi,
  deleteUploadedFileApi,
} from "../../redux/api/projectApi";
import { useNavigate } from "react-router-dom";

const UploadFilePage = () => {
  const navigate = useNavigate();
  const projectId = localStorage.getItem("projectId");

  // ✅ KEEP DEFAULT TEMPLATES
  const [files, setFiles] = useState({
    sourceFiles: [],
    trfTemplate: { name: "CB scheme TRF template_iec61010_1p.doc" },
    cdrTemplate: { name: "CDR report.xlsx" },
    letterTemplate: { name: "Intertek GFT-OP-10a Letter Report template.doc" },
    standardDocument: { name: "IEC_61010-1-2010.pdf" },
  });

  const [recentUploads, setRecentUploads] = useState([]);
  const [deletingFile, setDeletingFile] = useState("");

  const [successToast, setSuccessToast] = useState({ open: false, message: "" });
  const [errorToast, setErrorToast] = useState({ open: false, message: "" });

  const inputRefs = {
    sourceFiles: useRef(null),
  };

  const allowedExtensions = [
    "pdf", "docx", "msg", "xls", "xlsx",
    "png", "jpg", "jpeg", "eml", "doc", "txt",
  ];

  // ------------------------------------------------------
  // Load uploaded files (Cosmos DB)
  // ------------------------------------------------------
    const loadRecentUploads = async () => {
      const res = await getProjectByIdApi(projectId);

      // ✅ Show latest uploads first
      const files = res.uploaded_files || [];
      setRecentUploads([...files].reverse());
    };


  useEffect(() => {
    loadRecentUploads();
  }, []);

  const getExistingFileNames = () =>
    recentUploads.map((f) => f.filename.toLowerCase());

  // ------------------------------------------------------
  // AUTO UPLOAD SOURCE FILES (NO DUPLICATES)
  // ------------------------------------------------------
    const handleSourceFileChange = async (e) => {
      const selectedFiles = Array.from(e.target.files);
      const existingNames = getExistingFileNames();

      const validFiles = [];
      let duplicateCount = 0;

      for (const file of selectedFiles) {
        const ext = file.name.split(".").pop().toLowerCase();

        if (!allowedExtensions.includes(ext)) {
          setErrorToast({
            open: true,
            message: `File type not allowed: ${file.name}`,
          });
          continue;
        }

        if (existingNames.includes(file.name.toLowerCase())) {
          duplicateCount++;
          continue;
        }

        validFiles.push(file);
      }

      if (validFiles.length === 0) {
        if (duplicateCount > 0) {
          setErrorToast({
            open: true,
            message: "Duplicate file(s) already uploaded",
          });
        }
        return;
      }

      setFiles((prev) => ({
        ...prev,
        sourceFiles: [...prev.sourceFiles, ...validFiles],
      }));

      await uploadFilesApi(projectId, "source_documents", validFiles);
      await loadRecentUploads();

      let msg = `${validFiles.length} file${validFiles.length > 1 ? "s" : ""} uploaded successfully`;
      if (duplicateCount > 0) {
        msg += ` • ${duplicateCount} duplicate skipped`;
      }

      setSuccessToast({ open: true, message: msg });

      // ✅ CLEAR FORM
      setFiles((prev) => ({
        ...prev,
        sourceFiles: [],
      }));

      if (inputRefs.sourceFiles.current) {
        inputRefs.sourceFiles.current.value = "";
      }
    };


  // ------------------------------------------------------
  // DELETE UPLOADED FILE
  // ------------------------------------------------------
  const handleDeleteRecentFile = async (fileName) => {
    setDeletingFile(fileName);

    setTimeout(async () => {
      await deleteUploadedFileApi(projectId, fileName);

      // ALWAYS reload using same logic (reversed order)
      await loadRecentUploads();

      setDeletingFile("");

      setSuccessToast({
        open: true,
        message: `"${fileName}" deleted`,
      });
    }, 300);
  };


  // ------------------------------------------------------
  // RENDER FILE INPUT ROW (REUSED)
  // ------------------------------------------------------
const renderFileRow = (label, filesArray, browseHandler = null) => {
  const MAX_VISIBLE = 3;
  const visibleFiles = filesArray.slice(0, MAX_VISIBLE);
  const hiddenFiles = filesArray.slice(MAX_VISIBLE);

  return (
    <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
      <Box sx={{ minWidth: 220 }}>
        <Typography fontWeight={600}>{label}</Typography>
      </Box>

      <Box sx={{ flex: 1, display: "flex", flexWrap: "wrap", gap: 1 }}>
        {/* ✅ SHOW MAX 3 FILES */}
        {visibleFiles.map((file, idx) => (
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

            {browseHandler && (
              <IconButton
                size="small"
                onClick={() =>
                  setFiles((prev) => ({
                    ...prev,
                    sourceFiles: prev.sourceFiles.filter(
                      (_, i) => i !== idx
                    ),
                  }))
                }
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
        ))}

        {/* ✅ "+N more" WITH HOVER */}
        {hiddenFiles.length > 0 && (
          <Tooltip
            arrow
            placement="top"
            title={
              <Box>
                {hiddenFiles.map((file, i) => (
                  <Typography
                    key={i}
                    variant="body2"
                    sx={{ whiteSpace: "nowrap" }}
                  >
                    {file.name}
                  </Typography>
                ))}
              </Box>
            }
          >
            <Box
              sx={{
                bgcolor: "#e0e0e0",
                px: 1,
                py: 0.5,
                borderRadius: 1,
                cursor: "pointer",
              }}
            >
              <Typography fontWeight={600}>
                +{hiddenFiles.length} more
              </Typography>
            </Box>
          </Tooltip>
        )}

        {/* ✅ BROWSE BUTTON */}
        {browseHandler && (
          <>
            <Button variant="outlined" onClick={browseHandler}>
              Browse
            </Button>
            <input
              hidden
              type="file"
              multiple
              ref={inputRefs.sourceFiles}
              onChange={handleSourceFileChange}
            />
          </>
        )}
      </Box>
    </Box>
  );
};


  return (
    <Box display="flex" justifyContent="center" width="100%">
      <Box width="90%" display="flex" gap={3} sx={{ height: "60vh" }}>
        {/* LEFT – PROJECT FILES */}
        <Card sx={{ width: "70%", p: 3, height: "97%", overflowY: "auto", borderRadius: 2 }}>
          <Typography variant="h5" fontWeight={600} mb={3}>
            Project Files
          </Typography>

          <Stack spacing={3}>
            {renderFileRow(
              "Source Documents:",
              files.sourceFiles,
              () => inputRefs.sourceFiles.current.click()
            )}

            {renderFileRow("TRF Template:", [files.trfTemplate], null, true)}
            {renderFileRow("CDR Template:", [files.cdrTemplate], null, true)}
            {renderFileRow("Letter Template:", [files.letterTemplate], null, true)}
            {renderFileRow("Standard Document:", [files.standardDocument], null, true)}
          </Stack>
        </Card>

        {/* RIGHT – RECENT UPLOADS */}
        <Paper
          sx={{
            width: "30%",
            p: 2,
            height: "100%",
            display: "flex",
            flexDirection: "column",
            border: "1px solid #ddd",
            borderRadius: 2,
          }}
        >
          <Typography variant="h6" fontWeight={600}>
            Recent Uploads
          </Typography>

          <Box sx={{ flex: 1, overflowY: "auto", mt: 2 }}>
            {recentUploads.map((file, idx) => (
              <Box
                key={idx}
                sx={{
                  bgcolor: "#f7f7f7",
                  p: 1,
                  mb: 1,
                  borderRadius: 1,
                  display: "flex",
                  justifyContent: "space-between",
                  filter: deletingFile === file.filename ? "blur(3px)" : "none",
                  opacity: deletingFile === file.filename ? 0 : 1,
                }}
              >
                <Typography noWrap>{file.filename}</Typography>
                <IconButton
                  size="small"
                  onClick={() => handleDeleteRecentFile(file.filename)}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}
          </Box>

          <Button
            variant="contained"
            sx={{ mt: 2, backgroundColor: "#0d99ff" }}
            onClick={() => navigate("/report-page")}
          >
            Generate TRF
          </Button>
        </Paper>
      </Box>

      {/* SUCCESS TOAST */}
      <Snackbar
        open={successToast.open}
        autoHideDuration={2200}
        onClose={() => setSuccessToast({ open: false, message: "" })}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity="success" variant="filled">
          {successToast.message}
        </Alert>
      </Snackbar>

      {/* ERROR TOAST */}
      <Snackbar
        open={errorToast.open}
        autoHideDuration={2500}
        onClose={() => setErrorToast({ open: false, message: "" })}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity="error" variant="filled">
          {errorToast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default UploadFilePage;
