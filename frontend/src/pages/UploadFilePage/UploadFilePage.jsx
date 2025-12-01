import React, { useState, useEffect } from 'react';
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
import { useDispatch, useSelector } from 'react-redux';
import { generateTrfRequest } from '../../redux/features/generateTrf/generateTrfSlice';
import JSONData from '../../utils/pta_final.json';
import './UploadFilePage.css';

const UploadFilePage = () => {
  const [files, setFiles] = useState({
    sourceFiles: [], // multiple
    trfTemplate: null,
    cdrTemplate: null,
    letterTemplate: null,
    standardDocument: null,
  });

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

  // Load default files from backend
  useEffect(() => {
    const fetchDefaultFiles = async () => {
      const backendFiles = {
        sourceFiles: [],
        trfTemplate: { name: 'CB scheme TRF Template iec6101_1.docx' },
        cdrTemplate: { name: 'CDR Report Template.xlsx' },
        letterTemplate: { name: 'intertek gft OP 10 letter report.docx' },
        standardDocument: { name: 'IEC 61010-1-2010.pdf' },
      };
      setFiles((prev) => ({ ...prev, ...backendFiles }));
    };

    fetchDefaultFiles();
  }, []);

  const handleFileChange = (e, key, multiple = false) => {
    const selectedFiles = multiple
      ? Array.from(e.target.files)
      : e.target.files[0];
    if (multiple) {
      setFiles((prev) => ({
        ...prev,
        [key]: [...prev[key], ...selectedFiles],
      }));
    } else {
      setFiles((prev) => ({ ...prev, [key]: selectedFiles }));
    }
  };

  const handleDeleteFile = (key, index = null) => {
    if (key === 'sourceFiles' && index !== null) {
      setFiles((prev) => ({
        ...prev,
        [key]: prev[key].filter((_, i) => i !== index),
      }));
    } else {
      setFiles((prev) => ({ ...prev, [key]: null }));
    }
  };

  const handleGenerate = () => {
    setIsSubmitting(true); // start loader

    const file = new File(
      [JSON.stringify(JSONData, null, 2)],
      'pta_final.json',
      { type: 'application/json' }
    );

    dispatch(
      generateTrfRequest({
        project_id: 'PRJ_000001',
        file,
      })
    );
  };

  // Render single file input with delete logic
  const renderFileInput = (label, key, description, multiple = false) => {
    const hasFiles = multiple ? files[key].length > 0 : !!files[key];
    return (
      <Box
        sx={{ display: 'flex', width: '100%', alignItems: 'center', gap: 1 }}
      >
        {/* Label */}
        <Box sx={{ minWidth: '200px' }}>
          <Typography sx={{ fontWeight: 600 }}>
            {label}
            {description && (
              <Typography
                component="div"
                sx={{
                  fontSize: '14px',
                  color: 'gray',
                  fontWeight: 400,
                  ml: 0.5,
                }}
              >
                {description}
              </Typography>
            )}
          </Typography>
        </Box>

        {/* File boxes */}
        <Box
          sx={{
            display: 'flex',
            gap: 1,
            flexWrap: 'wrap',
            flex: 1,
          }}
        >
          {multiple
            ? files[key].map((file, idx) => (
                <Box
                  key={idx}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    bgcolor: '#f0f0f0',
                    px: 1,
                    py: 0.5,
                    borderRadius: 1,
                    gap: 0.5,
                  }}
                >
                  <Typography variant="body2">{file.name}</Typography>
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteFile(key, idx)}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Box>
              ))
            : files[key] && (
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    bgcolor: '#f0f0f0',
                    px: 1,
                    py: 0.5,
                    borderRadius: 1,
                    gap: 0.5,
                  }}
                >
                  <Typography variant="body2">{files[key].name}</Typography>
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteFile(key)}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Box>
              )}

          {/* Show Upload button only if no files */}
          {!hasFiles && (
            <Button
              variant="outlined"
              component="label"
              sx={{ fontSize: '13px' }}
            >
              Upload
              <input
                type="file"
                hidden
                multiple={multiple}
                onChange={(e) => handleFileChange(e, key, multiple)}
              />
            </Button>
          )}
        </Box>
      </Box>
    );
  };

  return (
    <div
      style={{
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <Card
        sx={{
          width: '80%',
          p: 3,
          borderRadius: 2,
          alignItems: 'center',
        }}
      >
        <Typography variant="h5" fontWeight={600} mb={3}>
          Project Files
        </Typography>

        <Box sx={{ display: 'flex', gap: 3 }}>
          <Box sx={{ width: '70%', boxShadow: 3, p: 2, borderRadius: '1%' }}>
            <Stack spacing={2}>
              {renderFileInput(
                'Source Documents:',
                'sourceFiles',
                '(Multiple Files)',
                true
              )}
              {renderFileInput('TRF Template:', 'trfTemplate', '(Word Input)')}
              {renderFileInput('CDR Template:', 'cdrTemplate', '(Excel Input)')}
              {renderFileInput(
                'Letter Template:',
                'letterTemplate',
                '(Word Input)'
              )}
              {renderFileInput('Standard Document:', 'standardDocument')}

              <div style={{ marginTop: '10%' }} />
              <Button
                variant="contained"
                onClick={handleGenerate}
                disabled={isSubmitting}
                sx={{
                  backgroundColor: '#0d99ff',
                  color: 'white',
                  '&:hover': { backgroundColor: '#0b91f0ff' },
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                }}
              >
                {isSubmitting ? (
                  <>
                    Generating TRF
                    <span className="loader" />
                  </>
                ) : (
                  'Generate TRF'
                )}
              </Button>
            </Stack>
          </Box>

          <Paper
            elevation={1}
            sx={{ width: '30%', p: 2, borderRadius: 2, boxShadow: 3 }}
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
