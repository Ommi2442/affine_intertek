import React, { useRef, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Divider,
} from '@mui/material';
import DataTable from '../../components/DataTable';
import jsonData from '../../utils/pta_final.json';
import './ReportPage.css';
import { useSelector } from 'react-redux';
import DataTable1 from '../../components/DataTable1';

const ReportPage = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarkData, setBookmarkData] = useState(null);

  const dataTableRef = useRef(null);

  const handleBookmarkFromChild = (data) => {
    setBookmarkData(data);
    setBookmarkOpen(true);
  };

  const { trfData, loading, error } = useSelector((state) => state.trf);

  if (loading) return <p>Uploading JSON...</p>;
  if (error) return <p>{error}</p>;

  console.log('TRF JSON:', trfData);

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
              <Typography
                className="report-title"
                sx={{ fontWeight: 700, fontSize: '20px' }}
              >
                TEST REPORT
              </Typography>
              <Typography
                className="report-title"
                sx={{ fontWeight: 700, fontSize: '20px' }}
              >
                IEC 61010-1
              </Typography>
              <Typography
                className="report-title"
                sx={{ fontWeight: 700, fontSize: '20px' }}
              >
                Safety requirements for electrical equipment for measurement,
                control, and laboratory use
              </Typography>
              <Typography
                className="report-title"
                sx={{ fontWeight: 700, fontSize: '20px' }}
              >
                Part 1: General requirements
              </Typography>
            </Box>

            {/* <DataTable
              ref={dataTableRef}
              jsonData={trfData?.json}
              onBookmarkClick={handleBookmarkFromChild}
            /> */}

            <DataTable1
              ref={dataTableRef}
              jsonData={jsonData}
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
                  {
                    text: 'Edit / Refine',
                    icon: '/images/edit_icon.svg',
                    bg: '#2C2C2C',
                  },
                  {
                    text: 'Finalise',
                    icon: '/images/approve_icon.png',
                    bg: '#396872ff',
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

          {/* CONFIDENCE */}
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
