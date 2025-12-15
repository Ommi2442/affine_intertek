/* eslint quotes: "off" */
/* eslint-disable */
import React, { useRef, useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Divider,
  TextField,
} from '@mui/material';
import './ReportPage.css';
import { useDispatch, useSelector } from 'react-redux';
import DataTable1 from '../../components/DataTable1';
import { finaliseReportRequest } from '../../redux/features/finaliseReport/finaliseReportSlice';
import { getProjectReportStatusApi } from '../../redux/api/projectStatusApi';

import { generateTrfApi } from '../../redux/api/generateTrfApi';
// import localJson from '../../utils/pta_final_5_UI_upd.json';
//import localJsonRemaining from '../../utils/43_84_page_trf.json';
//import RemainingPagesData from '../../components/RemainingPagesData';
//import NewJson from '../../utils/newJsonFrom42.json';
//import HtmlPageRenderer from '../../components/HtmlPageRenderer';
import localCdrJson from '../../utils/cdr_payload_2.json';
import CdrReport from '../../components/CdrReport';
import localJson from '../../utils/iec_61010_1614_1012_output_v1.json';
import PdfViewer from '../../components/PdfViewer';

const ReportPage = () => {
  const dispatch = useDispatch();
  const dataTableRef = useRef(null);

  const pdfViewerRef = useRef(null);

  const projectID = localStorage.getItem('projectId');

  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarkData, setBookmarkData] = useState(null);
  const [trfJson, setTrfJson] = useState(null);

  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);

  const [issuedBy, setIssuedBy] = useState('');

  const [status, setStatus] = useState('Pending'); // "Pending" for the trf api json , "Completed" for the local json"
  const [progress, setProgress] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [isFinalise, setIsFinalise] = useState(false);
  const [reportClick, setReportClick] = useState('trf');

  const myData = useSelector((state) => state?.trf);

  const STAGES = [
    { label: 'Indexing', threshold: 10 },
    { label: 'Generating TRF', threshold: 75 },
    { label: 'TRF Generated', threshold: 100 },
  ];

  // Get TRF report JSON
  const fetchTrfJson = async () => {
    try {
      const res = await generateTrfApi(projectID); // your API call
      if (res?.reports?.length > 0) {
        const jsonData = res.reports[0].json; 
        setTrfJson(jsonData);
      }
    } catch (err) {
      console.error("Error fetching TRF JSON:", err);
    }
  };


  useEffect(() => {
    setTrfJson(myData?.trfData?.data);
    console.log('trfData', myData?.trfData?.data)
  }, [myData]);

  useEffect(() => {
    if (dataTableRef.current && reportClick == 'trf') {
      const value = dataTableRef.current.getFieldValue(
        'Test Report issued under the responsibility of:'
      );
      setIssuedBy(value);
    }
  }, [localJson]);

  const handleIssuedByChange = (e) => {
    const newValue = e.target.value;
    setIssuedBy(newValue);

    if (dataTableRef.current) {
      dataTableRef.current.setFieldValue(
        'Test Report issued under the responsibility of:',
        newValue
      );
    }
  };

  const handleGenerateCDR = () => {
    setReportClick('cdr');
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
      if (status === "Completed") {
        await fetchTrfJson();
        return;
      }

      intervalId = setInterval(async () => {
        await checkStatus();

        if (status === "Completed" || progress === 100) {
          clearInterval(intervalId);
          intervalId = null;
          await fetchTrfJson();   // << fetch JSON immediately
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
    const textSupportTexts =
      data?.ai_fillable === true && Array.isArray(data?.text_support)
        ? data.text_support.map((item) => item.text)
        : [];

    setBookmarkData({
      ...data,
      textSupportTexts,
      textSupportRaw: data?.text_support || [],
    });

    setBookmarkOpen(true);
  };

  // ---------------- CITATION → PDF MODAL ----------------
  const handleCitationLinkClick = (filename, page, text) => {
    setPdfViewerOpen(true);

    const url = '/' + filename;

    // Wait for modal to render
    setTimeout(() => {
      if (!pdfViewerRef.current) return;

      pdfViewerRef.current.loadPdf(url);

      // Allow PDF pages + textLayer to render
      setTimeout(() => {
        if (!pdfViewerRef.current) return;
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

  // ---------------- LEFT PANEL ----------------
  // progress < 100 || !trfJson ---  for to load the trf report from api 
  // ! true ---- for to load local json
  const renderLeftPanel = () => {
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
            <Box className={`step-circle ${reached ? "active" : ""}`}>
              {reached ? "✔" : index + 1}
            </Box>

            <Typography className="step-label">{stage.label}</Typography>

            {index !== STAGES.length - 1 && (
              <Box className={`step-line ${reached ? "active" : ""}`} />
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
          background: progress === 100
            ? "linear-gradient(90deg, #4caf50, #81c784)"
            : "linear-gradient(90deg, #2196f3, #64b5f6)"
        }}
      >
        <Typography className="animated-progress-text">
          {progress}%
        </Typography>
      </Box>
    </Box>

    <Typography className="progress-advanced-status">
      {status}
    </Typography>

    <Button
      disabled={refreshing}
      className="refresh-advanced-btn"
      onClick={checkStatus}
    >
      {refreshing ? "Refreshing..." : "Refresh Status"}
    </Button>
  </Card>
      );
    }
    return (
      <Card className="left-card">
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

                <TextField
                  variant="outlined"
                  size="small"
                  value={issuedBy}
                  onChange={handleIssuedByChange}
                  style={{ flex: 2 }} // makes textbox expand
                />
              </div>
            )}
          </Box>

          {reportClick == 'trf' && (
            <Box className="report-title-container">
              <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
                TEST REPORT
              </Typography>
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
            <DataTable1
              ref={dataTableRef}
              jsonData={trfJson}           // api json load
              // jsonData={localJson}     //localJson load
              editMode={editMode}
              onBookmarkClick={handleBookmarkFromChild}
            />
          )}

          {reportClick == 'cdr' && (
            <CdrReport
              ref={dataTableRef}
              //jsonData={trfJson || localJson} // use real API trfJson when available
              jsonData={localCdrJson}
              editMode={editMode}
              projectId={localStorage.getItem('projectId')}
            />
          )}

          {/* Render Pages 43 to 84 */}
          {/* {Array.isArray(localJsonRemaining) &&
            localJsonRemaining
              .filter((p) => Number(p.page_no) >= 43)
              .map((p, index) => (
                <HtmlPageRenderer
                  key={index}
                  html={p.code_Data}
                  pageNo={p.page_no}
                />
              ))} */}

          {/* <RemainingPagesData
            ref={dataTableRef}
            jsonData={localJsonRemaining}
          /> */}
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
            <Typography className="bookmark-title">Citation</Typography>
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
              <Typography sx={{ fontWeight: 600, mb: 1 }}>
                Supporting Text
              </Typography>

              {bookmarkData.textSupportRaw.map((item, idx) => (
                <Box key={idx} sx={{ mb: 3 }}>
                  {/* Supporting Text */}
                  <Typography
                    sx={{ whiteSpace: 'pre-wrap', fontSize: 14, mb: 1 }}
                  >
                    {item.text}
                  </Typography>

                  {/* Corresponding hyperlink */}
                  <Typography
                    sx={{
                      fontSize: 14,
                      textDecoration: 'underline',
                      cursor: 'pointer',
                      color: '#0077cc',
                      mt: 0.5,
                    }}
                    onClick={() =>
                      handleCitationLinkClick(
                        item.filename,
                        item.page + 1,
                        item.text
                      )
                    }
                  >
                    {item.filename} (Page {item.page + 1})
                  </Typography>
                </Box>
              ))}
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
                    action: () => setEditMode(true),
                  },
                  {
                    text: 'Finalise',
                    icon: '/images/approve_icon.png',
                    bg: '#396872ff',
                    action: handleFinalise,
                  },
                  {
                    text: 'Download',
                    icon: '/images/download_icon.png',
                    bg: '#77D5EA',
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
                    <img
                      src={btn.icon}
                      alt=""
                      className={`icon-img ${
                        btn.text === 'Finalise'
                          ? isFinalise
                            ? 'icon-green' // ✔ Finalise overrides everything
                            : editMode
                              ? 'icon-red' // ✔ editMode=true → RED
                              : 'icon-green' // ✔ normal → GREEN
                          : 'icon-white' // ✔ all others → WHITE
                      }`}
                    />

                    {btn.text}
                  </Button>
                ))}
              </Box>
              <Typography className="generate-title">Generate</Typography>

              <Box className="generate-row">
                {['CDR', 'Letter'].map((label, i) => {
                  const isDisabledStyle = !isFinalise;

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
                        if (!isFinalise) return; // still prevent action
                        if (label === 'CDR') {
                          handleGenerateCDR(); // <-- your function
                        } else if (label === 'Letter') {
                          handleGenerateLetter(); // <-- your second function
                        }
                        console.log(label, 'clicked');
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
          <Card className="confidence-card">
            <CardContent>
              <Typography variant="h6" className="confidence-header">
                Confidence Score
              </Typography>

              <Box className="confidence-summary">
                <Typography>4/6 fields</Typography>
                <Typography fontWeight="bold">67%</Typography>
              </Box>

              <Box className="confidence-bar">
                <Box className="confidence-fill" style={{ width: '67%' }} />
              </Box>

              {[
                { label: 'High', count: 4, color: 'green' },
                { label: 'Medium', count: 1, color: 'yellow' },
                { label: 'Low', count: 0, color: 'red' },
                { label: 'User Edited', count: 12, color: 'grey' },
              ].map((row, i) => (
                <Box key={i} className="confidence-row">
                  <Box className="confidence-label">
                    <Box style={{ display: 'flex', gap: 5 }}>
                      <span className={`dot ${row.color}`} />
                      <Typography>{row.label}</Typography>
                    </Box>
                    <Typography fontWeight="bold">{row.count}</Typography>
                  </Box>
                  {i < 3 && <Divider />}
                </Box>
              ))}
            </CardContent>
          </Card>
        </Box>
      )}
    </Box>
  );
};

export default ReportPage;
