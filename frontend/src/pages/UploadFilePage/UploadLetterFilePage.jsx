/* eslint-disable */
/* eslint quotes: "off" */
import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Button,
  Typography,
  Stack,
  Card,
  Snackbar,
  Alert,
  Tooltip,
} from '@mui/material';
import { getProjectByIdApi } from '../../redux/api/projectApi';
import { useNavigate, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { generateTrfRequest } from '../../redux/features/generateTrf/generateTrfSlice';
import { generateLetterRequest } from '../../redux/features/generateLetter/generateLetterSlice';
import { uploadTrfOutApi } from '../../redux/api/uploadTrfOutApi';
import { uploadCdrOutApi } from '../../redux/api/uploadCdrOutApi';

const UploadLetterFilePage = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const dispatch = useDispatch();

  /* ---------------- PROJECT META ---------------- */
  const [projectMeta, setProjectMeta] = useState({
    standard: state?.standard || '',
    projectId: state?.projectId || localStorage.getItem('projectId') || '',
    clientName: state?.clientName || '',
    product: state?.product || '',
  });

  const { standard, projectId, clientName, product } = projectMeta;

  /* ---------------- REFS ---------------- */
  const trfInputRef = useRef(null);
  const cdrInputRef = useRef(null);

  /* ---------------- STATIC FILE ---------------- */
  // const files = {
  //   standardDocument: { name: 'IEC_61010-1-2010.pdf' },
  // };

  /* ---------------- STATE ---------------- */
  const [uploadedFiles, setUploadedFiles] = useState({
    trf: null,
    cdr: null,
  });
  const [trfBlobUrl, setTrfBlobUrl] = useState('');
  const [cdrBlobUrl, setcdrBlobUrl] = useState('');

  const [successToast, setSuccessToast] = useState({
    open: false,
    message: '',
  });
  const [errorToast, setErrorToast] = useState({
    open: false,
    message: '',
  });

  const allowedExtensions = [
    'pdf',
    'docx',
    'xls',
    'xlsx',
    'png',
    'jpg',
    'jpeg',
    'doc',
    'txt',
  ];

  /* ---------------- LOAD META ---------------- */
  useEffect(() => {
    const loadProject = async () => {
      if (!projectId) return;
      const res = await getProjectByIdApi(projectId);
      setProjectMeta((prev) => ({
        standard: prev.standard || res?.Standard || '',
        projectId: prev.projectId || res?.Project_Id || '',
        clientName: prev.clientName || res?.Client_Name || '',
        product: prev.product || res?.Product || '',
      }));
    };
    loadProject();
  }, [projectId]);

  /* ---------------- VALIDATION ---------------- */
  const validateFiles = (files) => {
    const valid = [];
    const invalid = [];

    files.forEach((file) => {
      const ext = file.name.split('.').pop().toLowerCase();
      if (!allowedExtensions.includes(ext)) invalid.push(file.name);
      else valid.push(file);
    });

    return { valid, invalid };
  };

  /* ---------------- TRF UPLOAD ---------------- */
  const handleTrfUpload = async (e) => {
    const selected = Array.from(e.target.files);
    if (!selected.length) return;

    const { valid, invalid } = validateFiles(selected);

    if (invalid.length) {
      setErrorToast({
        open: true,
        message: `Unsupported files: ${invalid.join(', ')}`,
      });
    }
    if (!valid.length) return;

    const res = await uploadTrfOutApi(projectId, 'trf', valid);
    setTrfBlobUrl(res?.blob_url);

    setUploadedFiles((prev) => ({
      ...prev,
      trf: res?.uploaded_files?.[0] || valid[0].name,
    }));

    setSuccessToast({
      open: true,
      message: 'TRF file uploaded successfully',
    });

    e.target.value = '';
  };

  /* ---------------- CDR UPLOAD ---------------- */
  const handleCdrUpload = async (e) => {
    const selected = Array.from(e.target.files);
    if (!selected.length) return;

    const { valid, invalid } = validateFiles(selected);

    if (invalid.length) {
      setErrorToast({
        open: true,
        message: `Unsupported files: ${invalid.join(', ')}`,
      });
    }
    if (!valid.length) return;

    const res = await uploadCdrOutApi(projectId, 'cdr', valid);
    setcdrBlobUrl(res?.blob_url);

    setUploadedFiles((prev) => ({
      ...prev,
      cdr: res?.uploaded_files?.[0] || valid[0].name,
    }));

    setSuccessToast({
      open: true,
      message: 'CDR file uploaded successfully',
    });

    e.target.value = '';
  };

  /* ---------------- FILE ROW ---------------- */
  const renderFileRow = (
    label,
    uploadedFile,
    onBrowse,
    helperText = '',
    disabled = false
  ) => (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        alignItems: 'center',
        gap: 2,
      }}
    >
      <Box>
        <Typography fontWeight={600}>{label}</Typography>
        {helperText && (
          <Typography
            variant="caption"
            sx={{
              color: 'red',
              fontWeight: 600,
            }}
          >
            ({helperText})
          </Typography>
        )}
      </Box>

      <Box sx={{ textAlign: 'center' }}>
        {uploadedFile ? (
          <Typography sx={{ fontSize: 14 }}>{uploadedFile}</Typography>
        ) : (
          <Typography sx={{ fontSize: 14, color: 'text.secondary' }}>
            No file uploaded
          </Typography>
        )}
      </Box>

      <Box sx={{ textAlign: 'right' }}>
        {
          <Button variant="outlined" onClick={onBrowse}>
            Browse
          </Button>
        }
      </Box>
    </Box>
  );

  /* ---------------- UI ---------------- */
  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="80vh"
    >
      <Card sx={{ width: '70%', maxWidth: 900, p: 3 }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" fontWeight={600}>
            Project Files
          </Typography>
          <Tooltip
            title={
              <Box>
                <div>
                  <b>Standard:</b> {standard}
                </div>
                <div>
                  <b>Project ID:</b> {projectId}
                </div>
                <div>
                  <b>Client:</b> {clientName}
                </div>
                <div>
                  <b>Product:</b> {product}
                </div>
              </Box>
            }
          >
            <Typography sx={{ color: 'text.secondary' }}>
              ({standard} / {projectId} / {clientName} / {product})
            </Typography>
          </Tooltip>
        </Box>

        <Stack spacing={2} sx={{ px: 6 }}>
          {renderFileRow(
            'TRF Filled:',
            uploadedFiles.trf,
            () => trfInputRef.current.click(),
            'docx'
          )}
          {renderFileRow(
            'CDR Filled:',
            uploadedFiles.cdr,
            () => cdrInputRef.current.click(),
            'xlsx(optional)'
          )}
          {/* {renderFileRow(
            'Standard Document:',
            files.standardDocument.name,
            null,
            '',
            true
          )} */}
        </Stack>

        <input
          hidden
          ref={trfInputRef}
          type="file"
          multiple
          onChange={handleTrfUpload}
        />
        <input
          hidden
          ref={cdrInputRef}
          type="file"
          multiple
          onChange={handleCdrUpload}
        />

        <Box sx={{ mt: 6, display: 'flex', justifyContent: 'center' }}>
          <Button
            variant="contained"
            sx={{ px: 6 }}
            onClick={async () => {
              if (!projectId) {
                setErrorToast({
                  open: true,
                  message: 'Project ID not found. Cannot generate Letter.',
                });
                return;
              }

              try {
                const res = await triggerGenerateLetterApi(
                  projectId,
                  trfBlobUrl,
                  cdrBlobUrl
                );

                if (res?.data) {
                  //  Navigate to Letter report page after backend generation
                  navigate('/report-page/letter', {
                    state: {
                      standard,
                      projectId,
                      clientName,
                      product,
                    },
                  });
                } else {
                  throw new Error('Letter generation failed');
                }
              } catch (err) {
                console.error('Letter generation failed:', err);
                setErrorToast({
                  open: true,
                  message: 'Failed to generate Letter report',
                });
              }
            }}
          >
            Generate Letter
          </Button>
        </Box>
      </Card>

      <Snackbar open={successToast.open} autoHideDuration={3000}>
        <Alert severity="success">{successToast.message}</Alert>
      </Snackbar>
      <Snackbar open={errorToast.open} autoHideDuration={3000}>
        <Alert severity="error">{errorToast.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default UploadLetterFilePage;
