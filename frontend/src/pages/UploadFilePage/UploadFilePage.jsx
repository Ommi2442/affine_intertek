import React, { useState, useRef } from 'react';
import {
  Box,
  Button,
  Typography,
  Stack,
  Paper,
  Card,
  IconButton,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CloseIcon from '@mui/icons-material/Close';

import uploadService from "./UploadService";

const UploadFilePage = () => {

  // const [projectId] = useState("PRJ_000018");


  const [files, setFiles] = useState({
    sourceFiles: [],           // multiple
    trfTemplate: { name: 'CB scheme TRF Template iec6101_1.docx' },
    cdrTemplate: { name: 'CDR Report Template.xlsx' },
    letterTemplate: { name: 'intertek gft OP 10 letter report.docx' },
    standardDocument: { name: 'IEC 61010-1-2010.pdf' }
  });

  const Navigate = useNavigate();

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

  // ------------------- Handle Remove -------------------
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

  // ------------------- Handle Upload -------------------
  const handleGenerate = async () => {
    console.log("FINAL FILE LIST:", files);
    const projectId = localStorage.getItem("projectId");


    try {
      // 1) Upload MULTIPLE SOURCE FILES
      if (files.sourceFiles.length > 0) {
        const res = await uploadService.uploadFiles(
          projectId,
          "source_documents",
          files.sourceFiles
        );
        console.log("Source docs uploaded:", res);
      }

      // 2) Upload SINGLE FILE categories
      const singleFileMap = [
        { key: "trf_template", fileKey: "trfTemplate" },
        { key: "cdr_template", fileKey: "cdrTemplate" },
        { key: "letter_template", fileKey: "letterTemplate" },
        { key: "standard_documents", fileKey: "standardDocument" }
      ];

      for (const entry of singleFileMap) {
        const fileObj = files[entry.fileKey];

        if (fileObj instanceof File) {
          const res = await uploadService.uploadFiles(
            projectId,
            entry.key,
            [fileObj]
          );
          
          console.log(`${entry.key} uploaded:`, res);
        }
      }

      // Finally navigate after all uploads complete
      Navigate("/report-page");

    } catch (err) {
      console.error("Upload failed:", err);
      alert("Upload failed! Check console.");
    }
  };

  // ------------------- Render File Input Section -------------------
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

          {/* Upload Button */}
          {showUploadButton && (
            <Button variant="outlined" onClick={() => inputRefs[key].current.click()}>
              Upload
            </Button>
          )}

          {/* Hidden Input */}
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

          <Paper elevation={1} sx={{ width: '30%', p: 2 }}>
            <Typography variant="h6" fontWeight={500}>Recent Uploads</Typography>
            <Typography variant="body2" sx={{ color: "gray" }}>(No recent uploads yet)</Typography>
          </Paper>
        </Box>

      </Card>
    </div>
  );
};

export default UploadFilePage;
