import React, { useState } from 'react';
import { Box, Button, Typography, Stack, Paper, Card } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const UploadFilePage = () => {
  const [files, setFiles] = useState({
    sourceFile: null,
    trfTemplate: null,
    cdrTemplate: null,
    letterTemplate: null,
    standardDocument: null,
  });

  const Navigate = useNavigate();

  const handleFileChange = (e, key) => {
    setFiles({
      ...files,
      [key]: e.target.files[0],
    });
  };

  const handleGenerate = () => {
    Navigate('/report-page');
    console.log('Uploaded Files:', files);
  };

  return (
    <div
      style={{
        height: '100vh',
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f4f6f8',
      }}
    >
      {/* Card stays perfectly centered */}
      <Card
        sx={{
          width: '70%',
          p: 3,
          borderRadius: 2,
          alignItems: 'center',
        }}
      >
        {/* Header */}
        <Typography variant="h5" fontWeight={600} mb={3}>
          Project Files
        </Typography>

        {/* Main Layout */}
        <Box sx={{ display: 'flex', gap: 3 }}>
          {/* Left Section */}
          <Box sx={{ width: '70%' }}>
            <Typography variant="h6" mb={2} fontWeight={500}>
              Upload Source Files
            </Typography>

            <Stack spacing={2}>
              {/* Source File */}
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography sx={{ width: '50%' }}>
                  Source Documents:
                  <div>(multiple Files)</div>
                </Typography>
                <Button variant="outlined" component="label" fullWidth>
                  {files.sourceFile
                    ? files.sourceFile.name
                    : 'Upload Source File'}
                  <input
                    type="file"
                    hidden
                    onChange={(e) => handleFileChange(e, 'sourceFile')}
                  />
                </Button>
              </Box>

              {/* TRF Template */}
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography sx={{ width: '50%' }}>
                  TRF Template:
                  <div>(word input)</div>
                </Typography>
                <Button variant="outlined" component="label" fullWidth>
                  {files.trfTemplate
                    ? files.trfTemplate.name
                    : 'Upload TRF Template'}
                  <input
                    type="file"
                    hidden
                    onChange={(e) => handleFileChange(e, 'trfTemplate')}
                  />
                </Button>
              </Box>

              {/* CDR Template */}
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography sx={{ width: '50%' }}>
                  CDR Template:<div>(Excel Input)</div>{' '}
                </Typography>
                <Button variant="outlined" component="label" fullWidth>
                  {files.cdrTemplate
                    ? files.cdrTemplate.name
                    : 'Upload CDR Template'}
                  <input
                    type="file"
                    hidden
                    onChange={(e) => handleFileChange(e, 'cdrTemplate')}
                  />
                </Button>
              </Box>

              {/* Letter Template */}
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography sx={{ width: '50%' }}>
                  Letter Template:<div>(Word Input)</div>
                </Typography>
                <Button variant="outlined" component="label" fullWidth>
                  {files.letterTemplate
                    ? files.letterTemplate.name
                    : 'Upload Letter Template'}
                  <input
                    type="file"
                    hidden
                    onChange={(e) => handleFileChange(e, 'letterTemplate')}
                  />
                </Button>
              </Box>

              {/* Standard Template */}
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography sx={{ width: '50%' }}>
                  Standard Document:
                </Typography>
                <Button variant="outlined" component="label" fullWidth>
                  {files.standardDocument
                    ? files.standardDocument.name
                    : 'Upload Standard Doc'}
                  <input
                    type="file"
                    hidden
                    onChange={(e) => handleFileChange(e, 'standardDocument')}
                  />
                </Button>
              </Box>

              <div style={{ marginTop: '10%' }}></div>
              {/* Generate Button */}
              <Button
                variant="contained"
                onClick={handleGenerate}
                sx={{
                  backgroundColor: '#0d99ff',
                  color: 'white',
                  '&:hover': { backgroundColor: '#0b91f0ff' },
                }}
              >
                Generate
              </Button>
            </Stack>
          </Box>

          {/* Right Section — Recent Uploads */}
          <Paper
            elevation={1}
            sx={{
              width: '30%',
              p: 2,
              borderRadius: 2,
            }}
          >
            <Typography variant="h6" fontWeight={500} mb={1}>
              Recent Uploads
            </Typography>
            <Typography variant="body2" sx={{ color: 'gray' }}>
              (No recent uploads yet)
            </Typography>
          </Paper>
        </Box>
      </Card>
    </div>
  );
};

export default UploadFilePage;
