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
  Paper,
} from '@mui/material';
import { getProjectByIdApi } from '../../redux/api/projectApi';
import { useNavigate, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { generateTrfRequest } from '../../redux/features/generateTrf/generateTrfSlice';
import { generateLetterRequest } from '../../redux/features/generateLetter/generateLetterSlice';
import { uploadTrfOutApi } from '../../redux/api/uploadTrfOutApi';
import { uploadCdrOutApi } from '../../redux/api/uploadCdrOutApi';
import { triggerGenerateLetterApi } from '../../redux/api/generateLetterApi';
import { idb_get, STORES } from '../../utils/idb';

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

  const allowedExtensions = ['docx', 'xlsx'];

  /* ---------------- LOAD META ---------------- */
  useEffect(() => {
    const loadProject = async () => {
      if (!projectId) return;
      const res = await getProjectByIdApi(projectId);
      //console.log('res', res);
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

    const file = selected[0];
    const ext = file.name.split('.').pop().toLowerCase();

    if (ext !== 'docx') {
      setErrorToast({
        open: true,
        message: 'Only .docx file is allowed for TRF Filled',
      });
      e.target.value = '';
      return;
    }

    try {
      const res = await uploadTrfOutApi(projectId, 'trf', [file]);

      setTrfBlobUrl(res?.blob_url);

      setUploadedFiles((prev) => ({
        ...prev,
        trf: res?.uploaded_files?.[0] || file.name,
      }));

      setSuccessToast({
        open: true,
        message: 'TRF file uploaded successfully',
      });
    } catch (err) {
      console.error('TRF upload failed:', err);
      setErrorToast({
        open: true,
        message: 'Failed to upload TRF file',
      });
    }

    e.target.value = '';
  };

  /* ---------------- CDR UPLOAD ---------------- */
  const handleCdrUpload = async (e) => {
    const selected = Array.from(e.target.files);
    if (!selected.length) return;

    const file = selected[0];
    const ext = file.name.split('.').pop().toLowerCase();

    if (ext !== 'xlsx') {
      setErrorToast({
        open: true,
        message: 'Only .xlsx file is allowed for CDR Filled',
      });
      e.target.value = '';
      return;
    }

    try {
      const res = await uploadCdrOutApi(projectId, 'cdr', [file]);

      setcdrBlobUrl(res?.blob_url);

      setUploadedFiles((prev) => ({
        ...prev,
        cdr: res?.uploaded_files?.[0] || file.name,
      }));

      setSuccessToast({
        open: true,
        message: 'CDR file uploaded successfully',
      });
    } catch (err) {
      console.error('CDR upload failed:', err);
      setErrorToast({
        open: true,
        message: 'Failed to upload CDR file',
      });
    }

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
          <Typography variant="caption">({helperText})</Typography>
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
      sx={{
        minHeight: '80vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 4,
        px: 4,
      }}
    >
      <Card
        sx={{
          height: '61vh',
          width: '55%',
          maxWidth: 900,
          p: 3,
          borderRadius: 3,
          boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
        }}
      >
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

        <Stack spacing={2} sx={{ px: 6, pt: 5 }}>
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
          accept=".docx"
          onChange={handleTrfUpload}
        />
        <input
          hidden
          ref={cdrInputRef}
          type="file"
          accept=".xlsx"
          onChange={handleCdrUpload}
        />

        <Box sx={{ mt: 6, pt: 7, display: 'flex', justifyContent: 'center' }}>
          <Button
            variant="contained"
            sx={{ px: 6 }}
            disabled={!trfBlobUrl}
            onClick={async () => {
              if (!projectId) {
                setErrorToast({
                  open: true,
                  message: 'Project ID not found. Cannot generate Letter.',
                });
                return;
              }

              const storageKey = `letter_report_${projectId}`;

              try {
                //  If already generated → just open Letter page
                const cached = await idb_get(storageKey, STORES.LETTER);
                if (cached) {
                  navigate('/report-page/letter', {
                    state: { standard, projectId, clientName, product },
                  });
                  return;
                }

                //  Not generated yet → go to Letter page and let it generate
                if (!trfBlobUrl) {
                  setErrorToast({
                    open: true,
                    message:
                      'Please upload TRF Filled file before generating Letter.',
                  });
                  return;
                }

                //  Navigate immediately → loader will show
                navigate('/report-page/letter', {
                  state: {
                    standard,
                    projectId,
                    clientName,
                    product,
                    trfBlobUrl, // pass these so Letter page can generate
                    cdrBlobUrl,
                  },
                });
              } catch (err) {
                console.error('Letter generation navigation failed:', err);
                setErrorToast({
                  open: true,
                  message: 'Failed to start Letter generation',
                });
              }
            }}
          >
            Generate Letter
          </Button>
        </Box>
      </Card>

      {/* RIGHT – RECENT UPLOADS */}
      <Paper
        sx={{
          width: '35%',
          maxWidth: 420,
          height: '61vh',
          p: 3,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid #e0e0e0',
          borderRadius: 3,
          boxShadow: '0 8px 24px rgba(0,0,0,0.06)',
          background: '#fafafa',
        }}
      >
        <Box
          sx={{
            width: '100%',
            display: 'flex',
            justifyContent: 'center',
          }}
        >
          <Box
            component="img"
            src="/images/letter_report_sample.png"
            alt="Letter report sample"
            sx={{
              width: '100%',
              maxWidth: 320,
              borderRadius: 2,
              border: '1px solid #ddd',
              boxShadow: '0 6px 16px rgba(0,0,0,0.12)',
            }}
          />
        </Box>

        <Typography
          variant="caption"
          sx={{ mt: 2, color: 'text.secondary', textAlign: 'center' }}
        >
          Preview of the generated Letter Report format
        </Typography>
      </Paper>

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
