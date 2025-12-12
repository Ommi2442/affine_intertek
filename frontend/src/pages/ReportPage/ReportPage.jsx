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

//import { triggerGenerateTrfApi } from '../../redux/api/generateTrfApi';
import localJson from '../../utils/pta_final_5_UI_upd.json';
//import localJsonRemaining from '../../utils/43_84_page_trf.json';
//import RemainingPagesData from '../../components/RemainingPagesData';
//import NewJson from '../../utils/newJsonFrom42.json';
//import HtmlPageRenderer from '../../components/HtmlPageRenderer';
//import localCdrJson from '../../utils/cdr_payload_2.json';
//import CdrReport from '../../components/CdrReport';

const ReportPage = () => {
  const dispatch = useDispatch();
  const dataTableRef = useRef(null);

  // ✅ original source of projectId (unchanged)
  const projectID = localStorage.getItem('projectId');

  /* ---------------- STATE ---------------- */
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarkData, setBookmarkData] = useState(null);
  const [trfJson, setTrfJson] = useState(null);

  const [issuedBy, setIssuedBy] = useState('');
  // ----------------------------------------------------------
  // PROGRESS STATE
  // ----------------------------------------------------------
  const [status, setStatus] = useState('Completed'); // testing
  const [progress, setProgress] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [isFinalise, setIsFinalise] = useState(false);

  const myData = useSelector((state) => state?.trf);
  console.log('myData', myData);

  useEffect(() => {
    setTrfJson(myData?.trfData?.data);
  }, [myData]);

  const STAGES = [
    { label: 'Indexing', threshold: 25 },
    { label: 'Embedding Completed', threshold: 50 },
    { label: 'Generating TRF', threshold: 75 },
    { label: 'TRF Generated', threshold: 100 },
  ];

  useEffect(() => {
    if (dataTableRef.current) {
      const value = dataTableRef.current.getFieldValue(
        'Test Report issued under the responsibility of:'
      );
      setIssuedBy(value);
    }
  }, [localJson]); // runs when JSON is loaded

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

  // useEffect(() => {
  //   const load = async () => {
  //     const response = await triggerGenerateTrfApi(projectID);
  //     setTrfJson(response.data); // TRF JSON loaded
  //     console.log('trfJson', trfJson);
  //   };

  //   load();
  // }, [projectID]);

  // ----------------------------------------------------------
  // 2️⃣ STATUS CHECK (✅ FIXED TO MATCH API RESPONSE)
  // ----------------------------------------------------------
  const checkStatus = async () => {
    if (!projectID) {
      console.warn('Missing projectID, skipping status check');
      return;
    }

    try {
      setRefreshing(true);

      const res = await getProjectReportStatusApi(projectID);

      setStatus(res?.status || 'Pending');
      setProgress(typeof res?.percentage === 'number' ? res.percentage : 0);
    } catch (err) {
      console.error('STATUS CHECK FAILED:', err);
    } finally {
      setRefreshing(false);
    }
  };

  // ----------------------------------------------------------
  // ✅ FIXED POLLING (FIRST LOAD + EVERY 15s)
  // ----------------------------------------------------------
  useEffect(() => {
    if (!projectID) return;

    let intervalId = null;

    const startPolling = async () => {
      await checkStatus();

      intervalId = setInterval(async () => {
        if (progress === 100) {
          clearInterval(intervalId);
          intervalId = null;
          return;
        }

        await checkStatus();
      }, 15000);
    };

    startPolling();

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [projectID, progress]);

  // ----------------------------------------------------------
  // BOOKMARK HANDLING (UNCHANGED)
  // ----------------------------------------------------------
  const handleBookmarkFromChild = (data) => {
    setBookmarkData(data);
    setBookmarkOpen(true);
  };

  const handleFinalise = () => {
    if (!dataTableRef.current) return;
    const updatedPayload = dataTableRef.current.getUpdatedJson();
    dispatch(finaliseReportRequest(updatedPayload));
    setIsFinalise(true);
  };

  // ----------------------------------------------------------
  // LEFT PANEL (PROGRESS OR REPORT)
  // ----------------------------------------------------------
  const renderLeftPanel = () => {
    console.log(localJson);
    console.log(trfJson);
    if (false) {
      return (
        <Card className="progress-advanced-card left-card">
          <Typography className="progress-advanced-title">
            Processing TRF Report
          </Typography>

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

          <Box className="progress-advanced-bar">
            <Box
              className="progress-advanced-fill"
              style={{ width: `${progress}%` }}
            />
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

    // ---------------- ORIGINAL LEFT PANEL ----------------
    return (
      <Card className="left-card">
        <CardContent className="left-content">
          <Box className="report-header">
            <img
              src="/images/trf_image1.jpg"
              className="header-image"
              alt="header"
            />
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
          </Box>

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

          <DataTable1
            ref={dataTableRef}
            //jsonData={trfJson}
            jsonData={localJson}
            editMode={editMode}
            onBookmarkClick={handleBookmarkFromChild}
          />

          {/* <CdrReport
            ref={dataTableRef}
            //jsonData={trfJson || localJson} // use real API trfJson when available
            jsonData={localCdrJson}
            editMode={editMode}
            projectId={localStorage.getItem('projectId')}
          /> */}

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

  // ----------------------------------------------------------
  // FINAL PAGE LAYOUT
  // ----------------------------------------------------------
  return (
    <Box className="report-container">
      <Box className="left-panel">{renderLeftPanel()}</Box>

      {bookmarkOpen ? (
        <Box className="bookmark-panel">
          <Box className="bookmark-header">
            <Typography className="bookmark-title">Citation</Typography>
            <Button size="small" onClick={() => setBookmarkOpen(false)}>
              ✕
            </Button>
          </Box>
          <Typography className="bookmark-field">
            {bookmarkData?.field}
          </Typography>
          <Typography className="bookmark-value">
            {bookmarkData?.value}
          </Typography>
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
