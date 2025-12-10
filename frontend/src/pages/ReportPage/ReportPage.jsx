import React, { useRef, useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Divider,
} from '@mui/material';
import { generateTrfApi } from '../../redux/api/generateTrfApi';
import './ReportPage.css';
import { useDispatch } from 'react-redux';
import DataTable1 from '../../components/DataTable1';
import { finaliseReportRequest } from '../../redux/features/finaliseReport/finaliseReportSlice';
import { getProjectReportStatusApi } from '../../redux/api/projectStatusApi';
import localJson from '../../utils/pta_final_5_UI_upd.json';

const ReportPage = () => {
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarkData, setBookmarkData] = useState(null);
  const [trfJson, setTrfJson] = useState(null);

  const dispatch = useDispatch();
  const dataTableRef = useRef(null);
  const projectID = localStorage.getItem('projectId');
  // ----------------------------------------------------------
  // PROGRESS STATE
  // ----------------------------------------------------------
  const [status, setStatus] = useState('Completed'); // testing
  const [progress, setProgress] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const STAGE_PERCENT = {
    Pending: 0,
    'Indexing in Progress': 25,
    'Ready for Report Generation': 50,
    'Generating Report': 75,
    Completed: 100,
  };

  const STAGES = [
    { label: 'Indexing', key: 'Indexing in Progress' },
    { label: 'TRF Report in Progress', key: 'Ready for Report Generation' },
    // { label: "Generating Report", key: "Report Generation Started" },
    { label: 'Report Generated', key: 'Completed' },
  ];

  // ----------------------------------------------------------
  // POLLING STATUS FUNCTION
  // ----------------------------------------------------------
  const checkStatus = async () => {
    try {
      setRefreshing(true);

      const data = await getProjectReportStatusApi(projectID);

      if (data?.status) {
        console.log('STATUS:', data.status);
        setStatus(data.status);
        setProgress(STAGE_PERCENT[data.status] ?? 0);
      }
    } catch (err) {
      console.error('STATUS CHECK FAILED:', err);
    } finally {
      setRefreshing(false);
    }
  };

  // ----------------------------------------------------------
  // INITIAL + POLLING (30s)
  // ----------------------------------------------------------
  useEffect(() => {
    if (status === 'Completed') return;

    checkStatus();
    const poll = setInterval(checkStatus, 30000);
    return () => clearInterval(poll);
  }, [status]);

  // ----------------------------------------------------------
  // KEEP PROGRESS IN SYNC (DEBUG SAFE)
  // ----------------------------------------------------------
  useEffect(() => {
    setProgress(STAGE_PERCENT[status] ?? 0);
  }, [status]);

  // ----------------------------------------------------------
  //  LOAD TRF JSON WHEN STATUS IS COMPLETED (FIX)
  // ----------------------------------------------------------
  useEffect(() => {
    if (status !== 'Completed' || trfJson) return;

    const loadTrf = async () => {
      try {
        const projectId = 'PRJ_000001';
        const res = await generateTrfApi(projectId);

        console.log('TRF RESPONSE:', res);

        const report = res?.reports?.[0];
        if (report?.json) {
          setTrfJson(report.json);
        }
      } catch (err) {
        console.error('TRF LOAD FAILED:', err);
      }
    };

    loadTrf();
  }, [status, trfJson]);

  // ----------------------------------------------------------
  // BOOKMARK HANDLER
  // ----------------------------------------------------------
  const handleBookmarkFromChild = (data) => {
    setBookmarkData(data);
    setBookmarkOpen(true);
  };

  const handleFinalise = () => {
    if (!dataTableRef.current) return;
    const updatedPayload = dataTableRef.current.getUpdatedJson();
    dispatch(finaliseReportRequest(updatedPayload));
  };

  // ----------------------------------------------------------
  // LEFT PANEL (PROGRESS OR TRF)
  // ----------------------------------------------------------
  const renderLeftPanel = () => {
    if (status !== 'Completed' || !trfJson) {
      return (
        <Card className="progress-advanced-card left-card">
          <Typography className="progress-advanced-title">
            Processing TRF Report
          </Typography>

          <Box className="steps-container">
            {STAGES.map((stage, index) => {
              const reached = progress >= STAGE_PERCENT[stage.key];
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
            <Typography className="header-text">
              Test Report issued under the responsibility of:
            </Typography>
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
            onBookmarkClick={handleBookmarkFromChild}
          />
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
                      className="icon-img icon-white"
                    />
                    {btn.text}
                  </Button>
                ))}
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
