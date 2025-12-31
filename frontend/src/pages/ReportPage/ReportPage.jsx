/* eslint quotes: "off" */
/* eslint-disable */
import React, { useRef, useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Divider,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
} from '@mui/material';
import './ReportPage.css';
import { useDispatch, useSelector } from 'react-redux';
import DataTable from '../../components/DataTable';
import { finaliseReportRequest } from '../../redux/features/finaliseReport/finaliseReportSlice';
import { getProjectReportStatusApi } from '../../redux/api/projectStatusApi';
import CloseIcon from '@mui/icons-material/Close';
import IconButton from '@mui/material/IconButton';

import { generateTrfApi } from '../../redux/api/generateTrfApi';
//import localCdrJson from '../../utils/cdr_payload_3.json';
import localCdrJson from '../../utils/cdr_payload_v5_updated.json';
import CdrReport from '../../components/CdrReport/CdrReport';
//import localJson from '../../utils/pta_final_6.json';
import PdfViewer from '../../components/PdfViewer';
//import localJson from '../../utils/iec_output_1.json';
import localJson from '../../utils/pta_final_6_2_output.json';
// import localJson2 from '../../utils/iec_output.json';

import ConfidenceScore from './ConfidenceScore';
import { truncateWords } from '../../Helpers/truncateWords';
import { normalizeNewLines } from '../../Helpers/normalizeNewLines';
import { RenderImageThumbnails } from '../../Helpers/renderImageThumbnails';
import { generateCdrRequest } from '../../redux/features/generateCdr/generateCdrSlice';
import { triggerGenerateCdrApi } from '../../redux/api/generateCdrApi';
//import { downloadReportRequest } from '../../redux/features/downloadReport/downloadReportSlice';
import { loadPdfWithCache } from '../../components/loadPdfWithCache';
import CdrLoader from '../../components/CdrReport/CdrLoader';

const ReportPage = () => {
  const dispatch = useDispatch();
  const dataTableRef = useRef(null);

  const pdfViewerRef = useRef(null);

  const projectID = localStorage.getItem('projectId');

  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarkData, setBookmarkData] = useState(null);
  const [trfJson, setTrfJson] = useState(null);
  const [cdrJson, setCdrJson] = useState(null);
  const [cdrLoading, setCdrLoading] = useState(false);

  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);

  // const [issuedBy, setIssuedBy] = useState('');

  const [status, setStatus] = useState('Pending'); // "Pending" for the trf api json , "Completed" for the local json"
  const [cdrStatus, setCdrStatus] = useState('Pending'); // Pending for the Cdr Json status
  const [progress, setProgress] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [isFinalise, setIsFinalise] = useState(false);

  // 🔹 TRF states
  const [trfEditMode, setTrfEditMode] = useState(false);
  const [trfFinalised, setTrfFinalised] = useState(false);

  // 🔹 CDR states
  const [cdrEditMode, setCdrEditMode] = useState(false);
  const [cdrFinalised, setCdrFinalised] = useState(false);

  const [reportClick, setReportClick] = useState('trf');

  const [activePdfUrl, setActivePdfUrl] = useState(null);
  const [confidenceTick, setConfidenceTick] = useState(0);

  const [activeDocUrl, setActiveDocUrl] = useState(null);
  const [viewerType, setViewerType] = useState(null); // 'pdf' | 'docx'

  const [openCitationDialog, setOpenCitationDialog] = React.useState(false);
  const [selectedCitation, setSelectedCitation] = React.useState(null);

  const myData = useSelector((state) => state?.trf);
  const cdrReportData = useSelector((state) => state?.cdr);

  const { state } = useLocation();

  const isEditMode = reportClick === 'cdr' ? cdrEditMode : trfEditMode;
  const isFinalised = reportClick === 'cdr' ? cdrFinalised : trfFinalised;

  // 🔹 Single source of truth for header info
  const [projectMeta, setProjectMeta] = useState({
    standard: state?.standard || '',
    projectId: state?.projectId || localStorage.getItem('projectId') || '',
    clientName: state?.clientName || '',
    product: state?.product || '',
  });

  const { standard, projectId, clientName, product } = projectMeta;

  const STAGES = [
    { label: 'Indexing', threshold: 10 },
    { label: 'Generating TRF', threshold: 75 },
    { label: 'TRF Generated', threshold: 100 },
  ];

  const navigate = useNavigate();

  // Get TRF report JSON
  const fetchTrfJson = async () => {
    try {
      const res = await generateTrfApi(projectID); // your API call
      if (res?.reports?.length > 0) {
        const jsonData = res.reports[0].json;
        setTrfJson(jsonData);
      }
    } catch (err) {
      console.error('Error fetching TRF JSON:', err);
    }
  };

  // Get CDR report JSON
  const fetchCdrJson = async () => {
    try {
      setCdrLoading(true);

      const res = await triggerGenerateCdrApi(projectID);
      console.log('CDR API RESPONSE:', res);

      if (res?.message === 'CDR Report generated successfully' && res?.data) {
        setCdrJson(res.data); // STORE JSON
        setCdrLoading(false);
      } else {
        console.log('CDR still processing...');
      }
    } catch (err) {
      console.error('CDR generation failed:', err);
    }
  };

  useEffect(() => {
    setTrfJson(myData?.trfData?.data);
    console.log('trfData', myData?.trfData?.data);
  }, [myData]);

  // useEffect(() => {
  //   if (dataTableRef.current && reportClick == 'trf') {
  //     const value = dataTableRef.current.getFieldValue(
  //       'Test Report issued under the responsibility of:'
  //     );
  //     setIssuedBy(value);
  //   }
  // }, [localJson]);

  // useEffect(() => {
  //   if (reportClick !== 'cdr' || !projectID) return;

  //   let intervalId = null;

  //   const checkCdrStatus = async () => {
  //     try {
  //       const res = await getProjectReportStatusApi(projectID);
  //       const message = res?.message || 'Pending';
  //       //const status = res?.cdr_status || 'Pending';
  //       //setCdrStatus(status);

  //       console.log('CDR Message:', message);

  //       if (message === 'CDR Report generated successfully') {
  //         clearInterval(intervalId);
  //         intervalId = null;
  //         await fetchCdrJson();
  //         return;
  //       }
  //     } catch (err) {
  //       console.error('CDR status polling failed', err);
  //     }
  //   };
  //   setCdrLoading(true);
  //   // FIRST HIT (immediate)
  //   checkCdrStatus();

  //   // POLLING
  //   //intervalId = setInterval(checkCdrStatus, 10000);

  //   // return () => {
  //   //   if (intervalId) clearInterval(intervalId);
  //   // };
  // }, [reportClick, projectID]);

  // const handleIssuedByChange = (e) => {
  //   const newValue = e.target.value;
  //   setIssuedBy(newValue);

  //   if (dataTableRef.current) {
  //     dataTableRef.current.setFieldValue(
  //       'Test Report issued under the responsibility of:',
  //       newValue
  //     );
  //   }
  // };

  const handleGenerateCDR = () => {
    if (!projectId) {
      setErrorToast({
        open: true,
        message: 'Project ID not found. Cannot generate CDR.',
      });
      return;
    }

    setReportClick('cdr');
    //setCdrStatus('Pending');
    setCdrJson(null);
    setCdrLoading(true);
    fetchCdrJson();
    //dispatch(generateCdrRequest(projectId));
  };

  const handleGenerateLetter = () => {
    setReportClick('letter');
  };

  // useEffect(() => {
  //   const load = async () => {
  //     const response = await triggerGenerateTrfApi(projectID);
  //     setTrfJson(response.data); // TRF JSON loaded
  //     console.log('trfJson', trfJson);
  //   };

  // ----------------------------------------------------------
  //  STATUS CHECK (FIXED TO MATCH API RESPONSE)
  // ----------------------------------------------------------
  const checkStatus = async () => {
    if (!projectID) {
      console.warn('Missing projectID, skipping status check');
      return;
    }

    try {
      setRefreshing(true);

      const res = await getProjectReportStatusApi(projectID);

      setStatus(res?.trf_status || 'Pending');
      setProgress(
        typeof res?.trf_percentage === 'number' ? res.trf_percentage : 0
      );
    } catch (err) {
      console.error('STATUS CHECK FAILED:', err);
    } finally {
      setRefreshing(false);
    }
  };

  // ----------------------------------------------------------
  //  FIXED POLLING (FIRST LOAD + EVERY 15s) 'comment below useEffect for the local json testing'
  // ----------------------------------------------------------
  useEffect(() => {
    if (!projectID) return;

    let intervalId = null;

    const startPolling = async () => {
      await checkStatus();

      // FIRST CHECK — IF ALREADY COMPLETE → FETCH JSON
      if (status === 'Completed') {
        await fetchTrfJson();
        return;
      }

      intervalId = setInterval(async () => {
        await checkStatus();

        if (status === 'Completed' || progress === 100) {
          clearInterval(intervalId);
          intervalId = null;
          await fetchTrfJson(); // << fetch JSON immediately
          return;
        }
      }, 15000);
    };

    startPolling();

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [projectID, progress, status]);

  // ---------------- BOOKMARK HANDLING ----------------
  const handleBookmarkFromChild = (data) => {
    //console.log('bookmark clicked', data);
    const textSupportTexts =
      data?.ai_fillable === true && Array.isArray(data?.text_support)
        ? data.text_support.map((item) => item.text)
        : [];
    //console.log('textsuptext', textSupportTexts);
    setBookmarkData({
      ...data,
      textSupportTexts,
      textSupportRaw: data?.text_support || [],
    });

    setBookmarkOpen(true);
  };

  const handleCitationLinkClick = (filename, page, text, blob_url) => {
    // ---- XLSX → DOWNLOAD ----
    if (filename?.toLowerCase().endsWith('.xlsx')) {
      const cleanUrl = blob_url.startsWith('/') ? blob_url.slice(1) : blob_url;

      const link = document.createElement('a');
      link.href = cleanUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      return;
    }

    // ---- PDF → INDEXEDDB → VIEWER ----
    setPdfViewerOpen(true);

    setTimeout(async () => {
      if (!pdfViewerRef.current) return;

      await loadPdfWithCache(projectID, filename, blob_url, pdfViewerRef);

      setTimeout(() => {
        pdfViewerRef.current.goToCitation(page, text);
      }, 1200);
    }, 200);
  };

  const handleFinalise = () => {
    if (!dataTableRef.current) return;
    const updatedPayload = dataTableRef.current.getUpdatedJson();
    dispatch(finaliseReportRequest(updatedPayload));
    setIsFinalise(true);
  };

  const handleRegenerate = () => {
    navigate('/create-project', {
      state: {
        standard,
        projectId,
        clientName,
        product,
      },
    });
  };

  const BASE_URL = import.meta.env.VITE_BACKEND_URL;

  const handleDownload = (projectId) => {
    window.open(`${BASE_URL}/projects/download-file?project_id=${projectId}`);
    //dispatch(downloadReportRequest(projectId));
  };

  const getCitationDialogText = () => {
    if (!selectedCitation) return '';

    /* -------- TRF -------- */
    if (reportClick === 'trf') {
      return normalizeNewLines(selectedCitation.text || '');
    }

    /* -------- CDR -------- */
    if (reportClick === 'cdr') {
      // case 1: string
      if (typeof selectedCitation === 'string') {
        return normalizeNewLines(selectedCitation);
      }

      // case 2: object with content
      if (typeof selectedCitation.content === 'string') {
        return normalizeNewLines(selectedCitation.content);
      }
    }

    return '';
  };

  // ---------------- LEFT PANEL ----------------
  // progress < 100 || !trfJson ---  for to load the trf report from api
  // ! true ---- for to load local json
  const renderLeftPanel = () => {
    //if (reportClick === 'cdr') return null;
    if (progress < 100 || !trfJson) {
      return (
        <Card className="progress-advanced-card left-card">
          <Typography className="progress-advanced-title">
            Processing TRF Report
          </Typography>

          {/* STAGE STEPS */}
          <Box className="steps-container">
            {STAGES.map((stage, index) => {
              const reached = progress >= stage.threshold;
              return (
                <Box key={index} className="step-item">
                  <Box className={`step-circle ${reached ? 'active' : ''}`}>
                    {reached ? '✔' : index + 1}
                  </Box>

                  <Typography className="step-label">{stage.label}</Typography>

                  {index !== STAGES.length - 1 && (
                    <Box className={`step-line ${reached ? 'active' : ''}`} />
                  )}
                </Box>
              );
            })}
          </Box>

          {/* ANIMATED PROGRESS BAR */}
          <Box className="animated-progress-wrapper">
            <Box
              className="animated-progress-fill"
              style={{
                width: `${progress}%`,
                background:
                  progress === 100
                    ? 'linear-gradient(90deg, #4caf50, #81c784)'
                    : 'linear-gradient(90deg, #2196f3, #64b5f6)',
              }}
            >
              <Typography className="animated-progress-text">
                {progress}%
              </Typography>
            </Box>
          </Box>

          <Typography className="progress-advanced-status">{status}</Typography>

          <Button
            disabled={refreshing}
            className="refresh-advanced-btn"
            onClick={checkStatus}
          >
            {refreshing ? 'Refreshing...' : 'Refresh Status'}
          </Button>
        </Card>
      );
    }
    return (
      <Card className="left-card">
        <Box
          sx={{ mt: 2, ml: 1, display: 'flex', alignItems: 'center', gap: 1 }}
        >
          <Tooltip
            arrow
            placement="bottom-start"
            title={
              <Box sx={{ fontSize: '13px !important', lineHeight: 1.6 }}>
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
                fontSize: '15px',
                color: 'text.secondary',
                cursor: 'help',
              }}
            >
              ({standard} / {projectId} / {clientName} / {product})
            </Typography>
          </Tooltip>
        </Box>
        <CardContent className="left-content">
          <Box className="report-header">
            <img
              src="/images/trf_image1.jpg"
              className="header-image"
              alt="header"
            />
            {reportClick == 'trf' && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  marginRight: '5%',
                }}
              >
                <Typography className="header-text">
                  Test Report issued under the responsibility of:
                </Typography>

                {/* <TextField
                  variant="outlined"
                  size="small"
                  value={issuedBy}
                  onChange={handleIssuedByChange}
                  style={{ flex: 2 }} // makes textbox expand
                /> */}
              </div>
            )}
          </Box>

          {reportClick == 'trf' && (
            <Box className="report-title-container">
              {/* <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
                TEST REPORT
              </Typography> */}
              <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
                IEC 61010-1
              </Typography>
              <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
                Safety requirements for electrical equipment for measurement,
                control, and laboratory use
              </Typography>
              <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
                Part 1: General requirements
              </Typography>
            </Box>
          )}

          {reportClick == 'cdr' && (
            <Box className="report-title-container">
              <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
                CDR REPORT
              </Typography>
            </Box>
          )}

          {reportClick == 'trf' && (
            <DataTable
              ref={dataTableRef}
              jsonData={trfJson} // api json load
              //jsonData={localJson} //localJson load
              editMode={trfEditMode}
              onBookmarkClick={handleBookmarkFromChild}
              reportType="trf"
              onConfidenceChange={() => {
                setConfidenceTick((v) => v + 1);
              }}
            />
          )}

          {reportClick === 'cdr' && (
            <>
              {cdrLoading && <CdrLoader />}

              {!cdrLoading && cdrJson && (
                <CdrReport
                  ref={dataTableRef}
                  jsonData={cdrJson}
                  editMode={cdrEditMode}
                  projectId={localStorage.getItem('projectId')}
                  onBookmarkClick={handleBookmarkFromChild}
                  reportType="cdr"
                  cdrFinalised={cdrFinalised}
                  onConfidenceChange={() => {
                    setConfidenceTick((v) => v + 1);
                  }}
                />
              )}
            </>
          )}

          {/* local rendering of cdr report */}
          {/* {reportClick === 'cdr' && (
            <CdrReport
              ref={dataTableRef}
              jsonData={localCdrJson}
              editMode={cdrEditMode}
              projectId={localStorage.getItem('projectId')}
              onBookmarkClick={handleBookmarkFromChild}
              reportType="cdr"
              cdrFinalised={cdrFinalised}
              onConfidenceChange={() => {
                setConfidenceTick((v) => v + 1);
              }}
            />
          )} */}
        </CardContent>
      </Card>
    );
  };

  // ---------------- FINAL PAGE LAYOUT ----------------
  return (
    <Box className="report-container">
      <Box className="left-panel">{renderLeftPanel()}</Box>

      {/* PDF VIEWER POPUP MODAL */}
      {pdfViewerOpen && (
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            background: 'rgba(0,0,0,0.65)',
            zIndex: 2000,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            backdropFilter: 'blur(3px)',
          }}
        >
          <Box
            sx={{
              width: '90%',
              height: '90%',
              background: '#fff',
              borderRadius: '8px',
              overflow: 'hidden',
              position: 'relative', // REQUIRED
              boxShadow: '0px 5px 20px rgba(0,0,0,0.3)',
            }}
          >
            <Button
              onClick={() => setPdfViewerOpen(false)}
              sx={{
                position: 'absolute',
                top: 10,
                right: 10,
                zIndex: 2100,
                background: 'rgba(0,0,0,0.6)',
                color: '#fff',
                '&:hover': { background: 'rgba(0,0,0,0.8)' },
              }}
            >
              Close
            </Button>

            {/* PDF VIEWER MUST BE INSIDE THIS RELATIVE BOX */}
            <PdfViewer ref={pdfViewerRef} />
          </Box>
        </Box>
      )}

      {/* BOOKMARK / CITATION PANEL */}
      {bookmarkOpen ? (
        <Box className="bookmark-panel">
          {/* Header */}
          <Box className="bookmark-header">
            <Typography className="bookmark-title"></Typography>
            <Button size="small" onClick={() => setBookmarkOpen(false)}>
              ✕
            </Button>
          </Box>

          {/* Field Name */}
          {/* <Typography className="bookmark-field">
            {bookmarkData?.field}
          </Typography> */}

          {/* Field Value */}
          {/* <Typography className="bookmark-value">
            {bookmarkData?.value}
          </Typography> */}

          {/* SUPPORTING TEXT + HYPERLINKS (Text-level placement) */}
          {bookmarkData?.textSupportRaw?.length > 0 && (
            <Box mt={2}>
              <Typography sx={{ fontWeight: 600, mb: 2 }}>
                Supporting Images
              </Typography>

              {/* 🔹 IMAGE THUMBNAILS */}
              <RenderImageThumbnails images={bookmarkData?.image_support} />

              <Typography sx={{ fontWeight: 600, mt: 2, mb: 2 }}>
                Supporting Text
              </Typography>

              {bookmarkData?.textSupportRaw?.map((item, idx) => {
                //console.log('Itemm', item);
                let rawText = '';
                let isTruncated = false;

                /* -------- TRF & CDR -------- */

                rawText = item?.text || '';
                isTruncated = rawText.split(/\s+/).length > 20;

                // /* -------- CDR -------- */
                // if (reportClick === 'cdr') {
                //   // case 1: string
                //   if (typeof item === 'string') {
                //     rawText = item;
                //   }
                //   // case 2: object with content
                //   else if (typeof item?.content === 'string') {
                //     rawText = item.content;
                //     isTruncated = rawText.split(/\s+/).length > 20;
                //   }
                // }

                const cleanedText = normalizeNewLines(rawText);
                const truncatedText = truncateWords(cleanedText, 20);

                //console.log('urll', item.url);
                return (
                  <Card key={idx} sx={{ mb: 2 }}>
                    <CardContent>
                      {/* Truncated text */}
                      <Typography sx={{ whiteSpace: 'pre-wrap', fontSize: 14 }}>
                        {truncatedText}
                        {isTruncated && (
                          <Typography
                            component="span"
                            sx={{
                              ml: 0.5,
                              color: '#0077cc',
                              cursor: 'pointer',
                              fontWeight: 500,
                            }}
                            onClick={() => {
                              setSelectedCitation(item);
                              setOpenCitationDialog(true);
                            }}
                          >
                            ...more
                          </Typography>
                        )}
                      </Typography>

                      {/* ---------- TRF LINK ---------- */}
                      {reportClick === 'trf' && item?.filename && (
                        <Typography
                          sx={{
                            fontSize: 13,
                            mt: 1,
                            color: '#1976d2',
                            cursor: 'pointer',
                            textDecoration: 'underline',
                          }}
                          onClick={() =>
                            handleCitationLinkClick(
                              item.filename,
                              item.page + 1,
                              rawText,
                              item.url
                            )
                          }
                        >
                          {item.filename} (Page {item.page})
                        </Typography>
                      )}

                      {/* ---------- CDR LINK ---------- */}
                      {reportClick === 'cdr' && item?.file && (
                        <Typography
                          sx={{
                            fontSize: 13,
                            mt: 1,
                            color: '#1976d2',
                            cursor: 'pointer',
                            textDecoration: 'underline',
                          }}
                          onClick={() =>
                            handleCitationLinkClick(
                              item.file,
                              item.page,
                              rawText,
                              item?.url
                            )
                          }
                        >
                          {item.file} (Page {item.page})
                        </Typography>
                      )}

                      {/* File + page */}
                    </CardContent>
                  </Card>
                );
              })}
            </Box>
          )}
        </Box>
      ) : (
        <Box className="right-panel">
          {/* ACTION CARD */}
          <Card className="action-card">
            <CardContent>
              <Typography variant="h6" className="action-title">
                Actions
              </Typography>

              <Box className="button-stack">
                {[
                  {
                    text: 'Edit / Refine',
                    icon: '/images/edit_icon.svg',
                    bg: '#2C2C2C',
                    action: () => {
                      if (reportClick === 'cdr') {
                        setCdrEditMode(true);
                        setCdrFinalised(false);
                      } else {
                        setTrfEditMode(true);
                        setTrfFinalised(false);
                      }
                    },
                  },
                  {
                    text: 'Finalize',
                    icon: '/images/approve_icon.png',
                    bg: '#396872ff',
                    action: () => {
                      handleFinalise();

                      if (reportClick === 'cdr') {
                        setCdrEditMode(false);
                        setCdrFinalised(true);
                      } else {
                        setTrfEditMode(false);
                        setTrfFinalised(true);
                      }
                    },
                  },
                  {
                    text: 'Download',
                    icon: '/images/download_icon.png',
                    bg: '#77D5EA',
                    action: () => handleDownload(projectID),
                  },
                  {
                    text: 'Missing Field Re..',
                    icon: '/images/file_icon.png',
                    bg: '#5191a0ff',
                  },
                  {
                    text: 'Regenerate',
                    icon: '/images/regenrate_icon.png',
                    bg: '#417581',
                    action: handleRegenerate,
                  },
                ].map((btn, i) => (
                  <Button
                    key={i}
                    fullWidth
                    variant="contained"
                    className="action-button"
                    onClick={btn.action}
                    style={{ background: btn.bg }}
                  >
                    {/* STATUS DOT (only for Finalize) */}
                    {btn.text === 'Finalize' && (
                      <span
                        className={`finalize-status-dot ${
                          isEditMode && !isFinalised ? 'red' : 'green'
                        }`}
                      />
                    )}
                    <img
                      src={btn.icon}
                      alt=""
                      className={`icon-img icon-white`}
                    />

                    {btn.text}
                  </Button>
                ))}
              </Box>
              <Typography className="generate-title">Generate</Typography>

              <Box className="generate-row">
                {['CDR', 'Letter']
                  .filter(
                    (label) => !(reportClick === 'cdr' && label === 'CDR')
                  )
                  .map((label, i) => {
                    const isDisabledStyle =
                      reportClick === 'cdr' ? !cdrFinalised : !trfFinalised;

                    return (
                      <Button
                        key={i}
                        variant="contained"
                        className="generate-btn"
                        style={{
                          background: isDisabledStyle ? '#A9A9A9' : '#417581', // grey out
                          cursor: isDisabledStyle ? 'not-allowed' : 'pointer',
                          opacity: isDisabledStyle ? 0.7 : 1,
                        }}
                        onClick={() => {
                          //if (!isFinalise) return;
                          if (reportClick === 'trf' && !trfFinalised) return;
                          if (reportClick === 'cdr' && !cdrFinalised) return;
                          // still prevent action
                          if (label === 'CDR') {
                            //console.log('cddddd');
                            handleGenerateCDR(); // <-- your function
                          } else if (label === 'Letter') {
                            handleGenerateLetter(); // <-- your second function
                          }
                          //console.log(label, 'clicked');
                        }}
                      >
                        <img
                          src="/images/approve_icon.png"
                          className="icon-img icon-white"
                          style={{
                            opacity: isDisabledStyle ? 0.6 : 1,
                          }}
                        />
                        {label}
                      </Button>
                    );
                  })}
              </Box>
            </CardContent>
          </Card>

          {/* CONFIDENCE CARD */}
          {((reportClick === 'trf' && trfJson) ||
            (reportClick === 'cdr' && cdrJson)) && (
            <ConfidenceScore
              data={reportClick === 'trf' ? trfJson : cdrJson}
              reportType={reportClick}
              confidenceTick={confidenceTick}
              projectId={projectId}
            />
          )}

          {/* local rendering of cdr report */}
          {/* {((reportClick === 'trf' && localJson) ||
            (reportClick === 'cdr' && localCdrJson)) && (
            <ConfidenceScore
              data={reportClick === 'trf' ? localJson : localCdrJson}
              reportType={reportClick}
              confidenceTick={confidenceTick}
              projectId={projectId}
            />
          )} */}
        </Box>
      )}
      <Dialog
        open={openCitationDialog}
        onClose={() => setOpenCitationDialog(false)}
        maxWidth="md"
        fullWidth
      >
        {/* ---------- Header with Close Icon ---------- */}
        <DialogTitle
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            pr: 1,
          }}
        >
          Citation Details
          <IconButton
            onClick={() => setOpenCitationDialog(false)}
            sx={{
              color: '#000',
            }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        {/* ---------- Content ---------- */}
        <DialogContent
          dividers
          sx={{
            overflowX: 'hidden',
          }}
        >
          {selectedCitation && (
            <>
              <Typography
                sx={{
                  fontSize: 14,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  overflowWrap: 'anywhere',
                  mb: 2,
                }}
              >
                {getCitationDialogText()}
                {/* {normalizeNewLines(selectedCitation.text)} */}
              </Typography>

              {reportClick === 'trf' && selectedCitation?.filename && (
                <Typography
                  sx={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: '#1976d2',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                  onClick={() =>
                    handleCitationLinkClick(
                      item?.filename,
                      selectedCitation.page + 1,
                      selectedCitation.text,
                      selectedCitation.url
                    )
                  }
                >
                  {selectedCitation.filename} (Page {selectedCitation.page + 1})
                </Typography>
              )}

              {reportClick === 'cdr' && selectedCitation?.filename && (
                <Typography
                  sx={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: '#1976d2',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                  onClick={() =>
                    handleCitationLinkClick(
                      selectedCitation.filename,
                      selectedCitation.page,
                      getCitationDialogText()
                    )
                  }
                >
                  {selectedCitation.filename} (Page {selectedCitation.page})
                </Typography>
              )}
            </>
          )}
        </DialogContent>

        {/* ---------- Footer with Black Button ---------- */}
        <DialogActions sx={{ p: 2 }}>
          <Button
            variant="contained"
            onClick={() => setOpenCitationDialog(false)}
            sx={{
              backgroundColor: '#000',
              color: '#fff',
              textTransform: 'none',
              '&:hover': {
                backgroundColor: '#000',
              },
            }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ReportPage;
