import React, { useRef, useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Divider,
} from '@mui/material';
import { generateTrfApi } from "../../redux/api/generateTrfApi";
// import jsonData from '../../utils/pta_final_remaining_v2.json';
import './ReportPage.css';
import { useDispatch } from 'react-redux';
import DataTable1 from '../../components/DataTable1';
import { finaliseReportRequest } from '../../redux/features/finaliseReport/finaliseReportSlice';

const ReportPage = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarkData, setBookmarkData] = useState(null);
  const [trfJson, setTrfJson] = useState(null);
  const [loading, setLoading] = useState(true);

  const dispatch = useDispatch();
  const dataTableRef = useRef(null);

  const handleBookmarkFromChild = (data) => {
    setBookmarkData(data);
    setBookmarkOpen(true);
  };

  const handleFinalise = () => {
    if (!dataTableRef.current) return;
    const updatedPayload = dataTableRef.current.getUpdatedJson();
    console.log('FINAL JSON PAYLOAD:', updatedPayload);
    dispatch(finaliseReportRequest(updatedPayload));
  };

  // -------------------- LOAD JSON FROM API --------------------
  useEffect(() => {
    const project_id = "PRJ_000001"; // replace with actual selection

    const load = async () => {
      try {
        const res = await generateTrfApi(project_id);
        const report = res.reports?.[0];

        if (report) {
          setTrfJson(report.json);   
        }
      } catch (err) {
        console.error("Error loading TRF:", err);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  // -------------------- SHOW LOADING UNTIL JSON IS READY --------------------
  if (loading || !trfJson) {
    return (
      <Box 
        sx={{
          height: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "20px",
          fontWeight: 600
        }}
      >
        Loading TRF Report...
      </Box>
    );
  }

  // -------------------- MAIN UI (RENDERED ONLY AFTER JSON IS READY) --------------------
  return (
    <Box className="report-container">
      
      {/* LEFT SIDE */}
      <Box className="left-panel">
        <Card
          className="left-card"
          sx={{
            borderRadius: '10px',
            overflow: 'hidden',
            backgroundColor: '#fff',
          }}
        >
          <CardContent className="left-content">
            <Box className="report-header">
              <img
                src="/images/trf_image1.jpg"
                className="header-image"
                alt="header"
              />

              <Typography
                className="header-text"
                sx={{ marginRight: '10%', fontWeight: 600, fontSize: '15px' }}
              >
                Test Report issued under the responsibility of:
              </Typography>
            </Box>

            <Box className="report-title-container">
              <Typography sx={{ fontWeight: 700, fontSize: '20px' }}>
                TEST REPORT
              </Typography>
              <Typography sx={{ fontWeight: 700, fontSize: '20px' }}>
                IEC 61010-1
              </Typography>
              <Typography sx={{ fontWeight: 700, fontSize: '20px' }}>
                Safety requirements for electrical equipment for measurement,
                control, and laboratory use
              </Typography>
              <Typography sx={{ fontWeight: 700, fontSize: '20px' }}>
                Part 1: General requirements
              </Typography>
            </Box>

            {/* TABLE */}
            <DataTable1
              ref={dataTableRef}
              jsonData={trfJson}
              onBookmarkClick={handleBookmarkFromChild}
            />
          </CardContent>
        </Card>
      </Box>

      {/* RIGHT SIDE */}
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
          <Card className="action-card" sx={{ borderRadius: '10px' }}>
            <CardContent>
              <Typography variant="h6" className="action-title">
                Actions
              </Typography>

              <Box className="button-stack">
                {[
                  { text: 'Edit / Refine', icon: '/images/edit_icon.svg', bg: '#2C2C2C' },
                  { text: 'Finalise',      icon: '/images/approve_icon.png', bg: '#396872ff', action: handleFinalise },
                  { text: 'Download',      icon: '/images/download_icon.png', bg: '#77D5EA' },
                  { text: 'Missing Field Re..', icon: '/images/file_icon.png', bg: '#5191a0ff' },
                  { text: 'Regenerate', icon: '/images/regenrate_icon.png', bg: '#417581' },
                ].map((btn, i) => (
                  <Button
                    key={i}
                    fullWidth
                    variant="contained"
                    className="action-button"
                    onClick={btn.action}
                    style={{ background: btn.bg }}
                  >
                    <img src={btn.icon} alt="" className="icon-img icon-white" />
                    {btn.text}
                  </Button>
                ))}
              </Box>

              <Typography className="generate-title">Generate</Typography>

              <Box className="generate-row">
                {['CDR', 'Letter'].map((label, i) => (
                  <Button
                    key={i}
                    variant="contained"
                    className="generate-btn"
                    style={{ background: '#417581' }}
                  >
                    <img
                      src="/images/approve_icon.png"
                      className="icon-img icon-white"
                    />
                    {label}
                  </Button>
                ))}
              </Box>
            </CardContent>
          </Card>

          {/* CONFIDENCE CARD */}
          <Card className="confidence-card" sx={{ borderRadius: '10px' }}>
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
                    <Box sx={{ display: 'flex', gap: 1 }}>
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
