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
  Tooltip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { uploadFilesApi } from "../../redux/api/uploadApi";
import {
  getProjectByIdApi,
  deleteUploadedFileApi,
} from "../../redux/api/projectApi";
import { useNavigate, useLocation } from "react-router-dom";

const UploadFilePage = () => {
  const navigate = useNavigate();
  const { state } = useLocation();

  // 🔹 Single source of truth for header info
  const [projectMeta, setProjectMeta] = useState({
    standard: state?.standard || "",
    projectId: state?.projectId || localStorage.getItem("projectId") || "",
    clientName: state?.clientName || "",
    product: state?.product || "",
  });

  const { standard, projectId, clientName, product } = projectMeta;

  /* ---------------- STATE ---------------- */
  const [files, setFiles] = useState({
    sourceFiles: [],
    trfTemplate: { name: "CB scheme TRF template_iec61010_1p.doc" },
    cdrTemplate: { name: "CDR report.xlsx" },
    letterTemplate: {
      name: "Intertek GFT-OP-10a Letter Report template.doc",
    },
    standardDocument: { name: "IEC_61010-1-2010.pdf" },
  });

  const [recentUploads, setRecentUploads] = useState([]);
  const [deletingFile, setDeletingFile] = useState("");
  const [successToast, setSuccessToast] = useState({
    open: false,
    message: "",
  });
  const [errorToast, setErrorToast] = useState({
    open: false,
    message: "",
  });

  const inputRefs = { sourceFiles: useRef(null) };

  const allowedExtensions = [
    "pdf",
    "docx",
    "msg",
    "xls",
    "xlsx",
    "png",
    "jpg",
    "jpeg",
    "eml",
    "doc",
    "txt",
  ];

  /* ---------------- LOAD FILES + FILL META IF NEEDED ---------------- */
  const loadRecentUploads = async () => {
    if (!projectId) return; // no id, nothing to load

    const res = await getProjectByIdApi(projectId);

    const files = res?.uploaded_files || [];
    setRecentUploads([...files].reverse());

    // If we came from refresh (no state), fill in missing header fields from API
    setProjectMeta((prev) => ({
      standard: prev.standard || res?.Standard || "",
      projectId: prev.projectId || res?.Project_Id || "",
      clientName: prev.clientName || res?.Client_Name || "",
      product: prev.product || res?.Product || "",
    }));
  };

  useEffect(() => {
    loadRecentUploads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]); // re-run if projectId source changes

  /* ---------------- UPLOAD ---------------- */
  const handleSourceFileChange = async (e) => {
    const selectedFiles = Array.from(e.target.files);
    const existingNames = recentUploads.map((f) => f.filename.toLowerCase());

    const validFiles = [];
    const unsupportedFiles = [];
    const duplicateFiles = []; // store names

    for (const file of selectedFiles) {
      const ext = file.name.split(".").pop().toLowerCase();

      if (!allowedExtensions.includes(ext)) {
        unsupportedFiles.push(file.name);
        continue;
      }

      if (existingNames.includes(file.name.toLowerCase())) {
        duplicateFiles.push(file.name); // collect duplicates
        continue;
      }

      validFiles.push(file);
    }

    // Unsupported files
    if (unsupportedFiles.length > 0) {
      setErrorToast({
        open: true,
        message: `Unsupported file(s): ${unsupportedFiles.join(", ")}`,
      });
    }

    // Only duplicates selected
    if (!validFiles.length && duplicateFiles.length > 0) {
      setErrorToast({
        open: true,
        message:
          duplicateFiles.length === 1
            ? `Duplicate file already exists: ${duplicateFiles[0]}`
            : `Duplicate files already exist: ${duplicateFiles.join(", ")}`,
      });

      if (inputRefs.sourceFiles.current) {
        inputRefs.sourceFiles.current.value = "";
      }
      return;
    }

    // Nothing valid at all
    if (!validFiles.length) return;

    // Upload valid files
    await uploadFilesApi(projectId, "source_documents", validFiles);
    await loadRecentUploads();

    // Success message with skipped duplicates
    setSuccessToast({
      open: true,
      message:
        duplicateFiles.length > 0
          ? `${validFiles.length} uploaded • ${duplicateFiles.length} skipped (${duplicateFiles.join(
              ", "
            )})`
          : `${validFiles.length} uploaded`,
    });

    if (inputRefs.sourceFiles.current) {
      inputRefs.sourceFiles.current.value = "";
    }
  };

  /* ---------------- DELETE ---------------- */
  const handleDeleteRecentFile = async (fileName) => {
    setDeletingFile(fileName);
    setTimeout(async () => {
      await deleteUploadedFileApi(projectId, fileName);
      await loadRecentUploads();
      setDeletingFile("");
    }, 300);
  };

  const handleGenerateTrf = () => {
    navigate("/report-page");
  };

  /* ---------------- RENDER ROW ---------------- */
  const renderFileRow = (
    label,
    filesArray,
    browseHandler = null,
    helperText = ""
  ) => {
    const showHelper =
      typeof helperText === "string" && helperText.trim().length > 0;

    return (
      <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
        <Box sx={{ minWidth: 220 }}>
          <Typography fontWeight={600}>{label}</Typography>

          {showHelper && (
            <Typography
              variant="caption"
              sx={{ color: "text.secondary", lineHeight: 1.1 }}
            >
              ({helperText})
            </Typography>
          )}
        </Box>

        <Box sx={{ flex: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
          {filesArray.map((file, idx) => (
            <Box
              key={idx}
              sx={{
                bgcolor: "#f0f0f0",
                px: 1,
                py: 0.5,
                borderRadius: 1,
              }}
            >
              <Typography>{file.name}</Typography>
            </Box>
          ))}

          {browseHandler && (
            <>
              <Button variant="outlined" onClick={browseHandler}>
                Upload
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

  /* ---------------- UI ---------------- */
  return (
    <Box display="flex" justifyContent="center" width="100%">
      <Box width="90%" display="flex" gap={3} sx={{ height: "72vh" }}>
        {/* LEFT – PROJECT FILES */}
        <Card
          sx={{
            width: "70%",
            p: 3,
            borderRadius: 2,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box>
            <Box
              sx={{ mb: 3, display: "flex", alignItems: "center", gap: 1 }}
            >
              <Typography variant="h5" fontWeight={600}>
                Project Files
              </Typography>

              <Tooltip
                arrow
                placement="bottom-start"
                title={
                  <Box sx={{ fontSize: "12px", lineHeight: 1.6 }}>
                    <div>
                      <b>Standard:</b> {standard}
                    </div>
                    <div>
                      <b>Project ID:</b> {projectId}
                    </div>
                    <div>
                      <b>Client Name:</b> {clientName}
                    </div>
                    <div>
                      <b>Product:</b> {product}
                    </div>
                  </Box>
                }
              >
                <Typography
                  sx={{
                    fontSize: "15px",
                    color: "text.secondary",
                    cursor: "help",
                  }}
                >
                  ({standard} / {projectId} / {clientName} / {product})
                </Typography>
              </Tooltip>
            </Box>

            <Stack spacing={3}>
              {renderFileRow(
                "Source Documents:",
                files.sourceFiles,
                () => inputRefs.sourceFiles.current.click(),
                "Multiple Files"
              )}

              {renderFileRow(
                "TRF Template:",
                [files.trfTemplate],
                null,
                "Word Input"
              )}
              {renderFileRow(
                "CDR Template:",
                [files.cdrTemplate],
                null,
                "Excel Input"
              )}
              {renderFileRow(
                "Letter Template:",
                [files.letterTemplate],
                null,
                "Word Input"
              )}
              {renderFileRow("Standard Document:", [files.standardDocument])}
            </Stack>
          </Box>

          {/* EXTREME BOTTOM */}
          <Typography
            variant="caption"
            sx={{
              mt: "auto",
              pt: 1,
              fontSize: "11px",
              color: "#d32f2f",
              lineHeight: 1.4,
              textAlign: "left",
            }}
          >
            Supported Documents Format: (.pdf, .docx, .msg, .xls, .xlsx, .png,
            .jpg, .jpeg, .eml, .doc, .txt)
          </Typography>
        </Card>

        {/* RIGHT – RECENT UPLOADS */}
        <Paper
          sx={{
            width: "30%",
            p: 2,
            display: "flex",
            flexDirection: "column",
            border: "1px solid #ddd",
            borderRadius: 2,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Typography variant="h6" fontWeight={600}>
              Recent Uploads
            </Typography>

            <Box
              sx={{
                px: 1.2,
                py: 0.3,
                fontSize: "12px",
                fontWeight: 600,
                bgcolor: "#eef4ff",
                color: "#2f5bea",
                borderRadius: "12px",
                whiteSpace: "nowrap",
              }}
            >
              Uploaded Files: {recentUploads.length}
            </Box>
          </Box>

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
                  filter:
                    deletingFile === file.filename ? "blur(3px)" : "none",
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
            onClick={handleGenerateTrf}
          >
            Generate TRF
          </Button>
        </Paper>
      </Box>

      {/* TOASTS */}
      <Snackbar
        open={successToast.open}
        autoHideDuration={3000}
        onClose={() => setSuccessToast({ open: false, message: "" })}
        anchorOrigin={{ vertical: "top", horizontal: "right" }}
        sx={{ mt: 6 }}   // margin-top
      >
        <Alert
          severity="success"
          variant="filled"
          sx={{ fontSize: "12px" }}
        >
          {successToast.message}
        </Alert>
      </Snackbar>



      <Snackbar
        open={errorToast.open}
        autoHideDuration={3000}
        onClose={() => setErrorToast({ open: false, message: "" })}
        anchorOrigin={{ vertical: "top", horizontal: "right" }}
        sx={{ mt: 6 }}   // margin-top
      >
        <Alert
          severity="error"
          variant="filled"
          sx={{ fontSize: "12px" }}
        >
          {errorToast.message}
        </Alert>
      </Snackbar>


    </Box>
  );
};

export default UploadFilePage;
