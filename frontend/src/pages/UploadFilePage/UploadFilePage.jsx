import React, { useState } from 'react';
import { Box, Button, Typography, Stack, Paper, Card } from '@mui/material';

const UploadFilePage = () => {
  const [files, setFiles] = useState({
    sourceFile: null,
    trfTemplate: null,
    cdrTemplate: null,
    letterTemplate: null,
  });

  const handleFileChange = (e, key) => {
    setFiles({
      ...files,
      [key]: e.target.files[0],
    });
  };

  const handleGenerate = () => {
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
        elevation={3}
        sx={{
          width: '50%',
          p: 3,
          borderRadius: 2,
          alignItems: 'center',
          border: '1px solid black',
        }}
      >
        {/* Header */}
        <Typography variant="h5" fontWeight={600} mb={3}>
          Project Files
        </Typography>

        {/* Main Layout */}
        <Box sx={{ display: 'flex', gap: 3 }}>
          {/* Left Section */}
          <Box sx={{ width: '65%' }}>
            <Typography variant="h6" mb={2} fontWeight={500}>
              Upload Source Files
            </Typography>

            <Stack spacing={2}>
              {/* Source File */}
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography sx={{ width: '40%' }}>Source Files:</Typography>
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
                <Typography sx={{ width: '40%' }}>TRF Template:</Typography>
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
                <Typography sx={{ width: '40%' }}>CDR Template:</Typography>
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
                <Typography sx={{ width: '40%' }}>Letter Template:</Typography>
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

              {/* Generate Button */}
              <Button
                variant="contained"
                onClick={handleGenerate}
                sx={{
                  backgroundColor: 'black',
                  color: 'white',
                  '&:hover': { backgroundColor: '#333' },
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
              width: '35%',
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
