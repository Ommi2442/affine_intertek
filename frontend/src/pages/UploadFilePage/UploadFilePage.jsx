import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Button,
  Typography,
  Stack,
  Paper,
  Card,
  IconButton,
  LinearProgress
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CloseIcon from '@mui/icons-material/Close';
import { useDispatch, useSelector } from 'react-redux';
import { generateTrfRequest } from '../../redux/features/generateTrf/generateTrfSlice';
import JSONData from '../../utils/pta_final.json';
import './UploadFilePage.css';
import { uploadFilesApi } from "../../redux/api/uploadApi";

const UploadFilePage = () => {

  // ------------------ PROGRESS BAR STATES ------------------
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(false);

  const startProgressSimulation = () => {
    setShowProgress(true);
    setUploadProgress(0);

    const interval = setInterval(() => {
      setUploadProgress(prev => {
        // Stop auto-progress at 95% until final uploads finish
        if (prev >= 95) {
          clearInterval(interval);
          return prev;
        }
        return prev + Math.random() * 10; // smooth incremental progress
      });
    }, 600);
  };

  const dispatch = useDispatch();

  const { trfData, loading, error } = useSelector((state) => state.trf);
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (trfData) {
      setIsSubmitting(false);
      navigate('/report-page');
    }
  }, [trfData]);

  useEffect(() => {
    if (error) {
      setIsSubmitting(false);
    }
  }, [error]);

  const [files, setFiles] = useState({
    sourceFiles: [],
    trfTemplate: { name: 'CB scheme TRF Template iec6101_1.docx' },
    cdrTemplate: { name: 'CDR Report Template.xlsx' },
    letterTemplate: { name: 'intertek gft OP 10 letter report.docx' },
    standardDocument: { name: 'IEC 61010-1-2010.pdf' }
  });

  const inputRefs = {
    sourceFiles: useRef(null),
    trfTemplate: useRef(null),
    cdrTemplate: useRef(null),
    letterTemplate: useRef(null),
    standardDocument: useRef(null),
  };

  // ------------------- Handle File Selection -------------------
  const handleFileChange = (e, key, multiple = false) => {
    const chosenFiles = Array.from(e.target.files);

    setFiles(prev => ({
      ...prev,
      [key]: multiple ? [...prev[key], ...chosenFiles] : chosenFiles[0] || null
    }));

    console.log(`Files selected for ${key}:`, chosenFiles.map(f => f.name));
  };

  // ------------------- Remove File -------------------
  const handleDeleteFile = (key, index = null) => {
    if (key === "sourceFiles" && index !== null) {
      setFiles(prev => ({
        ...prev,
        sourceFiles: prev.sourceFiles.filter((_, i) => i !== index),
      }));
    } else {
      setFiles(prev => ({ ...prev, [key]: null }));
    }
  };

  // ------------------- Upload Handler -------------------
  const handleGenerate = async () => {
    console.log("FINAL FILE LIST:", files);
    const projectId = localStorage.getItem("projectId");

    // 🔵 Start UI progress bar
    startProgressSimulation();

    try {
      // 1) Upload SOURCE FILES
      if (files.sourceFiles.length > 0) {
        const res = await uploadFilesApi(
          projectId,
          "source_documents",
          files.sourceFiles
        );
        console.log("Source docs uploaded:", res);
      }

      // 2) Upload SINGLE FILES
      const singleFileMap = [
        { key: "trf_template", fileKey: "trfTemplate" },
        { key: "cdr_template", fileKey: "cdrTemplate" },
        { key: "letter_template", fileKey: "letterTemplate" },
        { key: "standard_documents", fileKey: "standardDocument" }
      ];

      for (const entry of singleFileMap) {
        const fileObj = files[entry.fileKey];

        if (fileObj instanceof File) {
          const res = await uploadFilesApi(
            projectId,
            entry.key,
            [fileObj]
          );
          console.log(`${entry.key} uploaded:`, res);
        }
      }

      // 🟢 Finish progress
      setUploadProgress(100);

      setTimeout(() => {
        setShowProgress(false);
        setUploadProgress(0);
      }, 1200);

      navigate("/report-page");

    } catch (err) {
      console.error("Upload failed:", err);
      alert("Upload failed! Check console.");

      setShowProgress(false);
      setUploadProgress(0);
    }
  };

  // ------------------- Render File Input UI -------------------
  const renderFileInput = (label, key, description, multiple = false) => {
    const currentFiles = multiple ? files[key] : files[key] ? [files[key]] : [];
    const showUploadButton = currentFiles.length === 0;

    return (
      <Box sx={{ display: 'flex', width: '100%', alignItems: 'center', gap: 1 }}>

        <Box sx={{ minWidth: '220px' }}>
          <Typography sx={{ fontWeight: 600 }}>{label}</Typography>
          {description && <Typography sx={{ color: "gray", fontSize: "14px" }}>{description}</Typography>}
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, flex: 1 }}>

          {currentFiles.map((file, idx) => (
            <Box key={idx}
              sx={{
                display: 'flex',
                alignItems: 'center',
                bgcolor: '#f0f0f0',
                px: 1,
                py: 0.5,
                borderRadius: 1,
                gap: 0.5,
              }}>
              <Typography variant="body2">{file.name}</Typography>
              <IconButton size="small" onClick={() => handleDeleteFile(key, idx)}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}

          {showUploadButton && (
            <Button variant="outlined" onClick={() => inputRefs[key].current.click()}>
              Upload
            </Button>
          )}

          <input
            type="file"
            ref={inputRefs[key]}
            hidden
            multiple={multiple}
            onChange={(e) => handleFileChange(e, key, multiple)}
          />
        </Box>
      </Box>
    );
  };

  return (
    <div style={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
      <Card sx={{ width: '80%', p: 3 }}>

        <Typography variant="h5" fontWeight={600} mb={3}>
          Project Files
        </Typography>

        {/* ---------- PROGRESS BAR UI ---------- */}
        {showProgress && (
          <Box sx={{ width: "100%", mb: 3 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Uploading files... Please wait
            </Typography>

            <LinearProgress
              variant="determinate"
              value={uploadProgress}
              sx={{ height: 12, borderRadius: 2 }}
            />

            <Typography variant="body2" sx={{ mt: 1 }}>
              {Math.round(uploadProgress)}%
            </Typography>
          </Box>
        )}

        {/* ---------- LEFT SIDE UPLOAD INPUTS ---------- */}
        <Box sx={{ display: 'flex', gap: 3 }}>
          <Box sx={{ width: '70%' }}>
            <Stack spacing={3}>
              {renderFileInput("Source Documents:", "sourceFiles", "(Multiple Files)", true)}
              {renderFileInput("TRF Template:", "trfTemplate", "(Word Input)")}
              {renderFileInput("CDR Template:", "cdrTemplate", "(Excel Input)")}
              {renderFileInput("Letter Template:", "letterTemplate", "(Word Input)")}
              {renderFileInput("Standard Document:", "standardDocument")}

              <Button
                variant="contained"
                onClick={handleGenerate}
                sx={{ mt: 3, backgroundColor: '#0d99ff' }}>
                Upload Files & Generate TRF
              </Button>
            </Stack>
          </Box>

          {/* ---------- RIGHT SIDE RECENT UPLOADS ---------- */}
          <Paper elevation={1} sx={{ width: '30%', p: 2 }}>
            <Typography variant="h6" fontWeight={500}>Recent Uploads</Typography>
            <Typography variant="body2" sx={{ color: "gray" }}>
              (No recent uploads yet)
            </Typography>
          </Paper>
        </Box>

      </Card>
    </div>
  );
};

export default UploadFilePage;
